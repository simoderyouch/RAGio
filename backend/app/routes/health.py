from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from app.db.database import get_db_stats
from app.middleware.performance import get_performance_summary, get_system_stats
from app.middleware.error_handler import get_request_id
from app.utils.logger import log_info, log_error
from app.services.health_service import (
    get_health_status,
    get_readiness_status,
    check_database,
    check_qdrant,
    check_minio,
    check_redis
)
import time
import psutil


router = APIRouter()


@router.get("/")
async def health_check(request: Request):
    """Basic liveness check endpoint"""
    request_id = get_request_id(request)
    
    try:
        health = await get_health_status()
        
        log_info(
            "Health check completed",
            context="health_check",
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=200,
            content={
                **health,
                "request_id": request_id
            }
        )
    except Exception as e:
        log_error(e, context="health_check", request_id=request_id)
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "request_id": request_id,
                "error": str(e)
            }
        )


@router.get("/ready")
async def readiness_check(request: Request):
    """Readiness check - verifies all dependencies are available"""
    request_id = get_request_id(request)
    
    try:
        readiness = await get_readiness_status()
        status_code = 200 if readiness["status"] == "ready" else 503
        
        log_info(
            f"Readiness check: {readiness['status']}",
            context="health_check",
            request_id=request_id
        )
        
        return JSONResponse(
            status_code=status_code,
            content={
                **readiness,
                "request_id": request_id
            }
        )
    except Exception as e:
        log_error(e, context="readiness_check", request_id=request_id)
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": time.time(),
                "request_id": request_id,
                "error": str(e)
            }
        )


@router.get("/detailed")
async def detailed_health_check(request: Request):
    """Detailed health check with system metrics"""
    start_time = time.time()
    request_id = get_request_id(request)
    
    try:
        # Get component health status
        from app.services.health_service import check_prometheus
        db_status = await check_database()
        qdrant_status = await check_qdrant()
        minio_status = await check_minio()
        redis_status = await check_redis()
        prometheus_status = await check_prometheus()
        
        # Determine overall health
        components = [db_status, qdrant_status, minio_status]
        is_healthy = all(c["status"] in ["healthy", "degraded"] for c in components)
        
        # Get system metrics
        system_stats = get_system_stats()
        performance_summary = get_performance_summary()
        
        duration = time.time() - start_time
        
        log_info(
            "Detailed health check completed",
            context="health_check",
            request_id=request_id,
            duration=duration
        )
        
        return JSONResponse(
            status_code=200 if is_healthy else 503,
            content={
                "status": "healthy" if is_healthy else "unhealthy",
                "timestamp": time.time(),
                "request_id": request_id,
                "response_time": f"{duration:.3f}s",
                "components": {
                    "database": db_status,
                    "qdrant": qdrant_status,
                    "minio": minio_status,
                    "redis": redis_status,
                    "prometheus": prometheus_status
                },
                "system": system_stats,
                "performance": performance_summary
            }
        )
    except Exception as e:
        duration = time.time() - start_time
        log_error(
            e,
            context="detailed_health_check",
            request_id=request_id,
            duration=duration
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "timestamp": time.time(),
                "request_id": request_id,
                "response_time": f"{duration:.3f}s",
                "error": str(e)
            }
        )

# Metrics endpoint moved to app/routes/metrics.py

