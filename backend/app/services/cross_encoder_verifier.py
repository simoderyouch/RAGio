"""
Cross-Encoder Verification Service for final precision ranking.
Uses cross-encoder/ms-marco-MiniLM-L-6-v2 for fast, high-quality verification.

Handles offline scenarios gracefully by disabling verification when models
cannot be downloaded from HuggingFace.
"""

import os
import time
from typing import List, Optional, Tuple

import torch
from app.config import CROSS_ENCODER_MODEL
from app.utils.logger import log_info, log_error, log_warning, log_performance


# Lazy import to avoid loading model at startup
_verifier_model = None
_model_load_attempted = False
_model_load_failed = False


def preload_model():
    """Preload the cross-encoder model at startup."""
    _get_verifier_model()


def _get_verifier_model():
    """Lazy load the cross-encoder verification model with offline fallback."""
    global _verifier_model, _model_load_attempted, _model_load_failed
    
    # Don't retry if we already failed
    if _model_load_failed:
        return None
    
    if _verifier_model is None and not _model_load_attempted:
        _model_load_attempted = True
        
        try:
            import torch
            from sentence_transformers import CrossEncoder
            import os
            
            log_info("Loading cross-encoder verification model...", context="cross_encoder")
            
            # Set torch to use optimal number of threads for CPU
            torch.set_num_threads(4)
            
            # In offline mode, try to use cached model path if available
            is_offline = os.getenv("HF_HUB_OFFLINE", "0") == "1"
            hf_home = os.getenv("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
            
            # Try to find cached model path for offline mode
            model_path = CROSS_ENCODER_MODEL
            if is_offline:
                # Look for cached model in hub directory
                cached_model_path = os.path.join(hf_home, "hub", f"models--{CROSS_ENCODER_MODEL.replace('/', '--')}")
                if os.path.exists(cached_model_path):
                    # Find the snapshot directory
                    snapshots_dir = os.path.join(cached_model_path, "snapshots")
                    if os.path.exists(snapshots_dir):
                        snapshots = [d for d in os.listdir(snapshots_dir) if os.path.isdir(os.path.join(snapshots_dir, d))]
                        if snapshots:
                            model_path = os.path.join(snapshots_dir, snapshots[0])
                            log_info(f"  Using cached cross-encoder model path: {model_path}", context="cross_encoder")
            
            _verifier_model = CrossEncoder(
                model_path,
                max_length=512,
                device='cpu'
            )
            
            log_info("Cross-encoder verification model loaded successfully", context="cross_encoder")
            
        except ImportError:
            log_warning(
                "sentence-transformers not installed, cross-encoder disabled",
                context="cross_encoder"
            )
            _model_load_failed = True
            return None
        except OSError as e:
            # This typically happens when model can't be downloaded (no internet)
            log_warning(
                f"Cross-encoder model not available (offline or network error): {e}",
                context="cross_encoder"
            )
            _model_load_failed = True
            return None
        except Exception as e:
            log_error(e, context="cross_encoder", operation="model_load")
            _model_load_failed = True
            return None
    
    return _verifier_model


class CrossEncoderVerifier:
    """
    Cross-encoder verification for final high-precision ranking.
    
    Uses ms-marco-MiniLM-L-6-v2 which is:
    - Very fast on CPU (~80MB model)
    - High quality for relevance scoring
    - Trained on MS MARCO passage ranking
    
    Features:
    - Score thresholding to filter irrelevant results
    - Batch processing for efficiency
    - CPU-optimized inference
    """
    
    def __init__(
        self, 
        batch_size: int = 16,
        default_threshold: float = 0.0
    ):
        """
        Initialize cross-encoder verifier.
        
        Args:
            batch_size: Batch size for inference (16 recommended for this model on CPU)
            default_threshold: Default score threshold for filtering
        """
        self.batch_size = batch_size
        self.default_threshold = default_threshold
        self._model = None
    
    @property
    def model(self):
        """Lazy-load model on first use."""
        if self._model is None:
            self._model = _get_verifier_model()
        return self._model
    
    def verify(
        self,
        query: str,
        chunks: List,  # List[RetrievedChunk]
        threshold: Optional[float] = None,
        top_k: int = 10
    ) -> List:
        """
        Verify and rank chunks using cross-encoder.
        
        Args:
            query: The search query
            chunks: List of RetrievedChunk objects
            threshold: Minimum score threshold (None uses default)
            top_k: Maximum number of results to return
            
        Returns:
            Verified and ranked list of RetrievedChunks
        """
        start_time = time.time()
        
        if not chunks:
            return []
        
        threshold = threshold if threshold is not None else self.default_threshold
        
        # If model not available, return original order
        if self.model is None:
            log_warning(
                "Cross-encoder model not available, returning original order",
                context="cross_encoder"
            )
            return chunks[:top_k]
        
        try:
            log_info(
                f"Verifying {len(chunks)} chunks with cross-encoder",
                context="cross_encoder",
                query_length=len(query),
                threshold=threshold
            )
            
            # Prepare query-document pairs
            pairs = [(query, chunk.text) for chunk in chunks]
            
            # Score in batches
            scores = self._batch_score(pairs)
            
            # Combine chunks with scores
            scored_chunks = list(zip(chunks, scores))
            
            # Filter by threshold
            filtered = [(chunk, score) for chunk, score in scored_chunks if score >= threshold]
            
            # Sort by score (descending)
            filtered.sort(key=lambda x: x[1], reverse=True)
            
            # Update chunk scores and extract top-k
            result = []
            for chunk, score in filtered[:top_k]:
                chunk.score = float(score)
                result.append(chunk)
            
            duration = time.time() - start_time
            log_performance(
                "Cross-encoder verification completed",
                duration,
                input_chunks=len(chunks),
                filtered_chunks=len(filtered),
                output_chunks=len(result),
                threshold=threshold,
                top_score=result[0].score if result else 0
            )
            
            return result
            
        except Exception as e:
            log_error(e, context="cross_encoder", operation="verify")
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
    
    def score_pair(self, query: str, text: str) -> float:
        """
        Score a single query-document pair.
        
        Args:
            query: The query
            text: The document text
            
        Returns:
            Relevance score
        """
        if self.model is None:
            return 0.0
        
        try:
            with torch.no_grad():
                score = self.model.predict([(query, text)])
                return float(score[0]) if hasattr(score, '__iter__') else float(score)
        except Exception as e:
            log_error(e, context="cross_encoder", operation="score_pair")
            return 0.0
    
    def is_available(self) -> bool:
        """Check if cross-encoder model is available."""
        return self.model is not None


# Singleton instance
_verifier_instance: Optional[CrossEncoderVerifier] = None


def get_cross_encoder_verifier() -> CrossEncoderVerifier:
    """Get singleton cross-encoder verifier instance."""
    global _verifier_instance
    if _verifier_instance is None:
        _verifier_instance = CrossEncoderVerifier()
    return _verifier_instance

