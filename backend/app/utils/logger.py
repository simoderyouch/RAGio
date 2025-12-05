import logging
import logging.handlers
import sys
from pathlib import Path
from datetime import datetime, timezone
import json
import traceback
from typing import Any, Dict, Optional, Union
import os
import re
from app.config import OBSERVABILITY_ENABLED

# Create logs directory if it doesn't exist
# Use LOG_DIR env var if set (for Docker), otherwise use relative path
log_dir_env = os.getenv("LOG_DIR")
if log_dir_env:
    logs_dir = Path(log_dir_env)
else:
    # Use absolute path relative to project root (backend/logs)
    logs_dir = Path(__file__).parent.parent.parent / "logs"
logs_dir.mkdir(exist_ok=True, parents=True)

# Sensitive field patterns to filter from logs
SENSITIVE_FIELDS = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'access_token', 'refresh_token', 'auth_token', 'bearer_token',
    'private_key', 'secret_key', 'api_secret', 'credential', 'credentials',
    'authorization', 'auth_header', 'jwt', 'session_id', 'cookie'
}

# Patterns to detect sensitive data in strings
SENSITIVE_PATTERNS = [
    re.compile(r'password["\']?\s*[:=]\s*["\']?([^"\',\s]+)', re.IGNORECASE),
    re.compile(r'token["\']?\s*[:=]\s*["\']?([^"\',\s]+)', re.IGNORECASE),
    re.compile(r'secret["\']?\s*[:=]\s*["\']?([^"\',\s]+)', re.IGNORECASE),
    re.compile(r'api[_-]?key["\']?\s*[:=]\s*["\']?([^"\',\s]+)', re.IGNORECASE),
]


def sanitize_value(value: Any) -> Any:
    """Recursively sanitize sensitive data from log values"""
    if value is None:
        return value
    
    if isinstance(value, str):
        # Check if string contains sensitive patterns
        sanitized = value
        for pattern in SENSITIVE_PATTERNS:
            sanitized = pattern.sub(r'\1=***REDACTED***', sanitized)
        return sanitized
    
    if isinstance(value, dict):
        return {k: sanitize_value(v) for k, v in value.items()}
    
    if isinstance(value, (list, tuple)):
        return [sanitize_value(item) for item in value]
    
    return value


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize sensitive fields from a dictionary"""
    sanitized = {}
    for key, value in data.items():
        key_lower = key.lower()
        # Check if key matches sensitive field patterns
        if any(sensitive in key_lower for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = sanitize_value(value)
    return sanitized


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging with sensitive data filtering"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add all extra fields dynamically (from record.__dict__)
        # Skip internal logging fields and already added fields
        skip_fields = {
            'name', 'msg', 'args', 'created', 'filename', 'funcName',
            'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message',
            'pathname', 'process', 'processName', 'relativeCreated', 'thread',
            'threadName', 'exc_info', 'exc_text', 'stack_info', 'taskName'
        }
        
        for key, value in record.__dict__.items():
            if key not in skip_fields and not key.startswith('_'):
                # Sanitize sensitive data
                if isinstance(value, dict):
                    log_entry[key] = sanitize_dict(value)
                elif isinstance(value, str):
                    log_entry[key] = sanitize_value(value)
                else:
                    # For other types, check if key is sensitive
                    if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                        log_entry[key] = "***REDACTED***"
                    else:
                        log_entry[key] = value
        
        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_traceback = record.exc_info
            log_entry['exception'] = {
                'type': exc_type.__name__ if exc_type else 'Unknown',
                'message': str(exc_value) if exc_value else 'Unknown error',
                'traceback': traceback.format_exception(exc_type, exc_value, exc_traceback)
            }
        
        # Sanitize the entire log entry before returning
        log_entry = sanitize_dict(log_entry)
        
        return json.dumps(log_entry, default=str)


# RedisQueueHandler removed - logs are collected by Promtail from files

def setup_logger(name: str = "hcp_backend", log_level: str = "INFO") -> logging.Logger:
    """Setup logger with file rotation and console output"""
    logger = logging.getLogger(name)
    
    # Get log level from environment or use default
    env_log_level = os.getenv("LOG_LEVEL", log_level).upper()
    logger.setLevel(getattr(logging, env_log_level))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Prevent propagation to root logger to avoid duplicate logs
    logger.propagate = False
    
    # Console handler with colored output
    console_handler = logging.StreamHandler(sys.stdout)
    # Console shows INFO and above in production, DEBUG in development
    console_level = logging.DEBUG if os.getenv("ENVIRONMENT", "prod").lower() == "dev" else logging.INFO
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_format)
    
    # File handler with JSON formatting and rotation
    file_handler = logging.handlers.RotatingFileHandler(
        logs_dir / f"{name}.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    # File logs capture all levels (DEBUG and above)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONFormatter())
    
    # Error file handler for errors only
    error_handler = logging.handlers.RotatingFileHandler(
        logs_dir / f"{name}_errors.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(JSONFormatter())
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    # Logs are collected by Promtail from files - no need for Redis handler
    
    return logger

# Create main logger instance
logger = setup_logger()

def log_with_context(level: str, message: str, **kwargs) -> None:
    """Log with additional context"""
    extra = {}
    for key, value in kwargs.items():
        if value is not None:
            extra[key] = value
    
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra)

def log_error(error: Exception, context: str = "", message: Optional[str] = None, **kwargs) -> None:
    """Centralized error logging with context"""
    if message is None and "message" in kwargs:
        message = kwargs.pop("message")
    
    if message:
        error_msg = message
    else:
        error_msg = f"Error in {context}: {str(error)}"
    log_with_context("ERROR", error_msg, **kwargs)

def log_info(message: str, context: str = "", **kwargs) -> None:
    """Centralized info logging with context"""
    info_msg = f"Info in {context}: {message}"
    log_with_context("INFO", info_msg, **kwargs)

def log_warning(message: str, context: str = "", **kwargs) -> None:
    """Centralized warning logging with context"""
    warning_msg = f"Warning in {context}: {message}"
    log_with_context("WARNING", warning_msg, **kwargs)

def log_debug(message: str, context: str = "", **kwargs) -> None:
    """Centralized debug logging with context"""
    debug_msg = f"Debug in {context}: {message}"
    log_with_context("DEBUG", debug_msg, **kwargs)

def log_performance(operation: str, duration: float, **kwargs) -> None:
    """Log performance metrics"""
    perf_msg = f"Performance: {operation} took {duration:.3f}s"
    log_with_context("INFO", perf_msg, operation=operation, duration=duration, **kwargs)
