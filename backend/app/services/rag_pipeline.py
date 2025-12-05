"""
Modern RAG Pipeline - Main entry point for all retrieval operations.

This module integrates all RAG components into a unified pipeline:
1. Query Expansion (LLM-based)
2. Hybrid Retrieval (Dense + Sparse/BM25)
3. BGE Re-ranking
4. Cross-Encoder Verification
5. Context Assembly

Replaces the old retrieved_docs_unified() function.
"""

import time
from typing import List, Optional, Union
from dataclasses import dataclass

from langchain_core.documents import Document

from app.services.query_expansion import get_query_expander, QueryExpander
from app.services.hybrid_retrieval import get_hybrid_retriever, HybridRetriever, RetrievedChunk
from app.services.reranker import get_reranker, BGEReranker
from app.services.cross_encoder_verifier import get_cross_encoder_verifier, CrossEncoderVerifier
from app.services.context_assembly import get_context_assembler, ContextAssembler, AssembledContext
from app.utils.logger import log_info, log_error, log_warning, log_performance
from app.utils.observability import get_observability_client, OBSERVABILITY_ENABLED, generate_trace_id


@dataclass
class RAGConfig:
    """Configuration for RAG pipeline."""
    # Query expansion
    enable_expansion: bool = True
    num_expansions: int = 4
    
    # Hybrid retrieval
    hybrid_top_k: int = 50
    dense_top_k: int = 30
    sparse_top_k: int = 30
    
    # Re-ranking
    enable_reranking: bool = True
    rerank_top_k: int = 20
    
    # Cross-encoder verification
    enable_verification: bool = True
    verify_top_k: int = 10
    verify_threshold: float = 0.0
    
    # Context assembly
    max_tokens: int = 8000
    enable_dedup: bool = True
    enable_merge: bool = True


# Default configuration
DEFAULT_CONFIG = RAGConfig()

# Lightweight config for faster responses (skip heavy re-ranking)
FAST_CONFIG = RAGConfig(
    enable_expansion=True,
    num_expansions=2,
    hybrid_top_k=30,
    enable_reranking=False,
    enable_verification=False,
    max_tokens=5000
)


