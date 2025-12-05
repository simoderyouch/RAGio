"""
Context Assembly Service for final context preparation.
Handles deduplication, merging, and token budget management.
"""

import time
from typing import List, Dict, Set, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from app.utils.logger import log_info, log_error, log_warning, log_performance


@dataclass
class AssembledContext:
    """Assembled context ready for LLM consumption."""
    chunks: List  # List[RetrievedChunk]
    total_tokens: int
    file_sources: List[Dict]  # List of unique source files used
    
    def get_text(self, separator: str = "\n\n---\n\n") -> str:
        """Get concatenated text from all chunks."""
        return separator.join(chunk.text for chunk in self.chunks)
    
    def get_source_attribution(self) -> str:
        """Get formatted source attribution string."""
        if not self.file_sources:
            return ""
        
        sources = []
        for source in self.file_sources:
            name = source.get("file_name", "Unknown")
            pages = source.get("pages", [])
            if pages:
                page_str = ", ".join(str(p) for p in sorted(pages))
                sources.append(f"- {name} (pages: {page_str})")
            else:
                sources.append(f"- {name}")
        
        return "Sources:\n" + "\n".join(sources)
    
    def to_documents(self) -> List:
        """Convert to LangChain-compatible Document format."""
        from langchain_core.documents import Document
        
        return [
            Document(
                page_content=chunk.text,
                metadata={
                    "file_id": chunk.file_id,
                    "file_name": chunk.file_name,
                    "page": chunk.page,
                    "chunk_id": chunk.chunk_id,
                    "score": chunk.score
                }
            )
            for chunk in self.chunks
        ]


