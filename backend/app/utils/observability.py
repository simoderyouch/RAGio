"""
Observability utilities for standardized event tracking.
Uses Prometheus for metrics and file-based logging (collected by Promtail).
"""

import uuid
import os
import socket
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

# Observability configuration
OBSERVABILITY_ENABLED = os.getenv("OBSERVABILITY_ENABLED", "true").lower() == "true"
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
HOSTNAME = socket.gethostname()


def generate_trace_id() -> str:
    """Generate a new trace ID (UUID)."""
    return str(uuid.uuid4())


def generate_span_id() -> str:
    """Generate a new span ID (UUID)."""
    return str(uuid.uuid4())


def get_service_name() -> str:
    """Get current service name."""
    # Detect if running in Celery worker
    if "celery" in os.getenv("_", "").lower() or "CELERY" in os.environ:
        return "celery_worker"
    return "backend"


def format_timestamp() -> str:
    """Get current timestamp in ISO 8601 UTC format."""
    return datetime.now(timezone.utc).isoformat()


class ObservabilityClient:
    """Client for recording Prometheus metrics."""
    
    def __init__(self):
        self.service_name = get_service_name()
    
    def push_llm_usage(self, user_id: int, request_id: str,
                      provider: str, model: str, operation: str,
                      latency_ms: float, success: bool,
                      error_code: Optional[str] = None,
                      error_message: Optional[str] = None,
                      input_tokens: int = 0,
                      output_tokens: int = 0,
                      total_tokens: int = 0,
                      cost_usd: float = 0.0,
                      fallback_used: bool = False,
                      fallback_model: Optional[str] = None,
                      trace_id: Optional[str] = None) -> bool:
        """Record LLM token usage metrics in Prometheus (for RAG token tracking)."""
        if not OBSERVABILITY_ENABLED:
            return False
        
        try:
            from app.utils.prometheus_metrics import llm_tokens_total
            
            # Record tokens only (needed for RAG token usage tracking)
            if input_tokens > 0:
                llm_tokens_total.labels(type="input").inc(input_tokens)
            if output_tokens > 0:
                llm_tokens_total.labels(type="output").inc(output_tokens)
            
            return True
        except Exception:
            # Never block on observability
            return False
    
    def push_system_metric(self, metric_type: str, metric_value: float,
                          tags: Optional[Dict[str, Any]] = None) -> bool:
        """System metrics are no longer collected. This is a no-op for backward compatibility."""
        return True
    
    # Keep these methods for backward compatibility but they're no-ops
    # Logs go to files and are collected by Promtail
    def push_log(self, *args, **kwargs) -> bool:
        """Logs are handled by file handlers and collected by Promtail."""
        return True
    
    def push_api_usage(self, *args, **kwargs) -> bool:
        """API usage is handled by performance middleware directly."""
        return True
    
    def push_rag_analytics(self, user_id: int, request_id: str,
                          operation: str, stage_order: int,
                          duration_ms: float, success: bool,
                          candidates_count: int = 0,
                          chunks_retrieved: int = 0,
                          tokens_used: int = 0,
                          file_ids: Optional[List[int]] = None,
                          collection_name: str = "",
                          error_code: Optional[str] = None,
                          error_message: Optional[str] = None,
                          trace_id: Optional[str] = None) -> bool:
        """Record RAG operations metrics in Prometheus."""
        if not OBSERVABILITY_ENABLED:
            return False
        
        try:
            from app.utils.prometheus_metrics import (
                rag_operations_total,
                rag_stage_duration_seconds,
                rag_candidates_count,
                rag_tokens_per_request
            )
            
            # Record RAG operation success/failure
            success_label = "true" if success else "false"
            rag_operations_total.labels(
                operation=operation,
                success=success_label
            ).inc()
            
            # Record stage duration
            if duration_ms > 0:
                rag_stage_duration_seconds.labels(stage=operation).observe(duration_ms / 1000.0)
            
            # Record candidates count for retrieval stages
            if candidates_count > 0 and operation in ['hybrid_retrieval', 'reranking', 'cross_encoder']:
                rag_candidates_count.labels(stage=operation).observe(candidates_count)
            
            # Record token usage per request (only for context_assembly stage to avoid double counting)
            if tokens_used > 0 and operation == 'context_assembly':
                rag_tokens_per_request.observe(tokens_used)
            
            return True
        except Exception:
            # Never block on observability
            return False
    
    def push_qdrant_stats(self, *args, **kwargs) -> bool:
        """Qdrant stats can be added later if needed."""
        return True
    
    def push_system_event(self, *args, **kwargs) -> bool:
        """System events can be added later if needed."""
        return True


# Singleton instance
_observability_client: Optional[ObservabilityClient] = None


def get_observability_client() -> ObservabilityClient:
    """Get singleton observability client."""
    global _observability_client
    if _observability_client is None:
        _observability_client = ObservabilityClient()
    return _observability_client

