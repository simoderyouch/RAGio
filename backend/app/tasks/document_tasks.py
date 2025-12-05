"""
Background tasks for document processing using Celery.
"""
import asyncio
from celery import Task
from celery_app import celery_app
from sqlalchemy.orm import Session
from datetime import datetime
import time
import json

from app.db.database import SessionLocal
from app.db.models import UploadedFile, Chat
from app.utils.minio import initialize_minio
from app.utils.logger import log_info, log_error, log_warning, log_performance
from app.middleware.error_handler import FileProcessingException, ValidationException
from app.utils.observability import get_observability_client, OBSERVABILITY_ENABLED, generate_trace_id
from minio.error import S3Error

# Lazy imports for document processing services (only needed when task executes, not for discovery)
# These are imported inside the task functions to avoid breaking Celery Beat/ClickHouse worker imports
MinIOPyMuPDFLoader = None
MinIOTextLoader = None
parse_minio_path = None
process_document_qdrant = None
get_user_collection_name = None
get_rag_pipeline = None
FAST_CONFIG = None
generate_summary_chunked = None
generate_questions_chunked = None

def _lazy_import_document_services():
    """Lazy import document processing services - only import when actually needed."""
    global MinIOPyMuPDFLoader, MinIOTextLoader, parse_minio_path, process_document_qdrant
    global get_user_collection_name, get_rag_pipeline, FAST_CONFIG
    global generate_summary_chunked, generate_questions_chunked
    
    if MinIOPyMuPDFLoader is None:
        try:
            from app.utils.MinIOPyMuPDFLoader import MinIOPyMuPDFLoader
            from app.utils.MinIOTextLoader import MinIOTextLoader
            from app.utils.parse_minio_path import parse_minio_path
            from app.services.document_service import (
                process_document_qdrant, 
                get_user_collection_name
            )
            from app.services.rag_pipeline import get_rag_pipeline, FAST_CONFIG
            from app.services.chat_service import generate_summary_chunked, generate_questions_chunked
        except ImportError as e:
            # In lightweight images, these imports may fail
            # Tasks will fail gracefully if executed
            log_warning(f"Could not import document processing services: {e}", context="document_tasks")


