"""
Prometheus metrics definitions for observability.
All metrics are defined here and can be imported throughout the application.
"""

from prometheus_client import Counter, Histogram, Gauge

# HTTP Request Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_request_size_bytes = Histogram(
    'http_request_size_bytes',
    'HTTP request/response size in bytes',
    ['type'],  # 'request' or 'response'
    buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000, 1000000)
)

# LLM Token Metrics (for RAG token usage tracking)
llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total number of LLM tokens',
    ['type']  # 'input' or 'output'
)

# RAG Pipeline Metrics
rag_operations_total = Counter(
    'rag_operations_total',
    'Total number of RAG operations by stage',
    ['operation', 'success']  # operation: query_expansion, hybrid_retrieval, reranking, cross_encoder, context_assembly
)

rag_stage_duration_seconds = Histogram(
    'rag_stage_duration_seconds',
    'RAG pipeline stage duration in seconds',
    ['stage'],  # stage: query_expansion, hybrid_retrieval, reranking, cross_encoder, context_assembly
    buckets=(0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

rag_candidates_count = Histogram(
    'rag_candidates_count',
    'Number of candidates retrieved in RAG pipeline',
    ['stage'],  # stage: hybrid_retrieval, reranking, cross_encoder
    buckets=(1, 5, 10, 20, 50, 100, 200, 500)
)

rag_tokens_per_request = Histogram(
    'rag_tokens_per_request',
    'Number of tokens used per RAG request',
    buckets=(100, 500, 1000, 2000, 5000, 10000, 20000, 50000)
)

# Celery Task Metrics
celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total number of Celery tasks executed',
    ['task_name', 'queue', 'status']  # status: 'success', 'failure', 'retry'
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name', 'queue'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

celery_queue_length = Gauge(
    'celery_queue_length',
    'Current number of tasks in Celery queue',
    ['queue']  # queue name
)

celery_active_workers = Gauge(
    'celery_active_workers',
    'Current number of active Celery workers',
    ['queue']  # queue name
)

