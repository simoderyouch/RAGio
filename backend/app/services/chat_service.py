import os
import warnings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.documents import Document
from langdetect import detect
from typing import List


from app.utils.prompt import (
    custom_prompt_template,
    custom_summary_prompt_template,
    custom_summary_chunked_prompt_template,
    custom_question_extraction_prompt_template,
    custom_question_chunked_prompt_template
)
from app.utils.CustomEmbedding import CustomEmbedding
from app.config import encoder, llm, qdrant_client, LANGUAGE_MAP
from app.utils.logger import log_info, log_error, log_warning, log_performance
import re
import time
warnings.filterwarnings("ignore", message="langchain is deprecated.", category=DeprecationWarning)

from app.services.document_service import retrieved_docs_unified
from app.services.rag_pipeline import get_rag_pipeline, RAGConfig, FAST_CONFIG
from sqlalchemy.orm import Session
from sqlalchemy import asc
from app.db.models import Chat, UploadedFile
from app.middleware.error_handler import ValidationException, DatabaseException, FileProcessingException
from datetime import datetime, timezone
import json


def clean_response(response: str) -> str:
    """
    Robust response cleaning that preserves HTML structure and removes thinking tags.
    Ensures the response is never empty - returns original response if cleaning results in empty string.
    """
    if not response or not response.strip():
        return response
    
    try:
        original_response = response
        
        # Always remove thinking tags regardless of case or format
        response_clean = re.sub(r"<think>.*?</think>", "", response, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"<thinking>.*?</thinking>", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"<thought>.*?</thought>", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"<reasoning>.*?</reasoning>", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"<think>.*?</think>", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any remaining thinking-related content
        response_clean = re.sub(r"Let me think.*?\.", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"I need to think.*?\.", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r"Thinking.*?\.", "", response_clean, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove markdown code blocks but preserve HTML
        response_clean = re.sub(r'```.*?```', '', response_clean, flags=re.DOTALL)
        
        # Remove any non-semantic HTML tags that might interfere
        response_clean = re.sub(r'<script.*?</script>', '', response_clean, flags=re.DOTALL | re.IGNORECASE)
        response_clean = re.sub(r'<style.*?</style>', '', response_clean, flags=re.DOTALL | re.IGNORECASE)
        
        # Clean up extra whitespace
        response_clean = re.sub(r'\n\s*\n+', '\n\n', response_clean)
        response_clean = response_clean.strip()
        
        # Check if cleaning resulted in empty or near-empty response
        # Remove HTML tags temporarily to check if there's actual content
        text_only = re.sub(r'<[^>]+>', '', response_clean)
        text_only = text_only.strip()
        
        if not text_only or len(text_only) < 10:
            # If cleaning removed all content, return original response
            log_warning(
                "Response cleaning resulted in empty content, returning original response",
                context="response_cleaning",
                original_length=len(original_response),
                cleaned_length=len(text_only)
            )
            response_clean = original_response.strip()
        
        # Ensure proper HTML structure only if we have content
        if response_clean and not response_clean.startswith('<article>'):
            # If response doesn't start with article tag, wrap it
            response_clean = f'<article>{response_clean}</article>'
        
        final_response = response_clean.strip() if response_clean else original_response.strip()
        
        # Final safety check - never return empty string
        if not final_response or len(final_response.strip()) < 5:
            log_warning(
                "Response is empty after cleaning, returning original response",
                context="response_cleaning",
                original_length=len(original_response)
            )
            return original_response.strip() if original_response and original_response.strip() else "I apologize, but I couldn't generate a proper response. Please try again."
        
        return final_response
        
    except Exception as e:
        log_warning(f"Response cleaning failed: {e}", context="response_cleaning")
        # Return original response if cleaning fails, never empty
        if response and response.strip():
            return response.strip()
        return "I apologize, but I couldn't generate a proper response. Please try again."

def format_memory_for_prompt(memory: list, max_messages: int = 5) -> str:
    """Format conversation memory for prompt injection"""
    if not memory:
        return "No previous conversation."
    
    # Take only recent messages
    recent_memory = memory[-max_messages:] if len(memory) > max_messages else memory
    
    formatted_memory = []
    for msg in recent_memory:
        role = msg.get("role", "unknown")
        content = msg.get("content", "")
        if content.strip():
            formatted_memory.append(f"{role.title()}: {content}")
    
    return "\n".join(formatted_memory) if formatted_memory else "No previous conversation."


def format_context_with_sources(context: list) -> str:
    """
    Format context documents with source information for LLM.
    Includes file names and page numbers in the context to help LLM cite sources.
    
    Args:
        context: List of Document objects with metadata
        
    Returns:
        Formatted context string with source attribution
    """
    if not context:
        return "No context provided."
    
    formatted_chunks = []
    for i, doc in enumerate(context):
        if not hasattr(doc, 'page_content'):
            continue
            
        text = doc.page_content.strip()
        if not text:
            continue
        
        # Extract source information
        metadata = getattr(doc, 'metadata', {})
        file_name = metadata.get("file_name", "Unknown")
        page = metadata.get("page", 0)
        
        # Remove file extension for cleaner display
        if "." in file_name:
            file_name = file_name.rsplit(".", 1)[0]
        
        # Format chunk with source attribution
        if page and page > 0:
            source_prefix = f"[From {file_name}, Page {page}]: "
        else:
            source_prefix = f"[From {file_name}]: "
        
        formatted_chunks.append(f"{source_prefix}{text}")
    
    if not formatted_chunks:
        return "No context content available."
    
    return "\n\n".join(formatted_chunks)


def extract_sources_from_context(context: list) -> str:
    """
    Extract and format source information from context documents.
    Returns formatted sources string following the exact format requested.
    
    Args:
        context: List of Document objects with metadata
        
    Returns:
        Formatted sources string (e.g., "Sources: Page 13, Page 18" or "Sources: Document A — Page 5, Document B — Page 11–12")
    """
    if not context:
        return "Sources: None (reason: no context provided)"
    
    # Collect unique sources with pages
    sources_dict = {}  # {file_name: set of pages}
    
    for doc in context:
        if not hasattr(doc, 'metadata'):
            continue
            
        metadata = getattr(doc, 'metadata', {})
        file_name = metadata.get("file_name", "Unknown")
        page = metadata.get("page", 0)
        
        # Remove file extension for cleaner display
        if "." in file_name:
            file_name = file_name.rsplit(".", 1)[0]
        
        if file_name not in sources_dict:
            sources_dict[file_name] = set()
        
        # Only add valid page numbers (greater than 0)
        if isinstance(page, (int, float)) and page > 0:
            sources_dict[file_name].add(int(page))
    
    if not sources_dict:
        return "Sources: None (reason: no source metadata available)"
    
    # Format sources according to user requirements
    sources_list = []
    num_documents = len(sources_dict)
    
    for file_name, pages in sorted(sources_dict.items()):
        if pages:
            # Sort pages and format ranges
            sorted_pages = sorted(pages)
            page_strs = []
            
            # Group consecutive pages into ranges
            start = sorted_pages[0]
            end = sorted_pages[0]
            
            for i in range(1, len(sorted_pages)):
                if sorted_pages[i] == end + 1:
                    end = sorted_pages[i]
                else:
                    # Add the current range
                    if start == end:
                        page_strs.append(f"Page {start}")
                    else:
                        page_strs.append(f"Page {start}–{end}")
                    start = sorted_pages[i]
                    end = sorted_pages[i]
            
            # Add the last range
            if start == end:
                page_strs.append(f"Page {start}")
            else:
                page_strs.append(f"Page {start}–{end}")
            
            # Format based on number of documents
            if num_documents == 1:
                # Single document: "Sources: Page 13, Page 18"
                sources_list.extend(page_strs)
            else:
                # Multiple documents: "Document A — Page 5, Page 11–12"
                sources_list.append(f"{file_name} — {', '.join(page_strs)}")
        else:
            # No page numbers available, just document name
            if num_documents == 1:
                sources_list.append(file_name)
            else:
                sources_list.append(file_name)
    
    if not sources_list:
        return "Sources: None (reason: no source metadata available)"
    
    return "Sources: " + ", ".join(sources_list)

async def generate_response(
    index: str,
    question: str,
    context: list,
    memory: list = None,
    language: str = "Auto-detect",
    file_id: int = None,
    user_id: int = None,
):
    start_time = time.time()
    
    try:
        log_info(
            "Starting AI response generation",
            context="ai_response",
            index=index,
            question_length=len(question),
            context_length=len(context),
            language=language,
            memory_length=len(memory) if memory else 0
        )
        

        
        # Detect language
        language_names = LANGUAGE_MAP
        try:
            detected_lang = detect(context[0].page_content)
            log_info(
                f"Language detected: {detected_lang}",
                context="ai_response",
                index=index
            )
        except Exception as e:
            detected_lang = "en"
            log_warning(
                "Language detection failed, defaulting to English",
                context="ai_response",
                index=index,
                error=str(e)
            )

        selected_language = language if language != "Auto-detect" else language_names.get(detected_lang, "English")

        prompt_template = custom_prompt_template(selected_language)
        rag_prompt = ChatPromptTemplate.from_template(prompt_template)

        
        formatted_memory = format_memory_for_prompt(memory or [])

        # Chain: Input → Prompt → LLM → Output
        if llm is None:
            log_error(
                "LLM not available",
                context="ai_response",
                index=index
            )
            return "AI response generation is not available. Please configure GROQ_API_KEY environment variable."

        # Format context with source information for better LLM understanding
        # This helps the LLM know which document and page each piece of information comes from
        formatted_context = format_context_with_sources(context)

        rag_chain = (
            {
                "context": lambda _: formatted_context,
                "memory": lambda _: formatted_memory,
                "question": RunnablePassthrough(),
            }
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        response = rag_chain.invoke(question)
        
        # Use robust response cleaning
        response_clean = clean_response(response)

        # Extract and append sources section
        sources_section = extract_sources_from_context(context)
        
        # Append sources if not already present in response
        # Check case-insensitively for existing sources
        response_lower = response_clean.lower()
        if "sources:" not in response_lower:
            # Ensure proper HTML structure
            if response_clean.endswith('</article>'):
                # Insert sources before closing article tag with proper formatting
                response_clean = response_clean[:-10] + f'<p><strong>{sources_section}</strong></p></article>'
            elif response_clean.startswith('<article>'):
                # Response has article tag but doesn't end with it (shouldn't happen, but handle it)
                response_clean = response_clean + f'<p><strong>{sources_section}</strong></p>'
            else:
                # No article tag, append sources at the end
                response_clean = response_clean + f'<p><strong>{sources_section}</strong></p>'
        
        duration = time.time() - start_time
        log_performance(
            "AI response generation completed",
            duration,
            index=index,
            response_length=len(response_clean),
            original_length=len(response)
        )

        return response_clean

    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="ai_response",
            index=index,
            question=question,
            duration=duration
        )
        return f"Error: {str(e)}"




async def generate_summary(
    index: str,
    context: List[Document],
    language: str = "Auto-detect",
):
    start_time = time.time()
    
    try:
        log_info(
            "Starting summary generation",
            context="ai_summary",
            index=index,
            context_length=len(context),
            language=language
        )
        
        total_chars = sum(len(doc.page_content) for doc in context)
        estimated_tokens = total_chars // 4
        
        log_info(
            f"Context token estimation for summary",
            context="ai_summary",
            index=index,
            total_chars=total_chars,
            estimated_tokens=estimated_tokens,
            num_documents=len(context),
            threshold=15000
        )
        
        if estimated_tokens > 6000:
            log_warning(
                f"Context too large ({estimated_tokens} tokens), using chunked processing",
                context="ai_summary",
                index=index,
                estimated_tokens=estimated_tokens
            )
            return await generate_summary_chunked(index, context, language)
        
        language_names = LANGUAGE_MAP
        try:
            detected_lang = detect(context[0].page_content)
            log_info(
                f"Language detected for summary: {detected_lang}",
                context="ai_summary",
                index=index
            )
        except Exception as e:
            detected_lang = "en"
            log_warning(
                "Language detection failed for summary, defaulting to English",
                context="ai_summary",
                index=index,
                error=str(e)
            )

        selected_language = language if language != "Auto-detect" else language_names.get(detected_lang, "English")

        prompt_template = custom_summary_prompt_template(selected_language)
        rag_prompt = ChatPromptTemplate.from_template(prompt_template)

        # Check if LLM is available
        if llm is None:
            log_error(
                "LLM not available",
                context="ai_summary",
                index=index
            )
            return "AI summary generation is not available. Please configure GROQ_API_KEY environment variable."

        rag_chain = (
            {"context": lambda _: context, "question": lambda _: ""}
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        summary = rag_chain.invoke("")
        
        summary = clean_response(summary)
        
        duration = time.time() - start_time
        log_performance(
            "Summary generation completed",
            duration,
            index=index,
            summary_length=len(summary)
        )
        
        return summary

    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="ai_summary",
            index=index,
            duration=duration
        )
        return f"Error generating summary: {str(e)}"


async def generate_summary_chunked(
    index: str,
    context: List[Document],
    language: str = "Auto-detect",
    chunk_size: int = 10  
):
    """Generate summary by processing large documents in chunks"""
    try:
        log_info(
            "Starting chunked summary generation",
            context="ai_summary_chunked",
            index=index,
            total_chunks=len(context) // chunk_size + 1
        )
        
        chunks = [context[i:i + chunk_size] for i in range(0, len(context), chunk_size)]
        
        summaries = []
        for i, chunk in enumerate(chunks):
            log_info(
                f"Processing chunk {i+1}/{len(chunks)}",
                context="ai_summary_chunked",
                index=index,
                chunk_size=len(chunk)
            )
            
            chunk_summary = await generate_summary_single_chunk(index, chunk, language, i+1, len(chunks))
            summaries.append(chunk_summary)
        
        if len(summaries) > 1:
            log_info(
                "Combining chunk summaries",
                context="ai_summary_chunked",
                index=index,
                num_summaries=len(summaries)
            )
            
            combined_context = [Document(page_content="\n\n".join(summaries), metadata={"source": "combined_summaries"})]
            final_summary = await generate_summary_single_chunk(index, combined_context, language, 1, 1)
            return final_summary
        else:
            return summaries[0]
            
    except Exception as e:
        log_error(
            e,
            context="ai_summary_chunked",
            index=index
        )
        return f"Error generating chunked summary: {str(e)}"


async def generate_summary_single_chunk(
    index: str,
    context: List[Document],
    language: str,
    chunk_num: int = 1,
    total_chunks: int = 1
):
    """Generate summary for a single chunk of documents"""
    try:
        language_names = LANGUAGE_MAP
        try:
            detected_lang = detect(context[0].page_content)
        except Exception as e:
            detected_lang = "en"
            log_warning(
                "Language detection failed for chunk summary, defaulting to English",
                context="ai_summary_chunked",
                index=index,
                error=str(e)
            )

        selected_language = language if language != "Auto-detect" else language_names.get(detected_lang, "English")

        if total_chunks > 1:
            prompt_template = custom_summary_chunked_prompt_template(selected_language, chunk_num, total_chunks)
        else:
            prompt_template = custom_summary_prompt_template(selected_language)
        
        rag_prompt = ChatPromptTemplate.from_template(prompt_template)


        if llm is None:
            log_error(
                "LLM not available",
                context="ai_summary_single_chunk",
                index=index
            )
            return "AI summary generation is not available. Please configure GROQ_API_KEY environment variable."

        rag_chain = (
            {"context": lambda _: context, "question": lambda _: ""}
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        summary = rag_chain.invoke("")
        
        # Clean the response to remove thinking tags
        summary = clean_response(summary)
        
        return summary

    except Exception as e:
        log_error(
            e,
            context="ai_summary_single_chunk",
            index=index,
            chunk_num=chunk_num
        )
        return f"Error generating summary for chunk {chunk_num}: {str(e)}"


import json

async def generate_questions(
    index: str,
    context: List[Document],
    language: str = "Auto-detect",
):
    start_time = time.time()
    
    try:
        log_info(
            "Starting question generation",
            context="ai_questions",
            index=index,
            context_length=len(context),
            language=language
        )
        
        # Check if context is too large and needs chunking
        total_chars = sum(len(doc.page_content) for doc in context)
        estimated_tokens = total_chars // 4
        
        log_info(
            f"Context token estimation for questions",
            context="ai_questions",
            index=index,
            total_chars=total_chars,
            estimated_tokens=estimated_tokens,
            num_documents=len(context),
            threshold=15000
        )
        
        if estimated_tokens > 5000:
            log_warning(
                f"Context too large ({estimated_tokens} tokens), using chunked processing for questions",
                context="ai_questions",
                index=index,
                estimated_tokens=estimated_tokens
            )
            return await generate_questions_chunked(index, context, language)
        
        language_names = LANGUAGE_MAP
        try:
            detected_lang = detect(context[0].page_content)
            log_info(
                f"Language detected for questions: {detected_lang}",
                context="ai_questions",
                index=index
            )
        except Exception as e:
            detected_lang = "en"
            log_warning(
                "Language detection failed for questions, defaulting to English",
                context="ai_questions",
                index=index,
                error=str(e)
            )

        selected_language = language if language != "Auto-detect" else language_names.get(detected_lang, "English")

        prompt_template = custom_question_extraction_prompt_template(selected_language)
        rag_prompt = ChatPromptTemplate.from_template(prompt_template)

        # Check if LLM is available
        if llm is None:
            log_error(
                "LLM not available - GROQ_API_KEY not configured",
                context="ai_questions",
                index=index
            )
            return ["AI question generation is not available. Please configure GROQ_API_KEY environment variable."]

        rag_chain = (
            {"context": lambda _: context, "question": lambda _: ""}
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        result = rag_chain.invoke("")
        
        # Clean the response to remove thinking tags
        result = clean_response(result)
        
        log_info(
            "Raw question generation result received",
            context="ai_questions",
            index=index,
            result_length=len(result)
        )
        
        match = re.search(r"\[\s*\".*?\"\s*(?:,\s*\".*?\"\s*)*\]", result, re.DOTALL)
        if match:
            questions = json.loads(match.group(0))
            log_info(
                f"Extracted {len(questions)} questions from JSON",
                context="ai_questions",
                index=index,
                question_count=len(questions)
            )
        else:
            questions = result
            log_warning(
                "Could not extract JSON questions, using raw result",
                context="ai_questions",
                index=index
            )

        duration = time.time() - start_time
        log_performance(
            "Question generation completed",
            duration,
            index=index,
            question_count=len(questions) if isinstance(questions, list) else 0
        )

        return questions
       
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="ai_questions",
            index=index,
            duration=duration
        )
        return f"Error extracting questions: {str(e)}"


async def generate_questions_chunked(
    index: str,
    context: List[Document],
    language: str = "Auto-detect",
    chunk_size: int = 10  
):
    """Generate questions by processing large documents in chunks"""
    try:
        log_info(
            "Starting chunked question generation",
            context="ai_questions_chunked",
            index=index,
            total_chunks=len(context) // chunk_size + 1
        )
        
        
        chunks = [context[i:i + chunk_size] for i in range(0, len(context), chunk_size)]
        
        all_questions = []
        for i, chunk in enumerate(chunks):
            log_info(
                f"Processing chunk {i+1}/{len(chunks)} for questions",
                context="ai_questions_chunked",
                index=index,
                chunk_size=len(chunk)
            )
            
            # Generate questions for this chunk
            chunk_questions = await generate_questions_single_chunk(index, chunk, language, i+1, len(chunks))
            
            # Extract questions from result
            if isinstance(chunk_questions, list):
                all_questions.extend(chunk_questions)
 
        
        unique_questions = list(dict.fromkeys(all_questions))  # Preserve order
        final_questions = unique_questions[:10]  

        log_info(
            f"Generated {len(final_questions)} unique questions from chunks",
            context="ai_questions_chunked",
            index=index,
            total_generated=len(all_questions),
            unique_count=len(unique_questions)
        )
        
        return final_questions
            
    except Exception as e:
        log_error(
            e,
            context="ai_questions_chunked",
            index=index
        )
        return f"Error generating chunked questions: {str(e)}"


async def generate_questions_single_chunk(
    index: str,
    context: List[Document],
    language: str,
    chunk_num: int = 1,
    total_chunks: int = 1
):
    """Generate questions for a single chunk of documents"""
    try:
        language_names = LANGUAGE_MAP
        try:
            detected_lang = detect(context[0].page_content)
        except Exception as e:
            detected_lang = "en"
            log_warning(
                "Language detection failed for chunk questions, defaulting to English",
                context="ai_questions_chunked",
                index=index,
                error=str(e)
            )

        selected_language = language if language != "Auto-detect" else language_names.get(detected_lang, "English")

        prompt_template = custom_question_chunked_prompt_template(selected_language, chunk_num, total_chunks)
        
        rag_prompt = ChatPromptTemplate.from_template(prompt_template)

        # Check if LLM is available
        if llm is None:
            log_error(
                "LLM not available",
                context="ai_questions_single_chunk",
                index=index
            )
            return ["AI question generation is not available."]

        rag_chain = (
            {"context": lambda _: context, "question": lambda _: ""}
            | rag_prompt
            | llm
            | StrOutputParser()
        )

        result = rag_chain.invoke("")

        # Strip markdown code block if present (```json ... ```)
        result = re.sub(r"```(?:json)?\s*", "", result).strip()
        result = re.sub(r"```\s*$", "", result).strip()


        match = re.search(r"\[\s*\".*?\"\s*(?:,\s*\".*?\"\s*)*\]", result, re.DOTALL)
        if match:
            try:
                questions = json.loads(match.group(0))
                return questions
            except:
                return result
        else:
            return result

    except Exception as e:
        log_error(
            e,
            context="ai_questions_single_chunk",
            index=index,
            chunk_num=chunk_num
        )
        return f"Error generating questions for chunk {chunk_num}: {str(e)}"








async def get_file_messages(file_id: int, user_id: int, db: Session, request_id: str = None, limit: int = 10) -> list:
    try:
        file = db.query(UploadedFile).filter(UploadedFile.owner_id == user_id, UploadedFile.id == file_id).first()
        if file is None:
            log_warning("File not found for message retrieval", context="chat_messages", request_id=request_id, file_id=file_id, user_id=user_id)
            return []
            
        chats = db.query(Chat).filter(Chat.uploaded_file_id == file.id).order_by(asc(Chat.created_at_question)).limit(limit).all()
        
        if not chats:
            return []
        
        messages = []
        for chat in chats:
            if chat.question:
                messages.append({"role": "user", "content": chat.question})
            if chat.response:
                messages.append({"role": "assistant", "content": chat.response})
        
        return messages
        
    except Exception as e:
        log_error(e, context="chat_messages", request_id=request_id, file_id=file_id, user_id=user_id)
        return []


async def process_chat_request(
    question: str,
    file_id: int,
    user_id: int,
    db: Session,
    language: str = "Auto-detect",
    request_id: str = None
) -> dict:
    """
    Process a chat request for a single file: retrieve context, generate response, and save to DB.
    Returns the response along with source information for PDF highlighting.
    """
    start_time = time.time()
    try:
        log_info("Chat request started", context="process_chat", request_id=request_id, file_id=file_id, user_id=user_id)
        
        question_time = datetime.now(timezone.utc)
        file = db.query(UploadedFile).filter(UploadedFile.owner_id == user_id, UploadedFile.id == file_id).first()
        if file is None:
            raise ValidationException("File not found", {"file_id": file_id, "user_id": user_id})
        
        if file.embedding_path is None:
            raise ValidationException("Processed document not found", {"file_id": file_id, "user_id": user_id})
        
        message_history = await get_file_messages(file_id, user_id, db, request_id)
        
        try:
            # Use new RAG pipeline with multi-stage retrieval
            rag_pipeline = get_rag_pipeline(fast=False)
            
            # Retrieve relevant context using modern RAG pipeline
            context_result = await rag_pipeline.retrieve_as_documents(
                query=question,
                user_id=user_id,
                file_ids=[file_id],  # Filter to only this specific file
                max_tokens=5000
            )
            
            # Handle case where context is an error string
            if isinstance(context_result, str):
                # Fall back to legacy retrieval if RAG pipeline fails
                log_warning(
                    f"RAG pipeline returned error, falling back to legacy: {context_result}",
                    context="process_chat",
                    file_id=file_id
                )
                context = retrieved_docs_unified(
                    question=question,
                    user_id=user_id,
                    file_ids=[file_id],
                    max_tokens=5000
                )
                if isinstance(context, str):
                    raise FileProcessingException(context, {"file_id": file_id})
            else:
                context = context_result
            
            response = await generate_response(
                file.file_name.split('.')[0], 
                question, 
                context, 
                memory=message_history, 
                language=language,
                file_id=file_id,
                user_id=user_id
            )
            
            log_info(
                "Response generated using modern RAG pipeline",
                context="process_chat",
                request_id=request_id,
                file_id=file_id,
                context_chunks=len(context) if isinstance(context, list) else 0
            )
            
        except Exception as e:
            raise FileProcessingException(f"Failed to generate response: {str(e)}", {"file_id": file_id})
        
        # Validate response is not empty
        if not response or not response.strip():
            log_error(
                "Empty response generated",
                context="process_chat",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id
            )
            raise FileProcessingException(
                "Failed to generate a valid response. The AI model returned an empty response. Please try again or rephrase your question.",
                {"file_id": file_id, "user_id": user_id}
            )
        
        # Check if response only contains HTML tags with no actual text content
        text_only = re.sub(r'<[^>]+>', '', response)
        text_only = text_only.strip()
        if not text_only or len(text_only) < 5:
            log_error(
                "Response contains only HTML tags with no text content",
                context="process_chat",
                request_id=request_id,
                file_id=file_id,
                user_id=user_id,
                response_length=len(response),
                text_length=len(text_only)
            )
            raise FileProcessingException(
                "Failed to generate a valid response. The AI model returned a response with no meaningful content. Please try again or rephrase your question.",
                {"file_id": file_id, "user_id": user_id}
            )
        
        response_time = datetime.now(timezone.utc)
        
        chat = Chat(
            question=question,
            response=response,
            user_id=user_id,
            uploaded_file_id=file_id,
            created_at_question=question_time,
            created_at_response=response_time
        )
        
        try:
            db.add(chat)
            db.commit()
        except Exception as e:
            db.rollback()
            raise DatabaseException("Failed to save chat record", {"file_id": file_id, "user_id": user_id})
        
        duration = time.time() - start_time
        
        return {
            "message": response, 
            "create_at": response_time,
            "processing_time": f"{duration:.2f}s"
        }

    except (ValidationException, FileProcessingException, DatabaseException):
        raise
    except Exception as e:
        duration = time.time() - start_time
        log_error(e, context="process_chat", request_id=request_id, duration=duration)
        raise DatabaseException("Chat request failed", {"duration": duration})


async def process_general_chat(
    question: str,
    excluded_file_ids: List[int],
    user_id: int,
    db: Session,
    language: str = "Auto-detect",
    request_id: str = None,
    include_only_file_ids: List[int] = None
) -> dict:
    """
    Process a general chat request using all user documents by default.
    Users can exclude specific documents or specify only certain documents to include.
    
    Args:
        question: The user's question
        excluded_file_ids: List of file IDs to exclude from context
        user_id: The user's ID
        db: Database session
        language: Response language preference
        request_id: Request tracking ID
        include_only_file_ids: If provided, only use these file IDs (for backward compatibility)
    """
    start_time = time.time()
    try:
        log_info(
            "General chat request started", 
            context="process_general_chat", 
            request_id=request_id, 
            user_id=user_id,
            excluded_count=len(excluded_file_ids),
            include_only=include_only_file_ids is not None
        )
        
        # Get all processed files for the user
        all_files_query = db.query(UploadedFile).filter(
            UploadedFile.owner_id == user_id,
            UploadedFile.embedding_path.isnot(None)  # Only processed files
        )
        
        all_processed_files = all_files_query.all()
        
        if not all_processed_files:
            raise ValidationException(
                "No processed documents found. Please upload and process documents first.",
                {"user_id": user_id}
            )
        
        # Filter files based on inclusion/exclusion rules
        if include_only_file_ids is not None:
            # Use only specified files (backward compatibility mode)
            files = [f for f in all_processed_files if f.id in include_only_file_ids]
            if not files:
                raise ValidationException(
                    "None of the specified files are available or processed.",
                    {"file_ids": include_only_file_ids, "user_id": user_id}
                )
        else:
            # Use all files except excluded ones
            files = [f for f in all_processed_files if f.id not in excluded_file_ids]
            if not files:
                raise ValidationException(
                    "All documents have been excluded. Please include at least one document.",
                    {"excluded_file_ids": excluded_file_ids, "user_id": user_id}
                )
        
        # Build file ID lists for unified retrieval
        file_ids_to_include = [f.id for f in files] if include_only_file_ids else None
        file_ids_to_exclude = excluded_file_ids if not include_only_file_ids else None
        
        log_info(
            f"Using unified retrieval for general chat",
            context="process_general_chat",
            request_id=request_id,
            total_processed=len(all_processed_files),
            files_available=len(files),
            include_mode="specific" if file_ids_to_include else "exclude"
        )
        
        # Use new RAG pipeline with multi-stage retrieval for cross-document search
        try:
            rag_pipeline = get_rag_pipeline(fast=False)
            
            # Modern RAG pipeline with query expansion, hybrid search, and re-ranking
            all_contexts = await rag_pipeline.retrieve_as_documents(
                query=question,
                user_id=user_id,
                file_ids=file_ids_to_include,
                exclude_file_ids=file_ids_to_exclude,
                max_tokens=10000  # Higher token budget for multi-doc context
            )
            
            # Handle case where context is an error string
            if isinstance(all_contexts, str):
                # Fall back to legacy retrieval if RAG pipeline fails
                log_warning(
                    f"RAG pipeline returned error, falling back to legacy: {all_contexts}",
                    context="process_general_chat",
                    user_id=user_id
                )
                all_contexts = retrieved_docs_unified(
                    question=question,
                    user_id=user_id,
                    file_ids=file_ids_to_include,
                    exclude_file_ids=file_ids_to_exclude,
                    max_tokens=10000
                )
                if isinstance(all_contexts, str):
                    raise FileProcessingException(all_contexts, {"user_id": user_id})
                
        except Exception as e:
            log_error(
                e,
                context="process_general_chat",
                request_id=request_id,
                user_id=user_id
            )
            raise FileProcessingException(
                f"Failed to retrieve context: {str(e)}",
                {"user_id": user_id}
            )
        
        if not all_contexts:
            raise FileProcessingException(
                "No relevant content found in any of the selected documents.",
                {"file_count": len(files)}
            )
        
        # Extract unique document names from context metadata for response
        files_used_ids = set()
        document_names = []
        for doc in all_contexts:
            file_id = doc.metadata.get("file_id")
            file_name = doc.metadata.get("file_name", "Unknown")
            if file_id and file_id not in files_used_ids:
                files_used_ids.add(file_id)
                # Remove file extension for cleaner display
                name_without_ext = file_name.rsplit(".", 1)[0] if "." in file_name else file_name
                document_names.append(name_without_ext)
        
        # Get actual file objects for response
        files_used = [f for f in files if f.id in files_used_ids]
        
        log_info(
            f"Unified retrieval returned {len(all_contexts)} chunks from {len(files_used)} files",
            context="process_general_chat",
            request_id=request_id,
            chunks_retrieved=len(all_contexts),
            files_used=len(files_used)
        )
        
        # Get message history for general chat (all files)
        message_history = []
        try:
            # Get recent messages from all user files for context
            all_user_chats = db.query(Chat).filter(
                Chat.user_id == user_id
            ).order_by(Chat.created_at_response.desc()).limit(10).all()
            
            for chat in reversed(all_user_chats):  # Reverse to get chronological order
                if chat.question and chat.response:
                    message_history.append({
                        "role": "user",
                        "content": chat.question
                    })
                    message_history.append({
                        "role": "assistant",
                        "content": chat.response
                    })
        except Exception as e:
            log_warning(
                f"Failed to retrieve message history: {e}",
                context="process_general_chat",
                request_id=request_id,
                user_id=user_id
            )
            message_history = []
        
        # Generate response using standard generate_response function
        try:
            # Use descriptive index for logging (general chat across multiple documents)
            index_name = f"general_chat_{len(document_names)}docs" if document_names else "general"
            response = await generate_response(
                index=index_name,
                question=question,
                context=all_contexts,
                memory=message_history,
                language=language,
                file_id=None,  # General chat doesn't have a single file_id
                user_id=user_id
            )
        except Exception as e:
            raise FileProcessingException(
                f"Failed to generate response: {str(e)}",
                {"file_count": len(files_used)}
            )
        
        # Validate response is not empty
        if not response or not response.strip():
            log_error(
                "Empty response generated",
                context="process_general_chat",
                request_id=request_id,
                user_id=user_id,
                documents_used=len(files_used)
            )
            raise FileProcessingException(
                "Failed to generate a valid response. The AI model returned an empty response. Please try again or rephrase your question.",
                {"user_id": user_id, "documents_used": len(files_used)}
            )
        
        # Check if response only contains HTML tags with no actual text content
        text_only = re.sub(r'<[^>]+>', '', response)
        text_only = text_only.strip()
        if not text_only or len(text_only) < 5:
            log_error(
                "Response contains only HTML tags with no text content",
                context="process_general_chat",
                request_id=request_id,
                user_id=user_id,
                response_length=len(response),
                text_length=len(text_only),
                documents_used=len(files_used)
            )
            raise FileProcessingException(
                "Failed to generate a valid response. The AI model returned a response with no meaningful content. Please try again or rephrase your question.",
                {"user_id": user_id, "documents_used": len(files_used)}
            )
        
        response_time = datetime.now(timezone.utc)
        duration = time.time() - start_time
        
        log_info(
            f"General chat completed in {duration:.2f}s",
            context="process_general_chat",
            request_id=request_id,
            documents_used=len(files_used),
            response_length=len(response)
        )
        
        return {
            "message": response,
            "create_at": response_time.isoformat(),
            "processing_time": f"{duration:.2f}s",
            "documents_used": [{"id": file.id, "name": file.file_name} for file in files_used],
            "total_documents": len(all_processed_files),
            "excluded_count": len(excluded_file_ids)
        }
        
    except (ValidationException, FileProcessingException, DatabaseException):
        raise
    except Exception as e:
        duration = time.time() - start_time
        log_error(e, context="process_general_chat", request_id=request_id, duration=duration)
        raise DatabaseException("General chat request failed", {"duration": duration})