class RAGPipeline:
    """
    Modern multi-stage RAG pipeline.
    
    Pipeline stages:
    1. Query Expansion: Generate query reformulations using LLM
    2. Hybrid Retrieval: Combine dense and sparse search with RRF fusion
    3. BGE Re-ranking: Late interaction re-ranking for quality
    4. Cross-Encoder: Final precision verification
    5. Context Assembly: Deduplicate, merge, and manage token budget
    
    Features:
    - Configurable stages (can disable any stage)
    - CPU-optimized for production use
    - Lazy model loading
    - Comprehensive logging
    """
    
    def __init__(self, config: Optional[RAGConfig] = None):
        """
        Initialize RAG pipeline.
        
        Args:
            config: Pipeline configuration (uses default if None)
        """
        self.config = config or DEFAULT_CONFIG
        
        # Components are lazily loaded
        self._query_expander: Optional[QueryExpander] = None
        self._hybrid_retriever: Optional[HybridRetriever] = None
        self._reranker: Optional[BGEReranker] = None
        self._verifier: Optional[CrossEncoderVerifier] = None
        self._assembler: Optional[ContextAssembler] = None
    
    @property
    def query_expander(self) -> QueryExpander:
        if self._query_expander is None:
            self._query_expander = get_query_expander()
        return self._query_expander
    
    @property
    def hybrid_retriever(self) -> HybridRetriever:
        if self._hybrid_retriever is None:
            self._hybrid_retriever = get_hybrid_retriever()
        return self._hybrid_retriever
    
    @property
    def reranker(self) -> BGEReranker:
        if self._reranker is None:
            self._reranker = get_reranker()
        return self._reranker
    
    @property
    def verifier(self) -> CrossEncoderVerifier:
        if self._verifier is None:
            self._verifier = get_cross_encoder_verifier()
        return self._verifier
    
    @property
    def assembler(self) -> ContextAssembler:
        if self._assembler is None:
            self._assembler = get_context_assembler()
        return self._assembler
    
    async def retrieve(
        self,
        query: str,
        user_id: int,
        file_ids: Optional[List[int]] = None,
        exclude_file_ids: Optional[List[int]] = None,
        max_tokens: Optional[int] = None,
        config: Optional[RAGConfig] = None
    ) -> AssembledContext:
        """
        Execute full RAG pipeline.
        
        Args:
            query: User search query
            user_id: User ID for collection lookup
            file_ids: Optional list of file IDs to include (None = all files)
            exclude_file_ids: Optional list of file IDs to exclude
            max_tokens: Override max token budget
            config: Override pipeline config
            
        Returns:
            AssembledContext with retrieved and processed chunks
        """
        start_time = time.time()
        cfg = config or self.config
        max_tokens = max_tokens or cfg.max_tokens
        trace_id = generate_trace_id()
        request_id = ""  # Can be passed from caller if available
        
        try:
            log_info(
                "Starting RAG pipeline",
                context="rag_pipeline",
                user_id=user_id,
                query_length=len(query),
                file_filter=bool(file_ids),
                exclude_filter=bool(exclude_file_ids)
            )
            
            # Stage 1: Query Expansion
            stage_start = time.time()
            if cfg.enable_expansion:
                try:
                    expanded_queries = await self.query_expander.expand(
                        query,
                        num_expansions=cfg.num_expansions
                    )
                    stage_duration = (time.time() - stage_start) * 1000
                    log_info(
                        f"Query expanded to {len(expanded_queries)} variants",
                        context="rag_pipeline"
                    )
                    
                    # Push telemetry
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="query_expansion",
                                stage_order=1,
                                duration_ms=stage_duration,
                                success=True,
                                candidates_count=len(expanded_queries),
                                chunks_retrieved=0,
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                except Exception as e:
                    stage_duration = (time.time() - stage_start) * 1000
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="query_expansion",
                                stage_order=1,
                                duration_ms=stage_duration,
                                success=False,
                                error_code="EXPANSION_ERROR",
                                error_message=str(e),
                                candidates_count=0,
                                chunks_retrieved=0,
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                    raise
            else:
                expanded_queries = [query]
            
            # Stage 2: Hybrid Retrieval
            stage_start = time.time()
            try:
                candidates = self.hybrid_retriever.retrieve(
                    query=query,
                    expanded_queries=expanded_queries,
                    user_id=user_id,
                    file_ids=file_ids,
                    exclude_file_ids=exclude_file_ids,
                    top_k=cfg.hybrid_top_k,
                    dense_top_k=cfg.dense_top_k,
                    sparse_top_k=cfg.sparse_top_k
                )
                stage_duration = (time.time() - stage_start) * 1000
                
                if not candidates:
                    log_warning(
                        "No candidates retrieved from hybrid search",
                        context="rag_pipeline",
                        user_id=user_id
                    )
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="hybrid_retrieval",
                                stage_order=2,
                                duration_ms=stage_duration,
                                success=True,
                                candidates_count=0,
                                chunks_retrieved=0,
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                    return AssembledContext(chunks=[], total_tokens=0, file_sources=[])
                
                log_info(
                    f"Hybrid retrieval returned {len(candidates)} candidates",
                    context="rag_pipeline"
                )
                
                # Push telemetry
                if OBSERVABILITY_ENABLED:
                    try:
                        obs_client = get_observability_client()
                        obs_client.push_rag_analytics(
                            user_id=user_id,
                            request_id=request_id,
                            operation="hybrid_retrieval",
                            stage_order=2,
                            duration_ms=stage_duration,
                            success=True,
                            candidates_count=len(candidates),
                            chunks_retrieved=len(candidates),
                            tokens_used=0,
                            file_ids=file_ids or [],
                            collection_name="",
                            trace_id=trace_id
                        )
                    except Exception:
                        pass
            except Exception as e:
                stage_duration = (time.time() - stage_start) * 1000
                if OBSERVABILITY_ENABLED:
                    try:
                        obs_client = get_observability_client()
                        obs_client.push_rag_analytics(
                            user_id=user_id,
                            request_id=request_id,
                            operation="hybrid_retrieval",
                            stage_order=2,
                            duration_ms=stage_duration,
                            success=False,
                            error_code="RETRIEVAL_ERROR",
                            error_message=str(e),
                            candidates_count=0,
                            chunks_retrieved=0,
                            tokens_used=0,
                            file_ids=file_ids or [],
                            collection_name="",
                            trace_id=trace_id
                        )
                    except Exception:
                        pass
                raise
            
            # Stage 3: BGE Re-ranking
            stage_start = time.time()
            if cfg.enable_reranking and len(candidates) > cfg.rerank_top_k:
                try:
                    reranked = self.reranker.rerank(
                        query=query,
                        chunks=candidates,
                        top_k=cfg.rerank_top_k
                    )
                    stage_duration = (time.time() - stage_start) * 1000
                    log_info(
                        f"Re-ranking reduced to {len(reranked)} chunks",
                        context="rag_pipeline"
                    )
                    
                    # Push telemetry
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="reranking",
                                stage_order=3,
                                duration_ms=stage_duration,
                                success=True,
                                candidates_count=len(candidates),
                                chunks_retrieved=len(reranked),
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                except Exception as e:
                    stage_duration = (time.time() - stage_start) * 1000
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="reranking",
                                stage_order=3,
                                duration_ms=stage_duration,
                                success=False,
                                error_code="RERANKING_ERROR",
                                error_message=str(e),
                                candidates_count=len(candidates),
                                chunks_retrieved=0,
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                    # Fallback to top-k without reranking
                    reranked = candidates[:cfg.rerank_top_k]
            else:
                reranked = candidates[:cfg.rerank_top_k]
            
            # Stage 4: Cross-Encoder Verification
            stage_start = time.time()
            if cfg.enable_verification and len(reranked) > cfg.verify_top_k:
                try:
                    verified = self.verifier.verify(
                        query=query,
                        chunks=reranked,
                        threshold=cfg.verify_threshold,
                        top_k=cfg.verify_top_k
                    )
                    stage_duration = (time.time() - stage_start) * 1000
                    log_info(
                        f"Verification returned {len(verified)} chunks",
                        context="rag_pipeline"
                    )
                    
                    # Push telemetry
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="cross_encoder",
                                stage_order=4,
                                duration_ms=stage_duration,
                                success=True,
                                candidates_count=len(reranked),
                                chunks_retrieved=len(verified),
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                except Exception as e:
                    stage_duration = (time.time() - stage_start) * 1000
                    if OBSERVABILITY_ENABLED:
                        try:
                            obs_client = get_observability_client()
                            obs_client.push_rag_analytics(
                                user_id=user_id,
                                request_id=request_id,
                                operation="cross_encoder",
                                stage_order=4,
                                duration_ms=stage_duration,
                                success=False,
                                error_code="VERIFICATION_ERROR",
                                error_message=str(e),
                                candidates_count=len(reranked),
                                chunks_retrieved=0,
                                tokens_used=0,
                                file_ids=file_ids or [],
                                collection_name="",
                                trace_id=trace_id
                            )
                        except Exception:
                            pass
                    # Fallback to top-k without verification
                    verified = reranked[:cfg.verify_top_k]
            else:
                verified = reranked[:cfg.verify_top_k]
            
            # Stage 5: Context Assembly
            stage_start = time.time()
            try:
                context = self.assembler.assemble(
                    chunks=verified,
                    max_tokens=max_tokens,
                    deduplicate=cfg.enable_dedup,
                    merge_adjacent=cfg.enable_merge
                )
                stage_duration = (time.time() - stage_start) * 1000
                
                # Push telemetry
                if OBSERVABILITY_ENABLED:
                    try:
                        obs_client = get_observability_client()
                        obs_client.push_rag_analytics(
                            user_id=user_id,
                            request_id=request_id,
                            operation="context_assembly",
                            stage_order=5,
                            duration_ms=stage_duration,
                            success=True,
                            candidates_count=len(verified),
                            chunks_retrieved=len(context.chunks) if hasattr(context, 'chunks') else 0,
                            tokens_used=context.total_tokens if hasattr(context, 'total_tokens') else 0,
                            file_ids=file_ids or [],
                            collection_name="",
                            trace_id=trace_id
                        )
                    except Exception:
                        pass
            except Exception as e:
                stage_duration = (time.time() - stage_start) * 1000
                if OBSERVABILITY_ENABLED:
                    try:
                        obs_client = get_observability_client()
                        obs_client.push_rag_analytics(
                            user_id=user_id,
                            request_id=request_id,
                            operation="context_assembly",
                            stage_order=5,
                            duration_ms=stage_duration,
                            success=False,
                            error_code="ASSEMBLY_ERROR",
                            error_message=str(e),
                            candidates_count=len(verified),
                            chunks_retrieved=0,
                            tokens_used=0,
                            file_ids=file_ids or [],
                            collection_name="",
                            trace_id=trace_id
                        )
                    except Exception:
                        pass
                raise
            
            duration = time.time() - start_time
            log_performance(
                "RAG pipeline completed",
                duration,
                user_id=user_id,
                candidates=len(candidates),
                reranked=len(reranked),
                verified=len(verified),
                final_chunks=len(context.chunks),
                total_tokens=context.total_tokens
            )
            
            return context
            
        except Exception as e:
            log_error(
                e,
                context="rag_pipeline",
                user_id=user_id,
                query=query[:100]
            )
            # Return empty context on failure
            return AssembledContext(chunks=[], total_tokens=0, file_sources=[])
    
    async def retrieve_as_documents(
        self,
        query: str,
        user_id: int,
        file_ids: Optional[List[int]] = None,
        exclude_file_ids: Optional[List[int]] = None,
        max_tokens: Optional[int] = None,
        config: Optional[RAGConfig] = None
    ) -> Union[List[Document], str]:
        """
        Execute RAG pipeline and return as LangChain Documents.
        
        This is a drop-in replacement for the old retrieved_docs_unified().
        
        Returns:
            List of LangChain Document objects, or error string
        """
        try:
            context = await self.retrieve(
                query=query,
                user_id=user_id,
                file_ids=file_ids,
                exclude_file_ids=exclude_file_ids,
                max_tokens=max_tokens,
                config=config
            )
            
            if not context.chunks:
                return "No relevant documents found."
            
            return context.to_documents()
            
        except Exception as e:
            log_error(e, context="rag_pipeline", operation="retrieve_as_documents")
            return f"Error retrieving documents: {str(e)}"
    
    def retrieve_sync(
        self,
        query: str,
        user_id: int,
        file_ids: Optional[List[int]] = None,
        exclude_file_ids: Optional[List[int]] = None,
        max_tokens: Optional[int] = None,
        config: Optional[RAGConfig] = None
    ) -> AssembledContext:
        """
        Synchronous version of retrieve for non-async contexts.
        
        Note: Query expansion will use synchronous LLM call.
        """
        import asyncio
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop is not None:
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self.retrieve(
                        query, user_id, file_ids, exclude_file_ids, max_tokens, config
                    )
                )
                return future.result()
        else:
           
            return asyncio.run(
                self.retrieve(
                    query, user_id, file_ids, exclude_file_ids, max_tokens, config
                )
            )


