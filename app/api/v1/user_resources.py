"""User Resource API Endpoints - Quota, Rate Limit, and Cost Information"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from datetime import datetime, timedelta
from typing import Dict, Any
from uuid import UUID

from app.core.database import get_db, get_redis
from app.api.v1.auth import get_current_user
from app.models.user import UserModel
from app.services.rate_limiter import RateLimiter
from app.services.resource_quota_manager import ResourceQuotaManager
from app.services.cost_tracker import CostTracker, DateRange
from app.core.logging_config import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/users/me", tags=["User Resources"])


# ============================================================================
# Dependencies
# ============================================================================


async def get_rate_limiter(redis: Redis = Depends(get_redis)) -> RateLimiter:
    """Dependency to get RateLimiter instance"""
    return RateLimiter(redis=redis)


async def get_quota_manager(
    redis: Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> ResourceQuotaManager:
    """Dependency to get ResourceQuotaManager instance"""
    return ResourceQuotaManager(redis=redis, db_session=db)


async def get_cost_tracker(db: AsyncSession = Depends(get_db)) -> CostTracker:
    """Dependency to get CostTracker instance"""
    return CostTracker(db_session=db)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/quota", response_model=Dict[str, Any])
async def get_user_quota(
    current_user: UserModel = Depends(get_current_user),
    quota_manager: ResourceQuotaManager = Depends(get_quota_manager)
):
    """
    Get current resource quota usage for the authenticated user.
    
    Returns detailed information about:
    - CPU cores (used, available, limit)
    - Memory (used, available, limit)
    - Concurrent executions (used, available, limit)
    - Daily executions (used, available, limit)
    
    **Requirements: 13.5**
    **Validates: Property 50 - Quota Usage Accuracy**
    
    Args:
        current_user: Currently authenticated user
        quota_manager: Resource quota manager instance
        
    Returns:
        Dictionary with quota usage information
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 500: If quota query fails
    """
    try:
        user_id = UUID(current_user.id)
        
        # Get quota usage
        quota_usage = await quota_manager.get_quota_usage(user_id)
        
        logger.info(
            "quota_usage_retrieved",
            user_id=str(user_id),
            username=current_user.username,
            cpu_used=quota_usage.cpu_cores_used,
            memory_used=quota_usage.memory_mb_used,
            concurrent_used=quota_usage.concurrent_executions_used,
            daily_used=quota_usage.daily_executions_used
        )
        
        return quota_usage.to_dict()
        
    except Exception as e:
        logger.error(
            "quota_usage_retrieval_failed",
            user_id=str(current_user.id),
            username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve quota usage"
        )


@router.get("/rate-limit", response_model=Dict[str, Any])
async def get_user_rate_limit(
    current_user: UserModel = Depends(get_current_user),
    rate_limiter: RateLimiter = Depends(get_rate_limiter)
):
    """
    Get current rate limit status for the authenticated user.
    
    Returns information about:
    - Current rate limit (requests per minute)
    - Remaining quota
    - Reset time
    - User tier
    
    **Requirements: 12.4**
    **Validates: Property 44 - Rate Limit Status Accuracy**
    
    Args:
        current_user: Currently authenticated user
        rate_limiter: Rate limiter instance
        
    Returns:
        Dictionary with rate limit status
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 500: If rate limit query fails
    """
    try:
        user_id = UUID(current_user.id)
        
        # Get rate limit status
        rate_limit_status = await rate_limiter.get_rate_limit_status(
            user_id=user_id,
            user_role=current_user.role,
            resource="executions"
        )
        
        # Get limits for all time windows
        from app.services.rate_limiter import RATE_LIMITS
        user_limits = RATE_LIMITS.get(current_user.role, RATE_LIMITS[current_user.role])
        
        logger.info(
            "rate_limit_status_retrieved",
            user_id=str(user_id),
            username=current_user.username,
            role=current_user.role.value,
            remaining=rate_limit_status.remaining,
            limit=rate_limit_status.limit
        )
        
        return {
            "user_id": str(user_id),
            "user_role": current_user.role.value,
            "limits": {
                "per_minute": user_limits["executions_per_minute"],
                "per_hour": user_limits["executions_per_hour"],
                "per_day": user_limits["executions_per_day"]
            },
            "current_window": {
                "limit": rate_limit_status.limit,
                "remaining": rate_limit_status.remaining,
                "reset_at": rate_limit_status.reset_at.isoformat()
            }
        }
        
    except Exception as e:
        logger.error(
            "rate_limit_status_retrieval_failed",
            user_id=str(current_user.id),
            username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit status"
        )


@router.get("/costs", response_model=Dict[str, Any])
async def get_user_costs(
    current_user: UserModel = Depends(get_current_user),
    cost_tracker: CostTracker = Depends(get_cost_tracker),
    period: str = "month"
):
    """
    Get cost summary for the authenticated user.
    
    Returns cost information for the specified period:
    - Total cost
    - Execution count
    - Costs by tool
    - Costs by day
    - Currency
    
    **Requirements: 18.3**
    **Validates: Property 73 - Cost Aggregation**
    
    Args:
        current_user: Currently authenticated user
        cost_tracker: Cost tracker instance
        period: Time period for costs ("day", "week", "month", "year")
        
    Returns:
        Dictionary with cost summary
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If invalid period specified
        HTTPException 500: If cost query fails
    """
    try:
        user_id = UUID(current_user.id)
        
        # Calculate date range based on period
        now = datetime.utcnow()
        
        if period == "day":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif period == "year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period: {period}. Must be one of: day, week, month, year"
            )
        
        date_range = DateRange(start_date=start_date, end_date=now)
        
        # Get cost summary
        cost_summary = await cost_tracker.get_user_costs(user_id, date_range)
        
        logger.info(
            "user_costs_retrieved",
            user_id=str(user_id),
            username=current_user.username,
            period=period,
            total_cost=float(cost_summary.total_cost),
            execution_count=cost_summary.execution_count,
            currency=cost_summary.currency
        )
        
        return {
            "user_id": str(user_id),
            "period": period,
            "period_start": cost_summary.period_start.isoformat(),
            "period_end": cost_summary.period_end.isoformat(),
            "total_cost": float(cost_summary.total_cost),
            "currency": cost_summary.currency,
            "execution_count": cost_summary.execution_count,
            "costs_by_tool": {
                tool_id: float(cost)
                for tool_id, cost in cost_summary.costs_by_tool.items()
            },
            "costs_by_day": {
                day: float(cost)
                for day, cost in cost_summary.costs_by_day.items()
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "user_costs_retrieval_failed",
            user_id=str(current_user.id),
            username=current_user.username,
            period=period,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cost information"
        )
