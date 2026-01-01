"""Health Check Endpoint"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, Response
from typing import Dict, Any
import asyncio
import time
from app.core.monitoring import get_metrics, get_metrics_content_type
from app.core.config import settings

router = APIRouter(tags=["health"])

# Cache health check results to reduce database load
_health_cache = {
    "last_check": 0,
    "cache_duration": 30,  # Cache for 30 seconds
    "cached_result": None
}


async def check_mysql() -> bool:
    """Check MySQL connection health"""
    from app.core.database import check_mysql_connection
    return await check_mysql_connection()


async def check_mongodb() -> bool:
    """Check MongoDB connection health"""
    from app.core.database import check_mongodb_connection
    return await check_mongodb_connection()


async def check_redis() -> bool:
    """Check Redis connection health"""
    from app.core.database import check_redis_connection
    return await check_redis_connection()


async def check_rabbitmq() -> bool:
    """Check RabbitMQ connection health"""
    try:
        from app.core.celery_app import celery_app
        # Try to inspect the broker connection
        inspect = celery_app.control.inspect()
        # Get active queues - this will fail if RabbitMQ is down
        stats = inspect.stats()
        return stats is not None and len(stats) > 0
    except Exception:
        # If we can't connect to any workers, RabbitMQ might be down
        # or no workers are running. For health check purposes,
        # we'll consider this as RabbitMQ being unavailable
        return False


async def _perform_health_checks() -> Dict[str, Any]:
    """Perform actual health checks"""
    # Check all services
    checks = {
        "mysql": await check_mysql(),
        "mongodb": await check_mongodb(),
        "redis": await check_redis(),
        "rabbitmq": await check_rabbitmq()
    }
    
    # Determine overall health
    all_healthy = all(checks.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": checks,
        "timestamp": int(time.time())
    }


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Health check endpoint that verifies all service dependencies.
    
    Uses caching to reduce database load from frequent health checks.
    
    Returns:
        200 OK if all services are healthy
        503 Service Unavailable if any service is unhealthy
    
    **Requirements: 12.3**
    """
    current_time = time.time()
    
    # Check if we have a cached result that's still valid
    if (_health_cache["cached_result"] is not None and 
        current_time - _health_cache["last_check"] < _health_cache["cache_duration"]):
        response_data = _health_cache["cached_result"]
    else:
        # Perform health checks and cache the result
        response_data = await _perform_health_checks()
        _health_cache["cached_result"] = response_data
        _health_cache["last_check"] = current_time
    
    # Return appropriate status code
    if response_data["status"] == "healthy":
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data
        )


@router.get("/health/simple", status_code=status.HTTP_200_OK)
async def simple_health_check() -> JSONResponse:
    """
    Simple health check endpoint that just returns OK.
    
    Use this for basic liveness checks that don't need dependency validation.
    This endpoint generates minimal logs and has no database dependencies.
    
    Returns:
        200 OK always
    """
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "ok",
            "timestamp": int(time.time())
        }
    )


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format for scraping by Prometheus server.
    
    **Requirements: 12.1**
    """
    metrics_data = get_metrics()
    return Response(
        content=metrics_data,
        media_type=get_metrics_content_type()
    )