# Singleton pipeline instances
_default_pipeline: Optional[RAGPipeline] = None
_fast_pipeline: Optional[RAGPipeline] = None


def get_rag_pipeline(fast: bool = False) -> RAGPipeline:
    """
    Get RAG pipeline instance.
    
    Args:
        fast: Use lightweight/fast configuration
        
    Returns:
        RAGPipeline instance
    """
    global _default_pipeline, _fast_pipeline
    
    if fast:
        if _fast_pipeline is None:
            _fast_pipeline = RAGPipeline(config=FAST_CONFIG)
        return _fast_pipeline
    else:
        if _default_pipeline is None:
            _default_pipeline = RAGPipeline(config=DEFAULT_CONFIG)
        return _default_pipeline


# Convenience function for backward compatibility
async def retrieve_with_rag(
    query: str,
    user_id: int,
    file_ids: Optional[List[int]] = None,
    exclude_file_ids: Optional[List[int]] = None,
    max_tokens: int = 8000,
    fast: bool = False
) -> Union[List[Document], str]:
    """
    Convenience function for RAG retrieval.
    
    Replaces retrieved_docs_unified() in existing code.
    
    Args:
        query: Search query
        user_id: User ID
        file_ids: Optional file filter
        exclude_file_ids: Optional file exclusion
        max_tokens: Token budget
        fast: Use fast/lightweight pipeline
        
    Returns:
        List of Documents or error string
    """
    pipeline = get_rag_pipeline(fast=fast)
    return await pipeline.retrieve_as_documents(
        query=query,
        user_id=user_id,
        file_ids=file_ids,
        exclude_file_ids=exclude_file_ids,
        max_tokens=max_tokens
    )

