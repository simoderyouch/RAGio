"""
Prometheus metrics endpoint for observability.
Exposes metrics in Prometheus format for scraping.
"""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.utils.prometheus_metrics import (
    http_requests_total,
    http_request_duration_seconds,
    http_request_size_bytes,
    llm_tokens_total,
    rag_operations_total,
    rag_stage_duration_seconds,
    rag_candidates_count,
    rag_tokens_per_request,
    celery_tasks_total,
    celery_task_duration_seconds,
    celery_queue_length,
    celery_active_workers
)

router = APIRouter()


@router.get("/metrics")
async def metrics():
    """
    Prometheus metrics endpoint.
    Returns metrics in Prometheus text format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

