"""
Query Expansion Service for RAG Pipeline.
Uses LLM to generate query reformulations, synonyms, and related terms.
Includes caching for performance optimization.
"""

import time
import hashlib
import json
import re
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from app.utils.prompt import expansion_prompt_template
from app.config import llm
from app.utils.logger import log_info, log_error, log_warning, log_performance


@dataclass
class CacheEntry:
    """Cache entry with TTL support."""
    value: List[str]
    expires_at: float


class QueryExpansionCache:
    """Simple in-memory cache with TTL for query expansions."""
    
    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self.cache: Dict[str, CacheEntry] = {}
        self.ttl = ttl_seconds
        self.max_size = max_size
    
    def _hash_query(self, query: str) -> str:
        """Generate cache key from query."""
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def get(self, query: str) -> Optional[List[str]]:
        """Get cached expansion if exists and not expired."""
        key = self._hash_query(query)
        entry = self.cache.get(key)
        
        if entry is None:
            return None
        
        if time.time() > entry.expires_at:
            del self.cache[key]
            return None
        
        return entry.value
    
    def set(self, query: str, expansions: List[str]) -> None:
        """Cache expansion results."""
        # Evict old entries if cache is full
        if len(self.cache) >= self.max_size:
            self._evict_expired()
            if len(self.cache) >= self.max_size:
                # Remove oldest entries
                oldest_keys = sorted(
                    self.cache.keys(),
                    key=lambda k: self.cache[k].expires_at
                )[:len(self.cache) // 4]
                for k in oldest_keys:
                    del self.cache[k]
        
        key = self._hash_query(query)
        self.cache[key] = CacheEntry(
            value=expansions,
            expires_at=time.time() + self.ttl
        )
    
    def _evict_expired(self) -> None:
        """Remove all expired entries."""
        now = time.time()
        expired_keys = [
            k for k, v in self.cache.items()
            if now > v.expires_at
        ]
        for k in expired_keys:
            del self.cache[k]


# Global cache instance
_expansion_cache = QueryExpansionCache()







class QueryExpander:
    """
    Expands user queries using LLM to improve retrieval recall.
    
    Features:
    - LLM-based query reformulation
    - Synonym and paraphrase generation
    - Domain-specific term expansion
    - Abbreviation handling
    - Result caching for performance
    """
    
    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize query expander.
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.llm = llm
        self.cache = _expansion_cache
        self.cache.ttl = cache_ttl
    
    async def expand(
        self, 
        query: str, 
        num_expansions: int = 4,
        use_cache: bool = True
    ) -> List[str]:
        """
        Expand a query into multiple reformulations.
        
        Args:
            query: The original user query
            num_expansions: Number of expansions to generate (default: 4)
            use_cache: Whether to use caching (default: True)
            
        Returns:
            List containing original query + expanded queries
        """
        start_time = time.time()
        query = query.strip()
        
        if not query:
            return [query]
        
        # Check cache first
        if use_cache:
            cached = self.cache.get(query)
            if cached:
                log_info(
                    "Query expansion cache hit",
                    context="query_expansion",
                    query_length=len(query)
                )
                return cached
        
        try:
            # Generate expansions using LLM
            expansions = await self._generate_expansions(query, num_expansions)
            
            # Always include original query first
            result = [query] + [e for e in expansions if e.lower() != query.lower()]
            
            # Cache the result
            if use_cache:
                self.cache.set(query, result)
            
            duration = time.time() - start_time
            log_performance(
                "Query expansion completed",
                duration,
                original_query=query[:100],
                num_expansions=len(result) - 1
            )
            
            return result
            
        except Exception as e:
            log_error(
                e,
                context="query_expansion",
                query=query[:100]
            )
            # Return original query on failure
            return [query]
    
    async def _generate_expansions(self, query: str, num_expansions: int) -> List[str]:
        """Generate query expansions using LLM."""
        prompt = expansion_prompt_template(query)
        
        try:
            # Use the configured LLM
            response = await self.llm.ainvoke(prompt)
            
            # Extract content from response
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Parse JSON response
            expansions = self._parse_expansions(content, num_expansions)
            
            return expansions
            
        except Exception as e:
            log_warning(
                f"LLM expansion failed: {e}",
                context="query_expansion"
            )
            # Fallback to simple expansion
            return self._fallback_expansion(query)
    
    def _parse_expansions(self, content: str, num_expansions: int) -> List[str]:
        """Parse LLM response to extract expansions."""
        # Try to extract JSON array
        try:
            # Find JSON array in response
            match = re.search(r'\[.*?\]', content, re.DOTALL)
            if match:
                expansions = json.loads(match.group())
                if isinstance(expansions, list):
                    # Filter and clean
                    result = []
                    for exp in expansions:
                        if isinstance(exp, str) and exp.strip():
                            clean = exp.strip()
                            if len(clean) > 3 and len(clean) < 500:
                                result.append(clean)
                    return result[:num_expansions]
        except json.JSONDecodeError:
            pass
        
        lines = re.split(r'[\n,]', content)
        result = []
        for line in lines:
            # Clean line
            clean = re.sub(r'^[\d\.\)\-\*]+\s*', '', line.strip())
            clean = clean.strip('"\'')
            if clean and len(clean) > 3 and len(clean) < 500:
                result.append(clean)
        
        return result[:num_expansions]
    
    def _fallback_expansion(self, query: str) -> List[str]:
        """
        Simple rule-based fallback expansion.
        Used when LLM fails.
        """
        expansions = []
        words = query.lower().split()
        
        if len(words) > 1:
            expansions.append(' '.join(reversed(words)))
        
        if len(words) <= 3:
            expansions.append(f"what is {query}")
            expansions.append(f"explain {query}")
        
        return expansions[:4]


# Singleton instance
_query_expander: Optional[QueryExpander] = None


def get_query_expander() -> QueryExpander:
    """Get singleton query expander instance."""
    global _query_expander
    if _query_expander is None:
        _query_expander = QueryExpander()
    return _query_expander