class ContextAssembler:
    """
    Assembles final context from retrieved and ranked chunks.
    
    Features:
    - Semantic deduplication
    - Adjacent chunk merging
    - Token budget management
    - Metadata preservation
    - Source attribution
    """
    
    def __init__(
        self,
        similarity_threshold: float = 0.85,
        chars_per_token: int = 4
    ):
        """
        Initialize context assembler.
        
        Args:
            similarity_threshold: Threshold for considering chunks as duplicates
            chars_per_token: Approximate characters per token for budget estimation
        """
        self.similarity_threshold = similarity_threshold
        self.chars_per_token = chars_per_token
    
    def assemble(
        self,
        chunks: List,  # List[RetrievedChunk]
        max_tokens: int = 8000,
        merge_adjacent: bool = True,
        deduplicate: bool = True
    ) -> AssembledContext:
        """
        Assemble final context from chunks.
        
        Args:
            chunks: List of RetrievedChunk objects
            max_tokens: Maximum token budget
            merge_adjacent: Whether to merge adjacent chunks
            deduplicate: Whether to remove duplicate chunks
            
        Returns:
            AssembledContext with processed chunks
        """
        start_time = time.time()
        
        if not chunks:
            return AssembledContext(chunks=[], total_tokens=0, file_sources=[])
        
        try:
            log_info(
                f"Assembling context from {len(chunks)} chunks",
                context="context_assembly",
                max_tokens=max_tokens
            )
            
            processed = chunks.copy()
            
            # Step 1: Deduplicate
            if deduplicate:
                processed = self.deduplicate(processed)
                log_info(
                    f"After deduplication: {len(processed)} chunks",
                    context="context_assembly"
                )
            
            # Step 2: Merge adjacent chunks
            if merge_adjacent:
                processed = self.merge_adjacent_chunks(processed)
                log_info(
                    f"After merging: {len(processed)} chunks",
                    context="context_assembly"
                )
            
            # Step 3: Truncate to token budget
            processed = self.truncate_to_budget(processed, max_tokens)
            
            # Step 4: Calculate final token count
            total_tokens = self._estimate_tokens(processed)
            
            # Step 5: Extract source information
            file_sources = self._extract_sources(processed)
            
            result = AssembledContext(
                chunks=processed,
                total_tokens=total_tokens,
                file_sources=file_sources
            )
            
            duration = time.time() - start_time
            log_performance(
                "Context assembly completed",
                duration,
                input_chunks=len(chunks),
                output_chunks=len(processed),
                total_tokens=total_tokens,
                num_sources=len(file_sources)
            )
            
            return result
            
        except Exception as e:
            log_error(e, context="context_assembly")
            # Return original chunks on failure
            return AssembledContext(
                chunks=chunks[:10],
                total_tokens=self._estimate_tokens(chunks[:10]),
                file_sources=self._extract_sources(chunks[:10])
            )
    
    def deduplicate(self, chunks: List) -> List:
        """
        Remove duplicate or near-duplicate chunks.
        
        Uses text similarity to identify duplicates.
        Keeps the chunk with the higher score.
        """
        if len(chunks) <= 1:
            return chunks
        
        # Sort by score descending to keep best versions
        sorted_chunks = sorted(chunks, key=lambda x: x.score, reverse=True)
        
        keep = []
        seen_texts: List[str] = []
        
        for chunk in sorted_chunks:
            text = chunk.text.strip()
            
            # Check similarity with kept chunks
            is_duplicate = False
            for seen in seen_texts:
                similarity = self._text_similarity(text, seen)
                if similarity >= self.similarity_threshold:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                keep.append(chunk)
                seen_texts.append(text)
        
        return keep
    
    def merge_adjacent_chunks(self, chunks: List) -> List:
        """
        Merge adjacent chunks from the same file and page.
        
        This helps maintain context continuity.
        """
        if len(chunks) <= 1:
            return chunks
        
        # Group by file_id and sort by page/chunk_index
        grouped: Dict[int, List] = {}
        for chunk in chunks:
            file_id = chunk.file_id
            if file_id not in grouped:
                grouped[file_id] = []
            grouped[file_id].append(chunk)
        
        merged = []
        
        for file_id, file_chunks in grouped.items():
            # Sort by page and chunk_index
            file_chunks.sort(key=lambda x: (x.page, x.chunk_index))
            
            current_merged = None
            
            for chunk in file_chunks:
                if current_merged is None:
                    current_merged = chunk
                    continue
                
                # Check if chunks are adjacent (same page, consecutive index)
                if (chunk.page == current_merged.page and 
                    chunk.chunk_index == current_merged.chunk_index + 1):
                    # Merge: combine text, keep better score
                    current_merged.text = current_merged.text + "\n\n" + chunk.text
                    current_merged.score = max(current_merged.score, chunk.score)
                else:
                    # Not adjacent, save current and start new
                    merged.append(current_merged)
                    current_merged = chunk
            
            # Don't forget the last one
            if current_merged is not None:
                merged.append(current_merged)
        
        # Re-sort by score
        merged.sort(key=lambda x: x.score, reverse=True)
        
        return merged
    
    def truncate_to_budget(self, chunks: List, max_tokens: int) -> List:
        """
        Truncate chunks to fit within token budget.
        
        Prioritizes chunks by score.
        """
        if not chunks:
            return []
        
        result = []
        current_tokens = 0
        
        # Chunks should already be sorted by score
        for chunk in chunks:
            chunk_tokens = self._estimate_tokens_text(chunk.text)
            
            if current_tokens + chunk_tokens <= max_tokens:
                result.append(chunk)
                current_tokens += chunk_tokens
            elif current_tokens < max_tokens:
                # Try to fit partial chunk
                remaining_tokens = max_tokens - current_tokens
                remaining_chars = remaining_tokens * self.chars_per_token
                
                if remaining_chars > 100:  # Only include if meaningful
                    # Truncate chunk text
                    truncated_text = chunk.text[:remaining_chars]
                    # Try to end at sentence boundary
                    last_period = truncated_text.rfind('.')
                    if last_period > remaining_chars * 0.5:
                        truncated_text = truncated_text[:last_period + 1]
                    
                    chunk.text = truncated_text + "..."
                    result.append(chunk)
                
                break
            else:
                break
        
        return result
    
    def _estimate_tokens(self, chunks: List) -> int:
        """Estimate total tokens in chunks."""
        return sum(self._estimate_tokens_text(c.text) for c in chunks)
    
    def _estimate_tokens_text(self, text: str) -> int:
        """Estimate tokens in text."""
        return len(text) // self.chars_per_token
    
    def _text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using sequence matching.
        
        For performance, only compares first 500 chars.
        """
        # Truncate for performance
        t1 = text1[:500].lower()
        t2 = text2[:500].lower()
        
        return SequenceMatcher(None, t1, t2).ratio()
    
    def _extract_sources(self, chunks: List) -> List[Dict]:
        """Extract unique source file information."""
        sources: Dict[int, Dict] = {}
        
        for chunk in chunks:
            file_id = chunk.file_id
            
            if file_id not in sources:
                sources[file_id] = {
                    "file_id": file_id,
                    "file_name": chunk.file_name,
                    "pages": set()
                }
            
            if chunk.page:
                sources[file_id]["pages"].add(chunk.page)
        
        # Convert page sets to sorted lists
        result = []
        for source in sources.values():
            result.append({
                "file_id": source["file_id"],
                "file_name": source["file_name"],
                "pages": sorted(list(source["pages"]))
            })
        
        return result


# Singleton instance
_assembler_instance: Optional[ContextAssembler] = None


def get_context_assembler() -> ContextAssembler:
    """Get singleton context assembler instance."""
    global _assembler_instance
    if _assembler_instance is None:
        _assembler_instance = ContextAssembler()
    return _assembler_instance