class DatabaseTask(Task):
    """Base task with database session management."""
    _db = None

    @property
    def db(self):
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    def after_return(self, *args, **kwargs):
        """Close database session after task completion."""
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(bind=True, base=DatabaseTask, name="app.tasks.document_tasks.process_document_background")
def process_document_background(self, file_id: int, user_id: int):
    """
    Background task to process a document:
    - Load from MinIO
    - Process with Qdrant embeddings
    - Generate summary and questions
    - Save results to database
    
    Args:
        file_id: ID of the uploaded file to process
        user_id: ID of the user who owns the file
    
    Returns:
        dict: Processing results including summary, questions, and metadata
    """
    # Lazy import document processing services (only when task executes)
    _lazy_import_document_services()
    
    # Check if imports succeeded
    if (MinIOPyMuPDFLoader is None or MinIOTextLoader is None or 
        process_document_qdrant is None):
        error_msg = "Document processing services not available (missing dependencies)"
        log_error(error_msg, context="background_task", file_id=file_id, user_id=user_id)
        raise FileProcessingException(error_msg, {"file_id": file_id})
    
    start_time = time.time()
    task_id = self.request.id
    trace_id = generate_trace_id()
    db: Session = self.db
    minio_client = initialize_minio()
    
    # Push task started event
    if OBSERVABILITY_ENABLED:
        try:
            obs_client = get_observability_client()
            obs_client.push_system_event(
                event_type="celery_task_started",
                task_id=task_id,
                user_id=user_id,
                file_id=file_id,
                status="started",
                duration_ms=0.0,
                trace_id=trace_id
            )
        except Exception:
            pass
    
    try:
        log_info(
            "Background document processing started",
            context="background_task",
            task_id=task_id,
            file_id=file_id,
            user_id=user_id
        )
        
        # Update status to processing
        uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
        if not uploaded_file:
            error_msg = f"File not found: {file_id}"
            log_error(
                error_msg,
                context="background_task",
                task_id=self.request.id,
                file_id=file_id
            )
            raise ValidationException(error_msg, {"file_id": file_id})
        
        uploaded_file.processing_status = "processing"
        uploaded_file.task_id = self.request.id
        db.commit()
        
        # Parse MinIO path
        if not uploaded_file.file_path or not uploaded_file.file_path.startswith('/minio/'):
            error_msg = f"Invalid file path format: {uploaded_file.file_path}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            raise ValidationException(error_msg, {"file_path": uploaded_file.file_path})
        
        bucket_name, object_name = parse_minio_path(uploaded_file.file_path)
        
        # Verify object exists in MinIO
        try:
            minio_client.stat_object(bucket_name=bucket_name, object_name=object_name)
            log_info(
                "File found in MinIO storage",
                context="background_task",
                task_id=self.request.id,
                bucket_name=bucket_name,
                object_name=object_name
            )
        except S3Error as e:
            error_msg = f"File not found in storage: {str(e)}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            log_error(
                e,
                context="background_task",
                task_id=self.request.id,
                bucket_name=bucket_name,
                object_name=object_name
            )
            raise FileProcessingException(error_msg, {"bucket": bucket_name, "object": object_name})
        
        # Load the document based on file type
        try:
            # Get file type from database or infer from filename
            file_type_db = (uploaded_file.file_type or "").upper().strip()
            file_extension = ""
            if '.' in uploaded_file.file_name:
                file_extension = uploaded_file.file_name.rsplit('.', 1)[-1].lower().strip()
            
            # Determine actual file type (prefer extension if file_type is missing)
            if file_extension:
                file_type = file_extension.upper()
            elif file_type_db:
                file_type = file_type_db
            else:
                # Default to PDF if we can't determine
                file_type = "PDF"
                log_warning(
                    "Could not determine file type, defaulting to PDF",
                    context="background_task",
                    task_id=self.request.id,
                    file_name=uploaded_file.file_name
                )
            
            # Select appropriate loader based on file type
            if file_type == 'PDF':
                loader = MinIOPyMuPDFLoader(minio_client, bucket_name, object_name)
                log_info(
                    "Using PDF loader",
                    context="background_task",
                    task_id=self.request.id,
                    file_type=file_type,
                    file_name=uploaded_file.file_name
                )
            elif file_type in ['TXT', 'CSV', 'MD']:
                # Use lowercase extension for the loader
                loader_extension = file_extension if file_extension else file_type.lower()
                loader = MinIOTextLoader(minio_client, bucket_name, object_name, file_type=loader_extension)
                log_info(
                    f"Using text loader for {file_type}",
                    context="background_task",
                    task_id=self.request.id,
                    file_type=file_type,
                    file_extension=loader_extension,
                    file_name=uploaded_file.file_name
                )
            else:
                # Default to PDF loader for unknown types (backward compatibility)
                log_warning(
                    f"Unknown file type {file_type}, attempting PDF loader",
                    context="background_task",
                    task_id=self.request.id,
                    file_type=file_type,
                    file_name=uploaded_file.file_name
                )
                loader = MinIOPyMuPDFLoader(minio_client, bucket_name, object_name)
            
            documents = loader.load()
            log_info(
                "Document loaded successfully",
                context="background_task",
                task_id=self.request.id,
                num_documents=len(documents),
                file_type=file_type
            )
        except Exception as e:
            error_msg = f"Failed to load document: {str(e)}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            log_error(
                e,
                context="background_task",
                task_id=self.request.id,
                file_id=file_id,
                file_type=uploaded_file.file_type
            )
            raise FileProcessingException(error_msg, {"file_id": file_id})
        
        # Process document with Qdrant (unified collection)
        try:
            # Use asyncio.run() for proper async execution in sync context
            # Pass user_id, file_id, and file_name for unified collection architecture
            result = asyncio.run(process_document_qdrant(
                documents=documents,
                user_id=user_id,
                file_id=file_id,
                file_name=uploaded_file.file_name
            ))
            
            # Store the unified collection name (same for all user docs)
            uploaded_file.embedding_path = result["collection"]
            db.commit()
            log_info(
                "Document processed with unified Qdrant collection",
                context="background_task",
                task_id=self.request.id,
                collection=result["collection"],
                points_inserted=result["points_inserted"],
                user_id=user_id,
                file_id=file_id
            )
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            log_error(
                e,
                context="background_task",
                task_id=self.request.id,
                file_id=file_id
            )
            raise FileProcessingException(error_msg, {"file_id": file_id})
        
        try:
            # Get file name without extension for logging
            file_name_without_ext = uploaded_file.file_name.rsplit('.', 1)[0]
            


            rag_pipeline = get_rag_pipeline(fast=True)
            
            context = asyncio.run(rag_pipeline.retrieve_as_documents(
                query="provide a comprehensive summary of the main topics and key points in this document",
                user_id=user_id,
                file_ids=[file_id],  # Filter to only this document
                max_tokens=10000
            ))
            
            # Check if context is a string (error message) or list of documents
            if isinstance(context, str):
                log_warning(
                    f"RAG pipeline returned error: {context}",
                    context="background_task",
                    task_id=self.request.id,
                    file_id=file_id
                )
                summary = f"Unable to generate summary: {context}"
                questions = [f"Unable to generate questions: {context}"]
            else:
                # Use asyncio.run() for proper async execution in sync context
                summary = asyncio.run(generate_summary_chunked(file_name_without_ext, context))
                questions = asyncio.run(generate_questions_chunked(file_name_without_ext, context))

           
            log_info(
                "Summary and questions generated",
                context="background_task",
                task_id=self.request.id,
                summary_length=len(summary),
                questions_count=len(questions) if isinstance(questions, list) else 0
            )
        except Exception as e:
            error_msg = f"Failed to generate response: {str(e)}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            log_error(
                e,
                context="background_task",
                task_id=self.request.id,
                file_id=file_id
            )
            raise FileProcessingException(error_msg, {"file_id": file_id})
        
        # Save to database
        try:
            db.add(Chat(
                response=summary,
                user_id=user_id,
                uploaded_file_id=file_id,
                created_at_response=datetime.now()
            ))
            
            db.add(Chat(
                response=json.dumps(questions),
                user_id=user_id,
                uploaded_file_id=file_id,
                created_at_response=datetime.now()
            ))
            
            # Update file status to completed
            uploaded_file.processing_status = "completed"
            uploaded_file.error_message = None
            db.commit()
            
            log_info(
                "Chat records saved to database",
                context="background_task",
                task_id=self.request.id,
                user_id=user_id,
                file_id=file_id
            )
        except Exception as e:
            error_msg = f"Failed to save chat records: {str(e)}"
            uploaded_file.processing_status = "failed"
            uploaded_file.error_message = error_msg
            db.commit()
            log_error(
                e,
                context="background_task",
                task_id=self.request.id,
                user_id=user_id,
                file_id=file_id
            )
            raise
        
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # Push task completed event
        if OBSERVABILITY_ENABLED:
            try:
                obs_client = get_observability_client()
                obs_client.push_system_event(
                    event_type="celery_task_completed",
                    task_id=task_id,
                    user_id=user_id,
                    file_id=file_id,
                    status="success",
                    duration_ms=duration_ms,
                    trace_id=trace_id
                )
            except Exception:
                pass
        
        log_performance(
            "Background document processing completed",
            duration,
            task_id=self.request.id,
            file_id=file_id,
            user_id=user_id
        )
        
        return {
            "status": "completed",
            "file_id": file_id,
            "summary": summary,
            "questions": questions,
            "processing_time": f"{duration:.2f}s",
            "collection": uploaded_file.embedding_path
        }
        
    except Exception as e:
        duration = time.time() - start_time
        duration_ms = duration * 1000
        
        # Push task failed event
        if OBSERVABILITY_ENABLED:
            try:
                obs_client = get_observability_client()
                obs_client.push_system_event(
                    event_type="celery_task_failed",
                    task_id=task_id,
                    user_id=user_id,
                    file_id=file_id,
                    status="failed",
                    duration_ms=duration_ms,
                    error_code=type(e).__name__,
                    error_message=str(e),
                    trace_id=trace_id
                )
            except Exception:
                pass
        
        # Update file status to failed if not already done
        try:
            uploaded_file = db.query(UploadedFile).filter(UploadedFile.id == file_id).first()
            if uploaded_file and uploaded_file.processing_status != "failed":
                uploaded_file.processing_status = "failed"
                uploaded_file.error_message = str(e)
                db.commit()
        except Exception as db_error:
            log_error(
                db_error,
                context="background_task",
                task_id=task_id,
                message="Failed to update error status in database"
            )
        
        log_error(
            e,
            context="background_task",
            task_id=task_id,
            file_id=file_id,
            user_id=user_id,
            duration=duration
        )
        
        # Re-raise to mark Celery task as failed
        raise


@celery_app.task(name="app.tasks.document_tasks.process_uploaded_file_task")
def process_uploaded_file_task(file_id: int, user_id: int):
    """
    Legacy task - redirects to new background processing task.
    Kept for backwards compatibility.
    """
    return process_document_background(file_id, user_id)


@celery_app.task(name="app.tasks.document_tasks.process_pdf_from_url_task")
def process_pdf_from_url_task(file_id: int, user_id: int):
    """
    Legacy task - redirects to new background processing task.
    Kept for backwards compatibility.
    """
    return process_document_background(file_id, user_id)
