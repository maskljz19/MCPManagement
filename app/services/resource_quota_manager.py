"""Resource Quota Manager - Manages CPU, memory, and concurrency quotas"""

import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from uuid import UUID
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field

from app.models.resource_quota import ResourceQuotaModel
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ResourceRequirements(BaseModel):
    """Resource requirements for an execution"""
    cpu_cores: float = Field(default=1.0, ge=0.1, le=32.0)
    memory_mb: int = Field(default=512, ge=128, le=32768)
    concurrent_executions: int = Field(default=1, ge=1, le=100)
    estimated_duration_seconds: int = Field(default=30, ge=1, le=3600)


class QuotaCheckResult(BaseModel):
    """Result of quota check"""
    allowed: bool
    reason: Optional[str] = None
    exceeded_resource: Optional[str] = None
    current_usage: Optional[Dict[str, Any]] = None
    quota_limits: Optional[Dict[str, Any]] = None


class QuotaUsage(BaseModel):
    """Current quota usage for a user"""
    user_id: UUID
    cpu_cores_used: float
    cpu_cores_available: float
    cpu_cores_limit: float
    memory_mb_used: int
    memory_mb_available: int
    memory_mb_limit: int
    concurrent_executions_used: int
    concurrent_executions_available: int
    concurrent_executions_limit: int
    daily_executions_used: int
    daily_executions_available: int
    daily_executions_limit: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "cpu": {
                "used": self.cpu_cores_used,
                "available": self.cpu_cores_available,
                "limit": self.cpu_cores_limit
            },
            "memory": {
                "used_mb": self.memory_mb_used,
                "available_mb": self.memory_mb_available,
                "limit_mb": self.memory_mb_limit
            },
            "concurrent_executions": {
                "used": self.concurrent_executions_used,
                "available": self.concurrent_executions_available,
                "limit": self.concurrent_executions_limit
            },
            "daily_executions": {
                "used": self.daily_executions_used,
                "available": self.daily_executions_available,
                "limit": self.daily_executions_limit
            }
        }


