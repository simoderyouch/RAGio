"""
Celery application configuration for background task processing.
"""
from celery import Celery
from celery.signals import (
    worker_process_init, worker_ready, worker_shutdown,
    task_prerun, task_postrun, task_failure, task_retry
)
import os
import time
import threading
import socket
from dotenv import load_dotenv

load_dotenv()

# Celery task instrumentation for Prometheus metrics
from app.config import OBSERVABILITY_ENABLED

# Initialize Celery app
celery_app = Celery(
    "hcp_backend",
    broker=os.getenv("CELERY_BROKER_URL"),
    backend=os.getenv("CELERY_RESULT_BACKEND"),
    include=["app.tasks.document_tasks"]
)

# Setup Celery logging to use structured JSON logger
def setup_celery_logging():
    """Configure Celery to use structured JSON logging"""
    try:
        from app.utils.logger import setup_logger
        
        # Setup logger for Celery worker
        celery_logger = setup_logger(name="celery_worker", log_level=os.getenv("LOG_LEVEL", "INFO"))
        
        # Configure Celery's logging
        import logging
        celery_logging = logging.getLogger('celery')
        celery_logging.handlers = celery_logger.handlers
        celery_logging.setLevel(celery_logger.level)
        celery_logging.propagate = False
        
        # Configure Celery task logging
        celery_task_logging = logging.getLogger('celery.task')
        celery_task_logging.handlers = celery_logger.handlers
        celery_task_logging.setLevel(celery_logger.level)
        celery_task_logging.propagate = False
        
        return celery_logger
    except Exception as e:
        # Fallback to default logging if setup fails
        import logging
        return logging.getLogger('celery')


# Initialize Celery logger
celery_logger = None

@worker_process_init.connect
def setup_worker_logging(**kwargs):
    """Setup structured logging when worker process initializes"""
    global celery_logger
    try:
        celery_logger = setup_celery_logging()
        if celery_logger:
            celery_logger.info(
                "Celery worker process initialized",
                extra={
                    'worker_hostname': socket.gethostname(),
                    'worker_pid': os.getpid(),
                    'event': 'worker_init'
                }
            )
    except Exception as e:
        # Don't fail worker startup if logging setup fails
        import logging
        logging.warning(f"Failed to setup Celery logging: {e}")


@worker_process_init.connect
def start_metrics_server_on_worker_init(**kwargs):
    """Start Prometheus metrics HTTP server when Celery worker process initializes."""
    try:
        from app.utils.celery_metrics_server import start_metrics_server
        port = int(os.getenv("CELERY_METRICS_PORT", "8081"))
        start_metrics_server(port)
        
        # Start background thread to collect queue and worker metrics
        if OBSERVABILITY_ENABLED:
            _start_queue_metrics_collector()
    except Exception as e:
        # Don't fail worker startup if metrics server fails
        if celery_logger:
            celery_logger.warning(f"Failed to start metrics server: {e}", extra={'event': 'metrics_server_failed'})
        else:
            print(f"Warning: Failed to start metrics server: {e}")


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Log when worker is ready to accept tasks"""
    if celery_logger:
        celery_logger.info(
            "Celery worker ready",
            extra={
                'worker_hostname': socket.gethostname(),
                'worker_pid': os.getpid(),
                'event': 'worker_ready'
            }
        )


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Log when worker is shutting down"""
    if celery_logger:
        celery_logger.info(
            "Celery worker shutting down",
            extra={
                'worker_hostname': socket.gethostname(),
                'worker_pid': os.getpid(),
                'event': 'worker_shutdown'
            }
        )


