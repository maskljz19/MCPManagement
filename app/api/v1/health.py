"""Health Check Endpoint"""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, Response
from typing import Dict, Any
import asyncio
from app.core.monitoring import get_metrics, get_metrics_content_type

router = APIRouter(tags=["health"])


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


async def check_qdrant() -> bool:
    """Check Qdrant connection health"""
    from app.core.database import check_qdrant_connection
    return await check_qdrant_connection()


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


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check() -> JSONResponse:
    """
    Health check endpoint that verifies all service dependencies.
    
    Returns:
        200 OK if all services are healthy
        503 Service Unavailable if any service is unhealthy
    
    **Requirements: 12.3**
    """
    # Check all services
    checks = {
        "mysql": await check_mysql(),
        "mongodb": await check_mongodb(),
        "redis": await check_redis(),
        "qdrant": await check_qdrant(),
        "rabbitmq": await check_rabbitmq()
    }
    
    # Determine overall health
    all_healthy = all(checks.values())
    
    response_data: Dict[str, Any] = {
        "status": "healthy" if all_healthy else "unhealthy",
        "services": checks
    }
    
    if all_healthy:
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data
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
