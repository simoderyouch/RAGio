"""
Background tasks module for Celery.
"""
from app.tasks.document_tasks import (
    process_uploaded_file_task,
    process_pdf_from_url_task
)

__all__ = [
    "process_uploaded_file_task",
    "process_pdf_from_url_task"
]
