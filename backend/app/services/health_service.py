"""
Health check service for monitoring system components.
Checks connectivity to PostgreSQL, Qdrant, MinIO, and Redis.
"""
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
import time

from app.db.database import engine
from app.config import qdrant_client, MINIO_BUCKET_NAME
from app.utils.minio import initialize_minio
from app.utils.logger import log_info, log_error


async def check_database() -> Dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    try:
        start = time.time()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        duration = time.time() - start
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration * 1000, 2)
        }
    except Exception as e:
        log_error(e, context="health_check", component="database")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_qdrant() -> Dict[str, Any]:
    """Check Qdrant vector database connectivity."""
    try:
        if qdrant_client is None:
            return {
                "status": "unavailable",
                "error": "Qdrant client not configured"
            }
        
        start = time.time()
        # Try to get collections (lightweight operation)
        collections = qdrant_client.get_collections()
        duration = time.time() - start
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration * 1000, 2),
            "collections_count": len(collections.collections)
        }
    except Exception as e:
        log_error(e, context="health_check", component="qdrant")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_minio() -> Dict[str, Any]:
    """Check MinIO object storage connectivity."""
    try:
        start = time.time()
        minio_client = initialize_minio()
        
        
        bucket_exists = minio_client.bucket_exists(MINIO_BUCKET_NAME)
        duration = time.time() - start
        
        return {
            "status": "healthy" if bucket_exists else "degraded",
            "response_time_ms": round(duration * 1000, 2),
            "bucket_exists": bucket_exists,
            "bucket_name": MINIO_BUCKET_NAME
        }
    except Exception as e:
        log_error(e, context="health_check", component="minio")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity (if configured)."""
    try:
        import redis
        import os
        
        redis_url = os.getenv("REDIS_HOST")
        if not redis_url:
            return {
                "status": "not_configured",
                "message": "Redis not configured"
            }
        
        start = time.time()
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            db=int(os.getenv("REDIS_DB", 0)),
            password=os.getenv("REDIS_PASSWORD"),
            socket_connect_timeout=2
        )
        r.ping()
        duration = time.time() - start
        
        return {
            "status": "healthy",
            "response_time_ms": round(duration * 1000, 2)
        }
    except ImportError:
        return {
            "status": "not_installed",
            "message": "Redis client not installed"
        }
    except Exception as e:
        log_error(e, context="health_check", component="redis")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def check_prometheus() -> Dict[str, Any]:
    """Check Prometheus metrics endpoint availability."""
    try:
        import httpx
        import os
        
        # Check if /metrics endpoint is accessible
        start = time.time()
        async with httpx.AsyncClient(timeout=2.0) as client:
            # Try to access metrics endpoint on localhost
            response = await client.get("http://localhost:8000/metrics")
            duration = time.time() - start
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "response_time_ms": round(duration * 1000, 2)
                }
            else:
                return {
                    "status": "degraded",
                    "response_time_ms": round(duration * 1000, 2),
                    "status_code": response.status_code
                }
    except Exception as e:
        log_error(e, context="health_check", component="prometheus")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def get_health_status() -> Dict[str, Any]:
    """
    Get overall health status of all components.
    Returns liveness check (basic health).
    """
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "hcp-backend"
    }


async def get_readiness_status() -> Dict[str, Any]:
    """
    Get readiness status of all components.
    Returns detailed status of each dependency.
    """
    db_status = await check_database()
    qdrant_status = await check_qdrant()
    minio_status = await check_minio()
    redis_status = await check_redis()
    
    # Determine overall readiness
    critical_components = [db_status, qdrant_status, minio_status]
    is_ready = all(
        comp["status"] in ["healthy", "degraded"] 
        for comp in critical_components
    )
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": time.time(),
        "components": {
            "database": db_status,
            "qdrant": qdrant_status,
            "minio": minio_status,
            "redis": redis_status
        }
    }