def _collect_celery_queue_metrics():
    """Collect Celery queue length and active worker count using inspect API."""
    if not OBSERVABILITY_ENABLED:
        return
    
    try:
        from app.utils.prometheus_metrics import celery_queue_length, celery_active_workers
        
        # Use inspect API to get queue and worker info
        inspect = celery_app.control.inspect()
        
        # Get active queues and their lengths
        active_queues = inspect.active_queues()
        if active_queues:
            # Count workers per queue
            queue_workers = {}
            for worker_name, queues in active_queues.items():
                for queue_info in queues:
                    queue_name = queue_info.get('name', 'default')
                    if queue_name not in queue_workers:
                        queue_workers[queue_name] = 0
                    queue_workers[queue_name] += 1
            
            # Update active worker count per queue
            for queue_name, worker_count in queue_workers.items():
                celery_active_workers.labels(queue=queue_name).set(worker_count)
        
        # Get reserved tasks (tasks in queue waiting to be processed)
        reserved = inspect.reserved()
        if reserved:
            queue_lengths = {}
            for worker_name, tasks in reserved.items():
                # Get queue name from worker's active queues
                worker_queues = active_queues.get(worker_name, []) if active_queues else []
                for queue_info in worker_queues:
                    queue_name = queue_info.get('name', 'default')
                    if queue_name not in queue_lengths:
                        queue_lengths[queue_name] = 0
                    queue_lengths[queue_name] += len(tasks)
            
            # Update queue length metrics
            for queue_name, length in queue_lengths.items():
                celery_queue_length.labels(queue=queue_name).set(length)
            # Set to 0 for queues with no reserved tasks
            if active_queues:
                for worker_name, queues in active_queues.items():
                    for queue_info in queues:
                        queue_name = queue_info.get('name', 'default')
                        if queue_name not in queue_lengths:
                            celery_queue_length.labels(queue=queue_name).set(0)
    except Exception as e:
        # Never block on observability - fail silently
        pass


def _start_queue_metrics_collector():
    """Start background thread to periodically collect queue and worker metrics."""
    def collect_metrics_loop():
        while True:
            try:
                _collect_celery_queue_metrics()
                time.sleep(30)  # Collect every 30 seconds
            except Exception:
                # Continue even if collection fails
                time.sleep(30)
    
    thread = threading.Thread(target=collect_metrics_loop, daemon=True)
    thread.start()

# Store task start times for duration calculation
_task_start_times = {}

@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **signal_kwargs):
    """Log task start and record start time before execution."""
    if not task:
        return
    
    start_time = time.time()
    _task_start_times[task_id] = start_time
    
    # Extract task context
    task_name = task.name
    queue = task.request.delivery_info.get('routing_key', 'unknown') if hasattr(task, 'request') else 'unknown'
    retries = task.request.retries if hasattr(task, 'request') else 0
    
    # Log task start
    if celery_logger:
        celery_logger.info(
            f"Task {task_name} started",
            extra={
                'task_id': task_id,
                'task_name': task_name,
                'queue': queue,
                'retries': retries,
                'event': 'task_start',
                'args_count': len(args) if args else 0,
                'kwargs_keys': list(kwargs.keys()) if kwargs else []
            }
        )
    
    # Record metrics
    if OBSERVABILITY_ENABLED:
        pass  # Metrics are handled in task_postrun

@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, state=None, retval=None, **kwargs):
    """Log task completion and record metrics."""
    if not task:
        return
    
    try:
        task_name = task.name
        queue = task.request.delivery_info.get('routing_key', 'unknown') if hasattr(task, 'request') else 'unknown'
        
        # Calculate duration
        duration = None
        if task_id in _task_start_times:
            duration = time.time() - _task_start_times[task_id]
            del _task_start_times[task_id]
        
        # Determine status
        if state == 'SUCCESS':
            status = 'success'
            log_level = 'info'
        elif state == 'FAILURE':
            status = 'failure'
            log_level = 'error'
        elif state == 'RETRY':
            status = 'retry'
            log_level = 'warning'
        else:
            status = 'unknown'
            log_level = 'info'
        
        # Log task completion
        if celery_logger:
            log_data = {
                'task_id': task_id,
                'task_name': task_name,
                'queue': queue,
                'status': status,
                'state': state,
                'event': 'task_complete',
            }
            if duration is not None:
                log_data['duration_seconds'] = duration
            
            if log_level == 'error':
                celery_logger.error(f"Task {task_name} completed with status {status}", extra=log_data)
            elif log_level == 'warning':
                celery_logger.warning(f"Task {task_name} completed with status {status}", extra=log_data)
            else:
                celery_logger.info(f"Task {task_name} completed with status {status}", extra=log_data)
        
        # Record Prometheus metrics
        if OBSERVABILITY_ENABLED:
            try:
                from app.utils.prometheus_metrics import celery_tasks_total, celery_task_duration_seconds
                
                # Record task count
                celery_tasks_total.labels(
                    task_name=task_name,
                    queue=queue,
                    status=status
                ).inc()
                
                # Record task duration
                if duration is not None:
                    celery_task_duration_seconds.labels(
                        task_name=task_name,
                        queue=queue
                    ).observe(duration)
            except Exception:
                # Never block on observability
                pass
    except Exception as e:
        # Never block on logging
        if celery_logger:
            celery_logger.error(f"Error in task_postrun_handler: {e}", exc_info=True)

