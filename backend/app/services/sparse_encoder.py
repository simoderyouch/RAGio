"""
Sparse Encoder Service for BM25-based sparse vector generation.
Uses Qdrant's built-in sparse vector support for hybrid retrieval.
"""

import re
import math
from typing import List, Dict, Tuple, Optional
from collections import Counter
from dataclasses import dataclass

from app.utils.logger import log_info, log_error


@dataclass
class SparseVector:
    """Sparse vector representation for Qdrant."""
    indices: List[int]
    values: List[float]
    
    def to_dict(self) -> Dict:
        """Convert to Qdrant sparse vector format."""
        return {
            "indices": self.indices,
            "values": self.values
        }


class BM25SparseEncoder:
    """
    BM25-based sparse encoder for generating sparse vectors.
    Compatible with Qdrant's sparse vector format.
    
    Uses a vocabulary-based approach where each unique term
    gets a consistent index based on hashing.
    """
    
    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        vocab_size: int = 30000,
        min_token_length: int = 2,
        max_token_length: int = 50
    ):
        """
        Initialize BM25 encoder.
        
        Args:
            k1: BM25 term frequency saturation parameter
            b: BM25 length normalization parameter
            vocab_size: Size of vocabulary (for hash-based indexing)
            min_token_length: Minimum token length to consider
            max_token_length: Maximum token length to consider
        """
        self.k1 = k1
        self.b = b
        self.vocab_size = vocab_size
        self.min_token_length = min_token_length
        self.max_token_length = max_token_length
        
        # Stop words to filter out
        self.stop_words = {
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for',
            'from', 'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on',
            'that', 'the', 'to', 'was', 'were', 'will', 'with',
            'le', 'la', 'les', 'de', 'du', 'des', 'un', 'une', 'et',
            'est', 'en', 'au', 'aux', 'pour', 'par', 'sur', 'dans',
            'ce', 'cette', 'ces', 'qui', 'que', 'quoi', 'dont', 'ou'
        }
        
        # Average document length (will be updated dynamically)
        self.avg_doc_length = 500.0
        
    def _tokenize(self, text: str) -> List[str]:
        """
        Tokenize text into terms.
        
        Args:
            text: Input text
            
        Returns:
            List of tokens
        """
        # Lowercase and remove special characters
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split into tokens
        tokens = text.split()
        
        # Filter tokens
        filtered = []
        for token in tokens:
            # Check length
            if len(token) < self.min_token_length:
                continue
            if len(token) > self.max_token_length:
                continue
            
            # Check stop words
            if token in self.stop_words:
                continue
            
            filtered.append(token)
        
        return filtered
    
    def _term_to_index(self, term: str) -> int:
        """
        Convert term to vocabulary index using hashing.
        
        Args:
            term: The term to convert
            
        Returns:
            Index in vocabulary
        """
        # Use simple hash-based indexing
        return hash(term) % self.vocab_size
    
    def _compute_tf(self, term: str, term_counts: Counter, doc_length: int) -> float:
        """
        Compute BM25 term frequency score.
        
        Args:
            term: The term
            term_counts: Counter of term frequencies
            doc_length: Document length in tokens
            
        Returns:
            TF score
        """
        tf = term_counts.get(term, 0)
        
        # BM25 TF formula
        numerator = tf * (self.k1 + 1)
        denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / self.avg_doc_length))
        
        return numerator / denominator if denominator > 0 else 0.0
    
    def encode_document(self, text: str) -> SparseVector:
        """
        Encode a document into a sparse vector.
        
        Args:
            text: Document text
            
        Returns:
            SparseVector for the document
        """
        if not text or not text.strip():
            return SparseVector(indices=[], values=[])
        
        try:
            tokens = self._tokenize(text)
            
            if not tokens:
                return SparseVector(indices=[], values=[])
            
            doc_length = len(tokens)
            term_counts = Counter(tokens)
            
            # Build sparse vector
            index_value_pairs: Dict[int, float] = {}
            
            for term, count in term_counts.items():
                idx = self._term_to_index(term)
                tf_score = self._compute_tf(term, term_counts, doc_length)
                
                # Aggregate if same index (hash collision)
                if idx in index_value_pairs:
                    index_value_pairs[idx] += tf_score
                else:
                    index_value_pairs[idx] = tf_score
            
            # Sort by index for consistent ordering
            sorted_pairs = sorted(index_value_pairs.items())
            
            indices = [pair[0] for pair in sorted_pairs]
            values = [pair[1] for pair in sorted_pairs]
            
            return SparseVector(indices=indices, values=values)
            
        except Exception as e:
            log_error(e, context="sparse_encoder", operation="encode_document")
            return SparseVector(indices=[], values=[])
    
    def encode_query(self, text: str) -> SparseVector:
        """
        Encode a query into a sparse vector.
        Uses simpler TF scoring for queries.
        
        Args:
            text: Query text
            
        Returns:
            SparseVector for the query
        """
        if not text or not text.strip():
            return SparseVector(indices=[], values=[])
        
        try:
            tokens = self._tokenize(text)
            
            if not tokens:
                return SparseVector(indices=[], values=[])
            
            term_counts = Counter(tokens)
            
            # Build sparse vector with simple TF for queries
            index_value_pairs: Dict[int, float] = {}
            
            for term, count in term_counts.items():
                idx = self._term_to_index(term)
                # Simple TF for queries (no length normalization)
                tf_score = 1.0 + math.log(1 + count)
                
                if idx in index_value_pairs:
                    index_value_pairs[idx] += tf_score
                else:
                    index_value_pairs[idx] = tf_score
            
            # Sort by index
            sorted_pairs = sorted(index_value_pairs.items())
            
            indices = [pair[0] for pair in sorted_pairs]
            values = [pair[1] for pair in sorted_pairs]
            
            return SparseVector(indices=indices, values=values)
            
        except Exception as e:
            log_error(e, context="sparse_encoder", operation="encode_query")
            return SparseVector(indices=[], values=[])
    
    def encode_batch(self, texts: List[str], is_query: bool = False) -> List[SparseVector]:
        """
        Encode a batch of texts.
        
        Args:
            texts: List of texts to encode
            is_query: Whether texts are queries (vs documents)
            
        Returns:
            List of SparseVectors
        """
        encoder_func = self.encode_query if is_query else self.encode_document
        return [encoder_func(text) for text in texts]


# Singleton instance
_sparse_encoder: Optional[BM25SparseEncoder] = None


def get_sparse_encoder() -> BM25SparseEncoder:
    """Get singleton sparse encoder instance."""
    global _sparse_encoder
    if _sparse_encoder is None:
        _sparse_encoder = BM25SparseEncoder()
    return _sparse_encoder