class ResourceQuotaManager:
    """
    Resource Quota Manager enforces resource limits per user.
    
    Responsibilities:
    - Check if user has available quota before execution
    - Allocate resources when execution starts
    - Release resources when execution completes
    - Track daily execution counts
    - Support admin quota updates
    
    Uses Redis for real-time resource tracking and MySQL for quota configuration.
    
    **Requirements: 13.1, 13.2, 13.3, 13.4, 13.5**
    """
    
    # Redis key prefixes
    CPU_KEY_PREFIX = "quota:cpu:"
    MEMORY_KEY_PREFIX = "quota:memory:"
    CONCURRENT_KEY_PREFIX = "quota:concurrent:"
    DAILY_KEY_PREFIX = "quota:daily:"
    ALLOCATION_KEY_PREFIX = "quota:allocation:"
    
    # Default quotas (fallback if not in database)
    DEFAULT_QUOTAS = {
        "max_cpu_cores": 4.0,
        "max_memory_mb": 4096,
        "max_concurrent_executions": 5,
        "max_daily_executions": 1000
    }
    
    def __init__(self, redis: Redis, db_session: AsyncSession):
        """
        Initialize Resource Quota Manager.
        
        Args:
            redis: Redis client for real-time tracking
            db_session: Database session for quota configuration
        """
        self.redis = redis
        self.db_session = db_session
        self.logger = get_logger(__name__)
    
    # ========================================================================
    # Quota Checking (Requirement 13.1)
    # ========================================================================
    
    async def check_quota(
        self,
        user_id: UUID,
        resource_requirements: ResourceRequirements
    ) -> QuotaCheckResult:
        """
        Check if user has available quota for the requested resources.
        
        Verifies:
        - CPU cores available
        - Memory available
        - Concurrent execution slots available
        - Daily execution limit not exceeded
        
        Args:
            user_id: User ID to check
            resource_requirements: Required resources for execution
            
        Returns:
            QuotaCheckResult indicating if execution is allowed
            
        **Validates: Requirements 13.1**
        """
        try:
            # Get user's quota limits from database
            quota_limits = await self._get_user_quota_limits(user_id)
            
            # Get current usage from Redis
            current_usage = await self._get_current_usage(user_id)
            
            # Check CPU quota
            cpu_available = quota_limits["max_cpu_cores"] - current_usage["cpu_cores"]
            if resource_requirements.cpu_cores > cpu_available:
                self.logger.warning(
                    "quota_exceeded_cpu",
                    user_id=str(user_id),
                    required=resource_requirements.cpu_cores,
                    available=cpu_available,
                    limit=quota_limits["max_cpu_cores"]
                )
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"CPU quota exceeded. Required: {resource_requirements.cpu_cores} cores, Available: {cpu_available} cores",
                    exceeded_resource="cpu_cores",
                    current_usage=current_usage,
                    quota_limits=quota_limits
                )
            
            # Check memory quota
            memory_available = quota_limits["max_memory_mb"] - current_usage["memory_mb"]
            if resource_requirements.memory_mb > memory_available:
                self.logger.warning(
                    "quota_exceeded_memory",
                    user_id=str(user_id),
                    required=resource_requirements.memory_mb,
                    available=memory_available,
                    limit=quota_limits["max_memory_mb"]
                )
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Memory quota exceeded. Required: {resource_requirements.memory_mb} MB, Available: {memory_available} MB",
                    exceeded_resource="memory_mb",
                    current_usage=current_usage,
                    quota_limits=quota_limits
                )
            
            # Check concurrent executions quota
            concurrent_available = quota_limits["max_concurrent_executions"] - current_usage["concurrent_executions"]
            if resource_requirements.concurrent_executions > concurrent_available:
                self.logger.warning(
                    "quota_exceeded_concurrent",
                    user_id=str(user_id),
                    required=resource_requirements.concurrent_executions,
                    available=concurrent_available,
                    limit=quota_limits["max_concurrent_executions"]
                )
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Concurrent execution quota exceeded. Required: {resource_requirements.concurrent_executions}, Available: {concurrent_available}",
                    exceeded_resource="concurrent_executions",
                    current_usage=current_usage,
                    quota_limits=quota_limits
                )
            
            # Check daily executions quota
            daily_available = quota_limits["max_daily_executions"] - current_usage["daily_executions"]
            if daily_available <= 0:
                self.logger.warning(
                    "quota_exceeded_daily",
                    user_id=str(user_id),
                    used=current_usage["daily_executions"],
                    limit=quota_limits["max_daily_executions"]
                )
                return QuotaCheckResult(
                    allowed=False,
                    reason=f"Daily execution quota exceeded. Limit: {quota_limits['max_daily_executions']} executions per day",
                    exceeded_resource="daily_executions",
                    current_usage=current_usage,
                    quota_limits=quota_limits
                )
            
            # All checks passed
            return QuotaCheckResult(
                allowed=True,
                reason=None,
                exceeded_resource=None,
                current_usage=current_usage,
                quota_limits=quota_limits
            )
            
        except Exception as e:
            self.logger.error(
                "quota_check_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            # Graceful degradation: allow execution if check fails
            return QuotaCheckResult(
                allowed=True,
                reason="Quota check failed, allowing execution",
                exceeded_resource=None,
                current_usage=None,
                quota_limits=None
            )
    
    # ========================================================================
    # Resource Allocation (Requirement 13.1, 13.2)
    # ========================================================================
    
    async def allocate_resources(
        self,
        execution_id: UUID,
        user_id: UUID,
        resources: ResourceRequirements
    ) -> bool:
        """
        Allocate resources for an execution.
        
        Records resource allocation in Redis for tracking.
        Increments usage counters for CPU, memory, concurrent executions, and daily count.
        
        Args:
            execution_id: Execution ID
            user_id: User ID
            resources: Resources to allocate
            
        Returns:
            True if allocation successful
            
        **Validates: Requirements 13.1**
        """
        try:
            # Increment CPU usage
            cpu_key = f"{self.CPU_KEY_PREFIX}{user_id}"
            await self.redis.incrbyfloat(cpu_key, resources.cpu_cores)
            
            # Increment memory usage
            memory_key = f"{self.MEMORY_KEY_PREFIX}{user_id}"
            await self.redis.incrby(memory_key, resources.memory_mb)
            
            # Increment concurrent executions
            concurrent_key = f"{self.CONCURRENT_KEY_PREFIX}{user_id}"
            await self.redis.incr(concurrent_key)
            
            # Increment daily executions (with expiration at end of day)
            daily_key = f"{self.DAILY_KEY_PREFIX}{user_id}"
            await self.redis.incr(daily_key)
            
            # Set expiration to end of day if not already set
            ttl = await self.redis.ttl(daily_key)
            if ttl == -1:  # No expiration set
                # Calculate seconds until end of day
                now = datetime.now()
                end_of_day = datetime.combine(now.date() + timedelta(days=1), datetime.min.time())
                seconds_until_eod = int((end_of_day - now).total_seconds())
                await self.redis.expire(daily_key, seconds_until_eod)
            
            # Store allocation details for later release
            allocation_key = f"{self.ALLOCATION_KEY_PREFIX}{execution_id}"
            allocation_data = {
                "user_id": str(user_id),
                "cpu_cores": str(resources.cpu_cores),
                "memory_mb": str(resources.memory_mb),
                "concurrent_executions": str(resources.concurrent_executions),
                "allocated_at": str(time.time())
            }
            await self.redis.hset(allocation_key, mapping=allocation_data)
            
            # Set expiration for allocation record (24 hours)
            await self.redis.expire(allocation_key, 86400)
            
            self.logger.info(
                "resources_allocated",
                execution_id=str(execution_id),
                user_id=str(user_id),
                cpu_cores=resources.cpu_cores,
                memory_mb=resources.memory_mb,
                concurrent_executions=resources.concurrent_executions
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "resource_allocation_failed",
                execution_id=str(execution_id),
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            return False
    
    # ========================================================================
    # Resource Release (Requirement 13.3)
    # ========================================================================
    
    async def release_resources(
        self,
        execution_id: UUID
    ) -> None:
        """
        Release resources allocated for an execution.
        
        Decrements usage counters based on the allocation record.
        Called when execution completes, fails, or is cancelled.
        
        Args:
            execution_id: Execution ID
            
        **Validates: Requirements 13.3**
        """
        try:
            # Get allocation details
            allocation_key = f"{self.ALLOCATION_KEY_PREFIX}{execution_id}"
            allocation_data = await self.redis.hgetall(allocation_key)
            
            if not allocation_data:
                self.logger.warning(
                    "allocation_not_found",
                    execution_id=str(execution_id)
                )
                return
            
            # Parse allocation data
            user_id = UUID(allocation_data["user_id"])
            cpu_cores = float(allocation_data["cpu_cores"])
            memory_mb = int(allocation_data["memory_mb"])
            concurrent_executions = int(allocation_data["concurrent_executions"])
            
            # Decrement CPU usage
            cpu_key = f"{self.CPU_KEY_PREFIX}{user_id}"
            new_cpu = await self.redis.incrbyfloat(cpu_key, -cpu_cores)
            # Ensure it doesn't go negative
            if new_cpu < 0:
                await self.redis.set(cpu_key, "0")
            
            # Decrement memory usage
            memory_key = f"{self.MEMORY_KEY_PREFIX}{user_id}"
            new_memory = await self.redis.decrby(memory_key, memory_mb)
            # Ensure it doesn't go negative
            if new_memory < 0:
                await self.redis.set(memory_key, "0")
            
            # Decrement concurrent executions
            concurrent_key = f"{self.CONCURRENT_KEY_PREFIX}{user_id}"
            new_concurrent = await self.redis.decr(concurrent_key)
            # Ensure it doesn't go negative
            if new_concurrent < 0:
                await self.redis.set(concurrent_key, "0")
            
            # Delete allocation record
            await self.redis.delete(allocation_key)
            
            self.logger.info(
                "resources_released",
                execution_id=str(execution_id),
                user_id=str(user_id),
                cpu_cores=cpu_cores,
                memory_mb=memory_mb,
                concurrent_executions=concurrent_executions
            )
            
        except Exception as e:
            self.logger.error(
                "resource_release_failed",
                execution_id=str(execution_id),
                error=str(e),
                exc_info=True
            )
    
    # ========================================================================
    # Quota Usage Queries (Requirement 13.5)
    # ========================================================================
    
    async def get_quota_usage(
        self,
        user_id: UUID
    ) -> QuotaUsage:
        """
        Get current quota usage for a user.
        
        Returns current usage and available capacity for all resource types.
        
        Args:
            user_id: User ID
            
        Returns:
            QuotaUsage with current usage and limits
            
        **Validates: Requirements 13.5**
        """
        try:
            # Get quota limits
            quota_limits = await self._get_user_quota_limits(user_id)
            
            # Get current usage
            current_usage = await self._get_current_usage(user_id)
            
            # Calculate available capacity
            cpu_available = max(0, quota_limits["max_cpu_cores"] - current_usage["cpu_cores"])
            memory_available = max(0, quota_limits["max_memory_mb"] - current_usage["memory_mb"])
            concurrent_available = max(0, quota_limits["max_concurrent_executions"] - current_usage["concurrent_executions"])
            daily_available = max(0, quota_limits["max_daily_executions"] - current_usage["daily_executions"])
            
            return QuotaUsage(
                user_id=user_id,
                cpu_cores_used=current_usage["cpu_cores"],
                cpu_cores_available=cpu_available,
                cpu_cores_limit=quota_limits["max_cpu_cores"],
                memory_mb_used=current_usage["memory_mb"],
                memory_mb_available=memory_available,
                memory_mb_limit=quota_limits["max_memory_mb"],
                concurrent_executions_used=current_usage["concurrent_executions"],
                concurrent_executions_available=concurrent_available,
                concurrent_executions_limit=quota_limits["max_concurrent_executions"],
                daily_executions_used=current_usage["daily_executions"],
                daily_executions_available=daily_available,
                daily_executions_limit=quota_limits["max_daily_executions"]
            )
            
        except Exception as e:
            self.logger.error(
                "quota_usage_query_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            # Return default usage on error
            return QuotaUsage(
                user_id=user_id,
                cpu_cores_used=0.0,
                cpu_cores_available=self.DEFAULT_QUOTAS["max_cpu_cores"],
                cpu_cores_limit=self.DEFAULT_QUOTAS["max_cpu_cores"],
                memory_mb_used=0,
                memory_mb_available=self.DEFAULT_QUOTAS["max_memory_mb"],
                memory_mb_limit=self.DEFAULT_QUOTAS["max_memory_mb"],
                concurrent_executions_used=0,
                concurrent_executions_available=self.DEFAULT_QUOTAS["max_concurrent_executions"],
                concurrent_executions_limit=self.DEFAULT_QUOTAS["max_concurrent_executions"],
                daily_executions_used=0,
                daily_executions_available=self.DEFAULT_QUOTAS["max_daily_executions"],
                daily_executions_limit=self.DEFAULT_QUOTAS["max_daily_executions"]
            )
    
    # ========================================================================
    # Admin Quota Updates (Requirement 13.4)
    # ========================================================================
    
    async def update_user_quota(
        self,
        user_id: UUID,
        max_cpu_cores: Optional[float] = None,
        max_memory_mb: Optional[int] = None,
        max_concurrent_executions: Optional[int] = None,
        max_daily_executions: Optional[int] = None
    ) -> ResourceQuotaModel:
        """
        Update quota limits for a user (admin function).
        
        New limits apply to all future executions immediately.
        Does not affect currently running executions.
        
        Args:
            user_id: User ID
            max_cpu_cores: Maximum CPU cores (optional)
            max_memory_mb: Maximum memory in MB (optional)
            max_concurrent_executions: Maximum concurrent executions (optional)
            max_daily_executions: Maximum daily executions (optional)
            
        Returns:
            Updated ResourceQuotaModel
            
        **Validates: Requirements 13.4**
        """
        try:
            # Get existing quota or create new one
            stmt = select(ResourceQuotaModel).where(ResourceQuotaModel.user_id == str(user_id))
            result = await self.db_session.execute(stmt)
            quota = result.scalar_one_or_none()
            
            if not quota:
                # Create new quota
                from uuid import uuid4
                quota = ResourceQuotaModel(
                    id=str(uuid4()),
                    user_id=str(user_id),
                    max_cpu_cores=max_cpu_cores or self.DEFAULT_QUOTAS["max_cpu_cores"],
                    max_memory_mb=max_memory_mb or self.DEFAULT_QUOTAS["max_memory_mb"],
                    max_concurrent_executions=max_concurrent_executions or self.DEFAULT_QUOTAS["max_concurrent_executions"],
                    max_daily_executions=max_daily_executions or self.DEFAULT_QUOTAS["max_daily_executions"],
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                self.db_session.add(quota)
            else:
                # Update existing quota
                if max_cpu_cores is not None:
                    quota.max_cpu_cores = max_cpu_cores
                if max_memory_mb is not None:
                    quota.max_memory_mb = max_memory_mb
                if max_concurrent_executions is not None:
                    quota.max_concurrent_executions = max_concurrent_executions
                if max_daily_executions is not None:
                    quota.max_daily_executions = max_daily_executions
                quota.updated_at = datetime.now()
            
            await self.db_session.commit()
            await self.db_session.refresh(quota)
            
            self.logger.info(
                "quota_updated",
                user_id=str(user_id),
                max_cpu_cores=quota.max_cpu_cores,
                max_memory_mb=quota.max_memory_mb,
                max_concurrent_executions=quota.max_concurrent_executions,
                max_daily_executions=quota.max_daily_executions
            )
            
            return quota
            
        except Exception as e:
            self.logger.error(
                "quota_update_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            await self.db_session.rollback()
            raise
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    async def _get_user_quota_limits(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get quota limits for a user from database.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with quota limits
        """
        try:
            stmt = select(ResourceQuotaModel).where(ResourceQuotaModel.user_id == str(user_id))
            result = await self.db_session.execute(stmt)
            quota = result.scalar_one_or_none()
            
            if quota:
                return {
                    "max_cpu_cores": quota.max_cpu_cores,
                    "max_memory_mb": quota.max_memory_mb,
                    "max_concurrent_executions": quota.max_concurrent_executions,
                    "max_daily_executions": quota.max_daily_executions
                }
            else:
                # Return default quotas
                return self.DEFAULT_QUOTAS.copy()
                
        except Exception as e:
            self.logger.error(
                "get_quota_limits_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            return self.DEFAULT_QUOTAS.copy()
    
    async def _get_current_usage(self, user_id: UUID) -> Dict[str, Any]:
        """
        Get current resource usage for a user from Redis.
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary with current usage
        """
        try:
            # Get CPU usage
            cpu_key = f"{self.CPU_KEY_PREFIX}{user_id}"
            cpu_usage_str = await self.redis.get(cpu_key)
            cpu_usage = float(cpu_usage_str) if cpu_usage_str else 0.0
            
            # Get memory usage
            memory_key = f"{self.MEMORY_KEY_PREFIX}{user_id}"
            memory_usage_str = await self.redis.get(memory_key)
            memory_usage = int(memory_usage_str) if memory_usage_str else 0
            
            # Get concurrent executions
            concurrent_key = f"{self.CONCURRENT_KEY_PREFIX}{user_id}"
            concurrent_usage_str = await self.redis.get(concurrent_key)
            concurrent_usage = int(concurrent_usage_str) if concurrent_usage_str else 0
            
            # Get daily executions
            daily_key = f"{self.DAILY_KEY_PREFIX}{user_id}"
            daily_usage_str = await self.redis.get(daily_key)
            daily_usage = int(daily_usage_str) if daily_usage_str else 0
            
            return {
                "cpu_cores": cpu_usage,
                "memory_mb": memory_usage,
                "concurrent_executions": concurrent_usage,
                "daily_executions": daily_usage
            }
            
        except Exception as e:
            self.logger.error(
                "get_current_usage_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
            return {
                "cpu_cores": 0.0,
                "memory_mb": 0,
                "concurrent_executions": 0,
                "daily_executions": 0
            }
    
    async def reset_daily_executions(self, user_id: UUID) -> None:
        """
        Reset daily execution count for a user (admin function).
        
        Args:
            user_id: User ID
        """
        try:
            daily_key = f"{self.DAILY_KEY_PREFIX}{user_id}"
            await self.redis.delete(daily_key)
            
            self.logger.info(
                "daily_executions_reset",
                user_id=str(user_id)
            )
            
        except Exception as e:
            self.logger.error(
                "reset_daily_executions_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
    
    async def reset_all_usage(self, user_id: UUID) -> None:
        """
        Reset all resource usage for a user (admin function).
        
        Does not affect currently running executions.
        
        Args:
            user_id: User ID
        """
        try:
            # Reset all usage counters
            cpu_key = f"{self.CPU_KEY_PREFIX}{user_id}"
            memory_key = f"{self.MEMORY_KEY_PREFIX}{user_id}"
            concurrent_key = f"{self.CONCURRENT_KEY_PREFIX}{user_id}"
            daily_key = f"{self.DAILY_KEY_PREFIX}{user_id}"
            
            await self.redis.delete(cpu_key, memory_key, concurrent_key, daily_key)
            
            self.logger.info(
                "all_usage_reset",
                user_id=str(user_id)
            )
            
        except Exception as e:
            self.logger.error(
                "reset_all_usage_failed",
                user_id=str(user_id),
                error=str(e),
                exc_info=True
            )