@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwargs):
    """Log task failures with full exception details."""
    if not sender:
        return
    
    try:
        task = sender
        task_name = task.name
        queue = task.request.delivery_info.get('routing_key', 'unknown') if hasattr(task, 'request') else 'unknown'
        retries = task.request.retries if hasattr(task, 'request') else 0
        
        # Calculate duration if available
        duration = None
        if task_id in _task_start_times:
            duration = time.time() - _task_start_times[task_id]
            del _task_start_times[task_id]
        
        # Log task failure with exception details
        if celery_logger:
            log_data = {
                'task_id': task_id,
                'task_name': task_name,
                'queue': queue,
                'retries': retries,
                'status': 'failure',
                'event': 'task_failure',
                'exception_type': type(exception).__name__ if exception else 'Unknown',
                'exception_message': str(exception) if exception else 'Unknown error',
            }
            if duration is not None:
                log_data['duration_seconds'] = duration
            
            celery_logger.error(
                f"Task {task_name} failed: {str(exception) if exception else 'Unknown error'}",
                extra=log_data,
                exc_info=einfo or exception
            )
        
        # Record Prometheus metrics
        if OBSERVABILITY_ENABLED:
            try:
                from app.utils.prometheus_metrics import celery_tasks_total
                
                celery_tasks_total.labels(
                    task_name=task_name,
                    queue=queue,
                    status='failure'
                ).inc()
            except Exception:
                # Never block on observability
                pass
    except Exception as e:
        # Never block on logging
        if celery_logger:
            celery_logger.error(f"Error in task_failure_handler: {e}", exc_info=True)


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    """Log task retry attempts."""
    if not sender:
        return
    
    try:
        task = sender
        task_name = task.name
        queue = task.request.delivery_info.get('routing_key', 'unknown') if hasattr(task, 'request') else 'unknown'
        retries = task.request.retries if hasattr(task, 'request') else 0
        
        if celery_logger:
            celery_logger.warning(
                f"Task {task_name} retry attempt {retries}",
                extra={
                    'task_id': task_id,
                    'task_name': task_name,
                    'queue': queue,
                    'retries': retries,
                    'reason': str(reason) if reason else 'Unknown',
                    'event': 'task_retry'
                },
                exc_info=einfo
            )
    except Exception as e:
        if celery_logger:
            celery_logger.error(f"Error in task_retry_handler: {e}", exc_info=True)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution
    task_acks_late=True, 
    task_reject_on_worker_lost=True, 
    task_time_limit=300,  
    task_soft_time_limit=240, 
    
    # Result backend
    result_expires=3600, 
    result_backend_transport_options={"master_name": "mymaster"},
    
    # Worker configuration
    worker_prefetch_multiplier=1,  
    worker_max_tasks_per_child=100, 
    
    # Retry configuration
    task_default_retry_delay=60,  
    task_max_retries=3,  
)

# Task routing: separate queues for document processing
celery_app.conf.task_routes = {
    # Document processing tasks -> documents queue
    "app.tasks.document_tasks.*": {"queue": "documents"},
}

if __name__ == "__main__":
    celery_app.start()
