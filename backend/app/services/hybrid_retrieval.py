"""
Hybrid Retrieval Service combining Dense and Sparse search.
Uses Reciprocal Rank Fusion (RRF) for score merging.
"""

import time
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field
from collections import defaultdict

from qdrant_client.http.models import Filter, FieldCondition, MatchAny, MatchValue, SparseVector as QdrantSparseVector

from app.config import encoder, qdrant_client
from app.services.document_service import get_user_collection_name
from app.services.sparse_encoder import get_sparse_encoder, SparseVector
from app.utils.logger import log_info, log_error, log_warning, log_performance


def _check_encoder_available():
    """Check if embedding encoder is available."""
    if encoder is None:
        log_warning(
            "Embedding encoder not available - models may not be loaded",
            context="hybrid_retrieval"
        )
        return False
    return True


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk with metadata."""
    text: str
    file_id: int
    file_name: str
    page: int
    chunk_id: str
    score: float = 0.0
    dense_score: float = 0.0
    sparse_score: float = 0.0
    source: str = ""
    chunk_index: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "text": self.text,
            "file_id": self.file_id,
            "file_name": self.file_name,
            "page": self.page,
            "chunk_id": self.chunk_id,
            "score": self.score,
            "source": self.source,
            "chunk_index": self.chunk_index
        }


class HybridRetriever:
    """
    Hybrid retrieval combining dense and sparse (BM25) search.
    
    Features:
    - Dense vector search using existing embeddings
    - Sparse BM25 search using Qdrant's sparse vectors
    - Reciprocal Rank Fusion (RRF) for score merging
    - Support for file filtering (include/exclude)
    - Multi-query expansion support
    """
    
    def __init__(
        self,
        rrf_k: int = 60,
        dense_weight: float = 0.6,
        sparse_weight: float = 0.4
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            rrf_k: RRF constant (default: 60)
            dense_weight: Weight for dense scores (default: 0.6)
            sparse_weight: Weight for sparse scores (default: 0.4)
        """
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight
        self.sparse_encoder = get_sparse_encoder()
    
    def retrieve(
        self,
        query: str,
        expanded_queries: List[str],
        user_id: int,
        file_ids: Optional[List[int]] = None,
        exclude_file_ids: Optional[List[int]] = None,
        top_k: int = 50,
        dense_top_k: int = 30,
        sparse_top_k: int = 30
    ) -> List[RetrievedChunk]:
        """
        Perform hybrid retrieval with dense and sparse search.
        
        Args:
            query: Original user query
            expanded_queries: List of expanded queries (includes original)
            user_id: User ID for collection lookup
            file_ids: Optional list of file IDs to include
            exclude_file_ids: Optional list of file IDs to exclude
            top_k: Number of final results to return
            dense_top_k: Number of results from dense search per query
            sparse_top_k: Number of results from sparse search per query
            
        Returns:
            List of RetrievedChunks sorted by fused score
        """
        start_time = time.time()
        collection_name = get_user_collection_name(user_id)
        
        try:
            log_info(
                "Starting hybrid retrieval",
                context="hybrid_retrieval",
                user_id=user_id,
                num_queries=len(expanded_queries),
                top_k=top_k
            )
            
            # Build filter
            query_filter = self._build_filter(file_ids, exclude_file_ids)
            
            # Collect results from all queries
            all_dense_results: Dict[str, Dict] = {}  # chunk_id -> result
            all_sparse_results: Dict[str, Dict] = {}
            
            # Run dense and sparse search for each expanded query
            for exp_query in expanded_queries:
                # Dense search
                dense_results = self._dense_search(
                    exp_query, 
                    collection_name, 
                    query_filter, 
                    dense_top_k
                )
                for result in dense_results:
                    chunk_id = result.get("chunk_id", "")
                    if chunk_id not in all_dense_results:
                        all_dense_results[chunk_id] = result
                    else:
                        # Keep higher score
                        if result.get("score", 0) > all_dense_results[chunk_id].get("score", 0):
                            all_dense_results[chunk_id] = result
                
                # Sparse search (BM25)
                sparse_results = self._sparse_search(
                    exp_query,
                    collection_name,
                    query_filter,
                    sparse_top_k
                )
                for result in sparse_results:
                    chunk_id = result.get("chunk_id", "")
                    if chunk_id not in all_sparse_results:
                        all_sparse_results[chunk_id] = result
                    else:
                        if result.get("score", 0) > all_sparse_results[chunk_id].get("score", 0):
                            all_sparse_results[chunk_id] = result
            
            # Merge results using RRF
            merged_results = self._rrf_merge(
                list(all_dense_results.values()),
                list(all_sparse_results.values())
            )
            
            # Convert to RetrievedChunk objects
            chunks = []
            for result in merged_results[:top_k]:
                chunk = RetrievedChunk(
                    text=result.get("text", ""),
                    file_id=result.get("file_id", 0),
                    file_name=result.get("file_name", "Unknown"),
                    page=result.get("page", 0),
                    chunk_id=result.get("chunk_id", ""),
                    score=result.get("fused_score", 0.0),
                    dense_score=result.get("dense_score", 0.0),
                    sparse_score=result.get("sparse_score", 0.0),
                    source=result.get("source", ""),
                    chunk_index=result.get("chunk_index", 0)
                )
                chunks.append(chunk)
            
            duration = time.time() - start_time
            log_performance(
                "Hybrid retrieval completed",
                duration,
                user_id=user_id,
                dense_results=len(all_dense_results),
                sparse_results=len(all_sparse_results),
                final_results=len(chunks)
            )
            
            return chunks
            
        except Exception as e:
            log_error(
                e,
                context="hybrid_retrieval",
                user_id=user_id,
                collection=collection_name
            )
            return []
    
    def _build_filter(
        self,
        file_ids: Optional[List[int]],
        exclude_file_ids: Optional[List[int]]
    ) -> Optional[Filter]:
        """Build Qdrant filter for file inclusion/exclusion."""
        if file_ids and len(file_ids) > 0:
            return Filter(
                must=[
                    FieldCondition(
                        key="file_id",
                        match=MatchAny(any=file_ids)
                    )
                ]
            )
        elif exclude_file_ids and len(exclude_file_ids) > 0:
            return Filter(
                must_not=[
                    FieldCondition(
                        key="file_id",
                        match=MatchAny(any=exclude_file_ids)
                    )
                ]
            )
        return None
    
    def _dense_search(
        self,
        query: str,
        collection_name: str,
        query_filter: Optional[Filter],
        top_k: int
    ) -> List[Dict]:
        """Perform dense vector search."""
        try:
            # Check if encoder is available
            if not _check_encoder_available():
                log_warning(
                    "Cannot perform dense search - encoder not available",
                    context="dense_search"
                )
                return []
            
            # Check if collection exists
            collections = qdrant_client.get_collections().collections
            if collection_name not in [c.name for c in collections]:
                log_warning(
                    f"Collection {collection_name} not found",
                    context="dense_search"
                )
                return []
            
            # Embed query
            query_vector = encoder.embed_query(query)
            
            # Check if collection uses named vectors
            from app.services.document_service import check_collection_has_named_vectors
            has_named_vectors = check_collection_has_named_vectors(collection_name)
            
            # Search (use named vector if collection supports it)
            if has_named_vectors:
                results = qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    using="dense",  # Use named "dense" vector
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False
                ).points
            else:
                results = qdrant_client.query_points(
                    collection_name=collection_name,
                    query=query_vector,
                    query_filter=query_filter,
                    limit=top_k,
                    with_payload=True,
                    with_vectors=False
                ).points
            
            # Convert to dict format
            output = []
            for result in results:
                if not result.payload:
                    continue
                
                output.append({
                    "text": result.payload.get("text", ""),
                    "file_id": result.payload.get("file_id", 0),
                    "file_name": result.payload.get("file_name", "Unknown"),
                    "page": result.payload.get("page", 0),
                    "chunk_id": result.payload.get("chunk_id", str(result.id)),
                    "score": result.score,
                    "source": result.payload.get("source", ""),
                    "chunk_index": result.payload.get("chunk_index", 0)
                })
            
            return output
            
        except Exception as e:
            log_error(e, context="dense_search", collection=collection_name)
            return []
    
    def _sparse_search(
        self,
        query: str,
        collection_name: str,
        query_filter: Optional[Filter],
        top_k: int
    ) -> List[Dict]:
        """
        Perform sparse BM25 search.
        Falls back to dense search if sparse vectors not available.
        """
        try:
            # Check if collection has sparse vectors using the same logic as document_service
            from app.services.document_service import check_collection_has_sparse
            has_sparse = check_collection_has_sparse(collection_name)
            
            if not has_sparse:
                # Fall back to dense search with different parameters
                # This ensures we still get results even without sparse vectors
                log_info(
                    "Sparse vectors not available, using dense fallback",
                    context="sparse_search",
                    collection=collection_name
                )
                return self._dense_search(query, collection_name, query_filter, top_k)
            
            # Encode query for sparse search
            sparse_vector = self.sparse_encoder.encode_query(query)
            
            if not sparse_vector.indices:
                return []
            
            # Convert to Qdrant's SparseVector type
            qdrant_sparse = QdrantSparseVector(
                indices=sparse_vector.indices,
                values=sparse_vector.values
            )
            
          
            results = qdrant_client.query_points(
                collection_name=collection_name,
                query=qdrant_sparse,
                using="sparse",  
                query_filter=query_filter,
                limit=top_k,
                with_payload=True,
                with_vectors=False
            ).points
            
            # Convert to dict format
            output = []
            for result in results:
                if not result.payload:
                    continue
                
                output.append({
                    "text": result.payload.get("text", ""),
                    "file_id": result.payload.get("file_id", 0),
                    "file_name": result.payload.get("file_name", "Unknown"),
                    "page": result.payload.get("page", 0),
                    "chunk_id": result.payload.get("chunk_id", str(result.id)),
                    "score": result.score,
                    "source": result.payload.get("source", ""),
                    "chunk_index": result.payload.get("chunk_index", 0)
                })
            
            return output
            
        except Exception as e:
            log_warning(
                f"Sparse search failed, falling back to dense: {e}",
                context="sparse_search"
            )
            return self._dense_search(query, collection_name, query_filter, top_k)
    
    def _rrf_merge(
        self,
        dense_results: List[Dict],
        sparse_results: List[Dict]
    ) -> List[Dict]:
        """
        Merge dense and sparse results using Reciprocal Rank Fusion.
        
        RRF score = sum(1 / (k + rank)) for each result list
        """
        # Build rank dictionaries
        dense_ranks = {}
        for rank, result in enumerate(sorted(
            dense_results, 
            key=lambda x: x.get("score", 0), 
            reverse=True
        )):
            chunk_id = result.get("chunk_id", "")
            dense_ranks[chunk_id] = {
                "rank": rank + 1,
                "score": result.get("score", 0),
                "data": result
            }
        
        sparse_ranks = {}
        for rank, result in enumerate(sorted(
            sparse_results,
            key=lambda x: x.get("score", 0),
            reverse=True
        )):
            chunk_id = result.get("chunk_id", "")
            sparse_ranks[chunk_id] = {
                "rank": rank + 1,
                "score": result.get("score", 0),
                "data": result
            }
        
        # Calculate RRF scores
        all_chunk_ids = set(dense_ranks.keys()) | set(sparse_ranks.keys())
        fused_results = []
        
        for chunk_id in all_chunk_ids:
            dense_info = dense_ranks.get(chunk_id)
            sparse_info = sparse_ranks.get(chunk_id)
            
            # RRF score calculation
            rrf_score = 0.0
            dense_score = 0.0
            sparse_score = 0.0
            
            if dense_info:
                rrf_score += self.dense_weight * (1.0 / (self.rrf_k + dense_info["rank"]))
                dense_score = dense_info["score"]
            
            if sparse_info:
                rrf_score += self.sparse_weight * (1.0 / (self.rrf_k + sparse_info["rank"]))
                sparse_score = sparse_info["score"]
            
            # Get the data (prefer dense if both exist)
            data = (dense_info or sparse_info)["data"].copy()
            data["fused_score"] = rrf_score
            data["dense_score"] = dense_score
            data["sparse_score"] = sparse_score
            
            fused_results.append(data)
        
        # Sort by fused score
        fused_results.sort(key=lambda x: x.get("fused_score", 0), reverse=True)
        
        return fused_results


# Singleton instance
_hybrid_retriever: Optional[HybridRetriever] = None


def get_hybrid_retriever() -> HybridRetriever:
    """Get singleton hybrid retriever instance."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever

