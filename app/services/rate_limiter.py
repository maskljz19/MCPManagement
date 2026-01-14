"""Rate Limiter Service - Enforces execution frequency limits per user"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID
from redis.asyncio import Redis

from app.models.user import UserRole
from app.core.logging_config import get_logger

logger = get_logger(__name__)


# Rate limit configuration by user tier
RATE_LIMITS = {
    UserRole.VIEWER: {
        "executions_per_minute": 10,
        "executions_per_hour": 100,
        "executions_per_day": 500
    },
    UserRole.DEVELOPER: {
        "executions_per_minute": 30,
        "executions_per_hour": 500,
        "executions_per_day": 5000
    },
    UserRole.ADMIN: {
        "executions_per_minute": 100,
        "executions_per_hour": 2000,
        "executions_per_day": 20000
    }
}


class RateLimitResult:
    """Result of rate limit check"""
    def __init__(
        self,
        allowed: bool,
        remaining: int,
        reset_at: datetime,
        retry_after: Optional[int] = None
    ):
        self.allowed = allowed
        self.remaining = remaining
        self.reset_at = reset_at
        self.retry_after = retry_after  # Seconds until retry allowed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat(),
            "retry_after": self.retry_after
        }


class RateLimitStatus:
    """Current rate limit status for a user"""
    def __init__(
        self,
        user_id: UUID,
        resource: str,
        limit: int,
        remaining: int,
        reset_at: datetime
    ):
        self.user_id = user_id
        self.resource = resource
        self.limit = limit
        self.remaining = remaining
        self.reset_at = reset_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "resource": self.resource,
            "limit": self.limit,
            "remaining": self.remaining,
            "reset_at": self.reset_at.isoformat()
        }


class RateLimiter:
    """
    Rate limiter using Redis sliding window algorithm.
    
    Enforces execution frequency limits per user based on their tier.
    Supports multiple time windows (minute, hour, day).
    
    **Requirements: 12.1, 12.2, 12.3, 12.4, 12.5**
    """
    
    def __init__(self, redis: Redis):
        """
        Initialize rate limiter.
        
        Args:
            redis: Redis client for storing rate limit data
        """
        self.redis = redis
        self.logger = get_logger(__name__)
    
    def _get_rate_limit_key(self, user_id: UUID, resource: str, window: str) -> str:
        """
        Generate Redis key for rate limit tracking.
        
        Args:
            user_id: User ID
            resource: Resource being rate limited (e.g., "executions")
            window: Time window (minute, hour, day)
            
        Returns:
            Redis key string
        """
        return f"ratelimit:{user_id}:{resource}:{window}"
    
    def _get_window_duration(self, window: str) -> int:
        """
        Get window duration in seconds.
        
        Args:
            window: Time window (minute, hour, day)
            
        Returns:
            Duration in seconds
        """
        durations = {
            "minute": 60,
            "hour": 3600,
            "day": 86400
        }
        return durations.get(window, 60)
    
    def _get_user_limits(self, user_role: UserRole, resource: str) -> Dict[str, int]:
        """
        Get rate limits for a user based on their role.
        
        Args:
            user_role: User's role
            resource: Resource being rate limited
            
        Returns:
            Dictionary of limits by time window
        """
        if resource == "executions":
            return RATE_LIMITS.get(user_role, RATE_LIMITS[UserRole.VIEWER])
        
        # Default limits for unknown resources
        return {
            "executions_per_minute": 10,
            "executions_per_hour": 100,
            "executions_per_day": 500
        }
    
    async def check_rate_limit(
        self,
        user_id: UUID,
        user_role: UserRole,
        resource: str = "executions"
    ) -> RateLimitResult:
        """
        Check if user has exceeded rate limit.
        
        Uses sliding window algorithm to track requests over time.
        Checks all time windows (minute, hour, day) and returns
        the most restrictive result.
        
        Args:
            user_id: User ID to check
            user_role: User's role for tier-based limits
            resource: Resource being rate limited (default: "executions")
            
        Returns:
            RateLimitResult indicating if request is allowed
            
        **Validates: Requirements 12.1, 12.3**
        """
        try:
            limits = self._get_user_limits(user_role, resource)
            current_time = time.time()
            
            # Check each time window
            windows = [
                ("minute", limits.get("executions_per_minute", 10)),
                ("hour", limits.get("executions_per_hour", 100)),
                ("day", limits.get("executions_per_day", 500))
            ]
            
            for window_name, limit in windows:
                key = self._get_rate_limit_key(user_id, resource, window_name)
                window_duration = self._get_window_duration(window_name)
                window_start = current_time - window_duration
                
                # Remove old entries outside the window
                await self.redis.zremrangebyscore(key, 0, window_start)
                
                # Count requests in current window
                count = await self.redis.zcard(key)
                
                if count >= limit:
                    # Rate limit exceeded
                    # Get oldest entry to calculate retry_after
                    oldest_entries = await self.redis.zrange(key, 0, 0, withscores=True)
                    if oldest_entries:
                        oldest_timestamp = oldest_entries[0][1]
                        retry_after = int(oldest_timestamp + window_duration - current_time) + 1
                    else:
                        retry_after = window_duration
                    
                    reset_at = datetime.fromtimestamp(current_time + retry_after)
                    
                    self.logger.warning(
                        "rate_limit_exceeded",
                        user_id=str(user_id),
                        resource=resource,
                        window=window_name,
                        limit=limit,
                        count=count,
                        retry_after=retry_after
                    )
                    
                    return RateLimitResult(
                        allowed=False,
                        remaining=0,
                        reset_at=reset_at,
                        retry_after=retry_after
                    )
            
            # All windows passed, request is allowed
            # Return status for the most restrictive window (minute)
            minute_key = self._get_rate_limit_key(user_id, resource, "minute")
            minute_count = await self.redis.zcard(minute_key)
            minute_limit = limits.get("executions_per_minute", 10)
            remaining = max(0, minute_limit - minute_count)
            reset_at = datetime.fromtimestamp(current_time + 60)
            
            return RateLimitResult(
                allowed=True,
                remaining=remaining,
                reset_at=reset_at,
                retry_after=None
            )
            
        except Exception as e:
            self.logger.error(
                "rate_limit_check_failed",
                user_id=str(user_id),
                resource=resource,
                error=str(e),
                exc_info=True
            )
            # Graceful degradation: allow request if Redis fails
            return RateLimitResult(
                allowed=True,
                remaining=0,
                reset_at=datetime.now() + timedelta(minutes=1),
                retry_after=None
            )
    
    async def consume_quota(
        self,
        user_id: UUID,
        user_role: UserRole,
        resource: str = "executions",
        amount: int = 1
    ) -> bool:
        """
        Consume rate limit quota for a user.
        
        Records the request in all time windows using sorted sets
        with timestamps as scores for sliding window algorithm.
        
        Args:
            user_id: User ID
            user_role: User's role for tier-based limits
            resource: Resource being consumed (default: "executions")
            amount: Amount to consume (default: 1)
            
        Returns:
            True if quota was consumed successfully
            
        **Validates: Requirements 12.1**
        """
        try:
            current_time = time.time()
            limits = self._get_user_limits(user_role, resource)
            
            # Add entry to all time windows
            windows = ["minute", "hour", "day"]
            
            for window_name in windows:
                key = self._get_rate_limit_key(user_id, resource, window_name)
                window_duration = self._get_window_duration(window_name)
                
                # Add current request(s) to sorted set
                # Use unique member names to allow multiple requests at same timestamp
                for i in range(amount):
                    member = f"{current_time}:{i}"
                    await self.redis.zadd(key, {member: current_time})
                
                # Set expiration to window duration + buffer
                await self.redis.expire(key, window_duration + 60)
            
            self.logger.debug(
                "rate_limit_quota_consumed",
                user_id=str(user_id),
                resource=resource,
                amount=amount
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "rate_limit_consume_failed",
                user_id=str(user_id),
                resource=resource,
                amount=amount,
                error=str(e),
                exc_info=True
            )
            # Graceful degradation: return success even if Redis fails
            return True
    
    async def get_rate_limit_status(
        self,
        user_id: UUID,
        user_role: UserRole,
        resource: str = "executions"
    ) -> RateLimitStatus:
        """
        Get current rate limit status for a user.
        
        Returns remaining quota and reset time for the most
        restrictive window (minute).
        
        Args:
            user_id: User ID
            user_role: User's role for tier-based limits
            resource: Resource to check (default: "executions")
            
        Returns:
            RateLimitStatus with current status
            
        **Validates: Requirements 12.4**
        """
        try:
            limits = self._get_user_limits(user_role, resource)
            current_time = time.time()
            
            # Get status for minute window (most restrictive)
            key = self._get_rate_limit_key(user_id, resource, "minute")
            window_duration = self._get_window_duration("minute")
            window_start = current_time - window_duration
            
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            count = await self.redis.zcard(key)
            limit = limits.get("executions_per_minute", 10)
            remaining = max(0, limit - count)
            reset_at = datetime.fromtimestamp(current_time + window_duration)
            
            return RateLimitStatus(
                user_id=user_id,
                resource=resource,
                limit=limit,
                remaining=remaining,
                reset_at=reset_at
            )
            
        except Exception as e:
            self.logger.error(
                "rate_limit_status_failed",
                user_id=str(user_id),
                resource=resource,
                error=str(e),
                exc_info=True
            )
            # Return default status on error
            return RateLimitStatus(
                user_id=user_id,
                resource=resource,
                limit=10,
                remaining=10,
                reset_at=datetime.now() + timedelta(minutes=1)
            )
    
    async def reset_rate_limit(
        self,
        user_id: UUID,
        resource: str = "executions"
    ) -> None:
        """
        Reset rate limit for a user (admin function).
        
        Clears all rate limit data for the user across all time windows.
        
        Args:
            user_id: User ID to reset
            resource: Resource to reset (default: "executions")
            
        **Validates: Requirements 12.5**
        """
        try:
            windows = ["minute", "hour", "day"]
            
            for window_name in windows:
                key = self._get_rate_limit_key(user_id, resource, window_name)
                await self.redis.delete(key)
            
            self.logger.info(
                "rate_limit_reset",
                user_id=str(user_id),
                resource=resource
            )
            
        except Exception as e:
            self.logger.error(
                "rate_limit_reset_failed",
                user_id=str(user_id),
                resource=resource,
                error=str(e),
                exc_info=True
            )
            raise
