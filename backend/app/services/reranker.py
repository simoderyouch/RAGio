

import os
import time
from typing import List, Optional, Tuple
from pathlib import Path
from app.config import RERANKER_MODEL
import torch

from app.utils.logger import log_info, log_error, log_warning, log_performance


# Lazy import to avoid loading model at startup
_cross_encoder = None
_model_load_attempted = False
_model_load_failed = False


def preload_model():
    """Preload the reranker model at startup."""
    _get_cross_encoder()


def _get_cross_encoder():
    """Lazy load the cross-encoder model with offline fallback."""
    global _cross_encoder, _model_load_attempted, _model_load_failed
    
    # Don't retry if we already failed
    if _model_load_failed:
        return None
    
    if _cross_encoder is None and not _model_load_attempted:
        _model_load_attempted = True
        
        try:
            import torch
            from sentence_transformers import CrossEncoder
            import os
            
            log_info(f"Loading reranker model: {RERANKER_MODEL}...", context="reranker")
            
            # Set torch to use optimal number of threads for CPU
            torch.set_num_threads(4)
            
            # In offline mode, try to use cached model path if available
            is_offline = os.getenv("HF_HUB_OFFLINE", "0") == "1"
            hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
            
            # Try to find cached model path for offline mode
            model_path = RERANKER_MODEL
            if is_offline:
                # Look for cached model in hub directory
                cached_model_path = os.path.join(hf_home, "hub", f"models--{RERANKER_MODEL.replace('/', '--')}")
                if os.path.exists(cached_model_path):
                    # Find the snapshot directory
                    snapshots_dir = os.path.join(cached_model_path, "snapshots")
                    if os.path.exists(snapshots_dir):
                        snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
                        if snapshots:
                            model_path = os.path.join(snapshots_dir, snapshots[0])
                            log_info(f"  Using cached reranker model path: {model_path}", context="reranker")
            
            # Try to load from local cache first
            _cross_encoder = CrossEncoder(
                model_path,
                max_length=512,
                device='cpu'
            )
            
            log_info(f"Reranker model loaded successfully: {RERANKER_MODEL}", context="reranker")
            
        except ImportError:
            log_warning(
                "sentence-transformers not installed, reranker disabled",
                context="reranker"
            )
            _model_load_failed = True
            return None
        except OSError as e:
            # This typically happens when model can't be downloaded (no internet)
            log_warning(
                f"Reranker model not available (offline or network error): {e}",
                context="reranker"
            )
            _model_load_failed = True
            return None
        except Exception as e:
            log_error(e, context="reranker", operation="model_load")
            _model_load_failed = True
            return None
    
    return _cross_encoder


class BGEReranker:
    """
    Cross-encoder based reranker for improving retrieval quality.
    
    
    Features:
    - Batch processing for efficiency
    - CPU-optimized inference
    - Lazy model loading
    """
    
    def __init__(self, batch_size: int = 8):
        """
        Initialize reranker.
        
        Args:
            batch_size: Batch size for inference (8-16 recommended for CPU)
        """
        self.batch_size = batch_size
        self._model = None
    
    @property
    def model(self):
        """Lazy-load model on first use."""
        if self._model is None:
            self._model = _get_cross_encoder()
        return self._model
    
    def rerank(
        self,
        query: str,
        chunks: List,  
        top_k: int = 20
    ) -> List:
        """
        Re-rank chunks using BGE reranker.
        
        Args:
            query: The search query
            chunks: List of RetrievedChunk objects
            top_k: Number of top results to return
            
        Returns:
            Re-ranked list of RetrievedChunks
        """
        start_time = time.time()
        
        if not chunks:
            return []
        
        # If model not available, return original order
        if self.model is None:
            log_warning(
                "Reranker model not available, returning original order",
                context="reranker"
            )
            return chunks[:top_k]
        
        try:
            log_info(
                f"Re-ranking {len(chunks)} chunks",
                context="reranker",
                query_length=len(query)
            )
            
            # Prepare query-document pairs
            pairs = [(query, chunk.text) for chunk in chunks]
            
            # Score in batches
            scores = self._batch_score(pairs)
            
            # Combine chunks with scores
            scored_chunks = list(zip(chunks, scores))
            
            # Sort by score (descending)
            scored_chunks.sort(key=lambda x: x[1], reverse=True)
            
            # Update chunk scores and extract top-k
            result = []
            for chunk, score in scored_chunks[:top_k]:
                chunk.score = float(score)
                result.append(chunk)
            
            duration = time.time() - start_time
            log_performance(
                "BGE re-ranking completed",
                duration,
                input_chunks=len(chunks),
                output_chunks=len(result),
                top_score=result[0].score if result else 0
            )
            
            return result
            
        except Exception as e:
            log_error(e, context="reranker", operation="rerank")
            # Return original order on failure
            return chunks[:top_k]
    
    def _batch_score(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """
        Score query-document pairs in batches.
        
        Args:
            pairs: List of (query, document) tuples
            
        Returns:
            List of scores
        """
        scores = []
        
        with torch.no_grad():
            for i in range(0, len(pairs), self.batch_size):
                batch = pairs[i:i + self.batch_size]
                batch_scores = self.model.predict(batch)
                
                # Handle both single score and array returns
                if hasattr(batch_scores, '__iter__'):
                    scores.extend(batch_scores.tolist() if hasattr(batch_scores, 'tolist') else list(batch_scores))
                else:
                    scores.append(float(batch_scores))
        
        return scores
    
    def is_available(self) -> bool:
        """Check if reranker model is available."""
        return self.model is not None


# Singleton instance
_reranker_instance: Optional[BGEReranker] = None


def get_reranker() -> BGEReranker:
    """Get singleton reranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = BGEReranker()
    return _reranker_instance

