"""Execution Queue Manager Service - Manages priority-based execution queue"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from redis.asyncio import Redis

from app.models.execution_queue import ExecutionQueueModel, QueueStatus
from app.models.user import UserModel, UserRole
from app.schemas.mcp_execution import ExecutionOptions
from app.core.exceptions import MCPExecutionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class QueuePosition:
    """Queue position information"""
    def __init__(
        self,
        execution_id: UUID,
        position: int,
        estimated_wait_seconds: int,
        total_queued: int
    ):
        self.execution_id = execution_id
        self.position = position
        self.estimated_wait_seconds = estimated_wait_seconds
        self.total_queued = total_queued
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": str(self.execution_id),
            "position": self.position,
            "estimated_wait_seconds": self.estimated_wait_seconds,
            "total_queued": self.total_queued
        }


class QueueStats:
    """Queue statistics"""
    def __init__(
        self,
        total_queued: int,
        total_processing: int,
        total_completed: int,
        total_failed: int,
        total_cancelled: int,
        average_wait_time_seconds: float
    ):
        self.total_queued = total_queued
        self.total_processing = total_processing
        self.total_completed = total_completed
        self.total_failed = total_failed
        self.total_cancelled = total_cancelled
        self.average_wait_time_seconds = average_wait_time_seconds
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_queued": self.total_queued,
            "total_processing": self.total_processing,
            "total_completed": self.total_completed,
            "total_failed": self.total_failed,
            "total_cancelled": self.total_cancelled,
            "average_wait_time_seconds": self.average_wait_time_seconds
        }


class ExecutionRequest:
    """Execution request data"""
    def __init__(
        self,
        execution_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        options: ExecutionOptions,
        priority: int
    ):
        self.execution_id = execution_id
        self.tool_id = tool_id
        self.user_id = user_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.options = options
        self.priority = priority


class QueuedExecution:
    """Queued execution information"""
    def __init__(
        self,
        execution_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        tool_name: str,
        status: QueueStatus,
        priority: int,
        queue_position: Optional[int],
        estimated_wait_seconds: Optional[int],
        queued_at: datetime
    ):
        self.execution_id = execution_id
        self.tool_id = tool_id
        self.user_id = user_id
        self.tool_name = tool_name
        self.status = status
        self.priority = priority
        self.queue_position = queue_position
        self.estimated_wait_seconds = estimated_wait_seconds
        self.queued_at = queued_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": str(self.execution_id),
            "tool_id": str(self.tool_id),
            "user_id": str(self.user_id),
            "tool_name": self.tool_name,
            "status": self.status.value,
            "priority": self.priority,
            "queue_position": self.queue_position,
            "estimated_wait_seconds": self.estimated_wait_seconds,
            "queued_at": self.queued_at.isoformat()
        }


class ExecutionQueueManager:
    """
    Manages priority-based execution queue for MCP tools.
    
    Responsibilities:
    - Enqueue execution requests with priority calculation
    - Dequeue highest priority requests for execution
    - Track queue positions and estimated wait times
    - Enforce queue capacity limits per user tier
    - Handle queue cancellations
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4, 6.5**
    """
    
    # Queue capacity limits per user tier
    QUEUE_CAPACITY_LIMITS = {
        UserRole.VIEWER: 10,
        UserRole.DEVELOPER: 50,
        UserRole.ADMIN: 200
    }
    
    # Global queue capacity limit
    GLOBAL_QUEUE_CAPACITY = 1000
    
    # Priority bonuses per user tier
    TIER_PRIORITY_BONUS = {
        UserRole.VIEWER: 0,
        UserRole.DEVELOPER: 2,
        UserRole.ADMIN: 5
    }
    
    # Average execution time for wait time estimation (seconds)
    AVERAGE_EXECUTION_TIME = 30
    
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Optional[Redis] = None
    ):
        self.db = db_session
        self.redis = redis_client
    
    async def enqueue(
        self,
        execution_request: ExecutionRequest,
        user_role: UserRole
    ) -> QueuedExecution:
        """
        Enqueue an execution request with priority calculation.
        
        Priority calculation:
        - Base priority from request (1-10)
        - User tier bonus (VIEWER: 0, DEVELOPER: +2, ADMIN: +5)
        - Age penalty: -1 for every 5 minutes in queue (applied during dequeue)
        
        Args:
            execution_request: The execution request to enqueue
            user_role: Role of the user making the request
            
        Returns:
            QueuedExecution with queue position and estimated wait time
            
        Raises:
            MCPExecutionError: If queue capacity exceeded
            
        **Validates: Requirements 6.1, 6.5**
        """
        # Check global queue capacity
        total_queued = await self._get_total_queued()
        if total_queued >= self.GLOBAL_QUEUE_CAPACITY:
            logger.warning(
                "queue_capacity_exceeded",
                total_queued=total_queued,
                global_capacity=self.GLOBAL_QUEUE_CAPACITY
            )
            raise MCPExecutionError(
                "Queue capacity exceeded. Please try again later.",
                status_code=503
            )
        
        # Check user-specific queue capacity
        user_queued = await self._get_user_queued_count(execution_request.user_id)
        user_limit = self.QUEUE_CAPACITY_LIMITS.get(user_role, self.QUEUE_CAPACITY_LIMITS[UserRole.VIEWER])
        
        if user_queued >= user_limit:
            logger.warning(
                "user_queue_capacity_exceeded",
                user_id=str(execution_request.user_id),
                user_queued=user_queued,
                user_limit=user_limit,
                user_role=user_role.value
            )
            raise MCPExecutionError(
                f"User queue capacity exceeded. Maximum {user_limit} queued executions allowed.",
                status_code=429
            )
        
        # Calculate priority with tier bonus
        base_priority = execution_request.priority
        tier_bonus = self.TIER_PRIORITY_BONUS.get(user_role, 0)
        final_priority = base_priority + tier_bonus
        
        # Create queue entry
        queued_at = datetime.utcnow()
        queue_entry = ExecutionQueueModel(
            id=str(execution_request.execution_id),
            tool_id=str(execution_request.tool_id),
            user_id=str(execution_request.user_id),
            tool_name=execution_request.tool_name,
            arguments=execution_request.arguments,
            options=execution_request.options.model_dump(),
            priority=final_priority,
            status=QueueStatus.QUEUED,
            queued_at=queued_at
        )
        
        self.db.add(queue_entry)
        await self.db.commit()
        await self.db.refresh(queue_entry)
        
        # Add to Redis sorted set for fast priority-based retrieval
        if self.redis:
            # Score = priority * 1000000 - timestamp (higher priority and older = higher score)
            score = final_priority * 1000000 - int(queued_at.timestamp())
            await self.redis.zadd(
                "queue:executions",
                {str(execution_request.execution_id): score}
            )
        
        # Calculate queue position and estimated wait time
        queue_position = await self._calculate_queue_position(execution_request.execution_id, final_priority)
        estimated_wait = self._estimate_wait_time(queue_position)
        
        # Update queue entry with position and estimate
        queue_entry.queue_position = queue_position
        queue_entry.estimated_wait_seconds = estimated_wait
        await self.db.commit()
        
        logger.info(
            "execution_enqueued",
            execution_id=str(execution_request.execution_id),
            tool_id=str(execution_request.tool_id),
            user_id=str(execution_request.user_id),
            priority=final_priority,
            queue_position=queue_position,
            estimated_wait_seconds=estimated_wait
        )
        
        return QueuedExecution(
            execution_id=execution_request.execution_id,
            tool_id=execution_request.tool_id,
            user_id=execution_request.user_id,
            tool_name=execution_request.tool_name,
            status=QueueStatus.QUEUED,
            priority=final_priority,
            queue_position=queue_position,
            estimated_wait_seconds=estimated_wait,
            queued_at=queued_at
        )
    
    async def dequeue(self) -> Optional[ExecutionRequest]:
        """
        Dequeue the highest priority execution request.
        
        Priority ordering:
        1. Higher priority value
        2. Older queued time (FIFO within same priority)
        
        Returns:
            ExecutionRequest if available, None if queue is empty
            
        **Validates: Requirements 6.2**
        """
        # Try Redis first for fast retrieval
        if self.redis:
            # Get highest score (highest priority, oldest)
            items = await self.redis.zrange(
                "queue:executions",
                0,
                0,
                desc=True,
                withscores=True
            )
            
            if items:
                execution_id_str = items[0][0].decode() if isinstance(items[0][0], bytes) else items[0][0]
                
                # Remove from Redis
                await self.redis.zrem("queue:executions", execution_id_str)
                
                # Get from database and update status
                stmt = select(ExecutionQueueModel).where(
                    and_(
                        ExecutionQueueModel.id == execution_id_str,
                        ExecutionQueueModel.status == QueueStatus.QUEUED
                    )
                )
                result = await self.db.execute(stmt)
                queue_entry = result.scalar_one_or_none()
                
                if queue_entry:
                    # Update status to processing
                    queue_entry.status = QueueStatus.PROCESSING
                    queue_entry.started_at = datetime.utcnow()
                    await self.db.commit()
                    
                    # Parse options
                    options = ExecutionOptions(**queue_entry.options)
                    
                    logger.info(
                        "execution_dequeued",
                        execution_id=queue_entry.id,
                        tool_id=queue_entry.tool_id,
                        priority=queue_entry.priority
                    )
                    
                    return ExecutionRequest(
                        execution_id=UUID(queue_entry.id),
                        tool_id=UUID(queue_entry.tool_id),
                        user_id=UUID(queue_entry.user_id),
                        tool_name=queue_entry.tool_name,
                        arguments=queue_entry.arguments,
                        options=options,
                        priority=queue_entry.priority
                    )
        
        # Fallback to database query
        stmt = select(ExecutionQueueModel).where(
            ExecutionQueueModel.status == QueueStatus.QUEUED
        ).order_by(
            ExecutionQueueModel.priority.desc(),
            ExecutionQueueModel.queued_at.asc()
        ).limit(1)
        
        result = await self.db.execute(stmt)
        queue_entry = result.scalar_one_or_none()
        
        if not queue_entry:
            return None
        
        # Update status to processing
        queue_entry.status = QueueStatus.PROCESSING
        queue_entry.started_at = datetime.utcnow()
        await self.db.commit()
        
        # Remove from Redis if present
        if self.redis:
            await self.redis.zrem("queue:executions", queue_entry.id)
        
        # Parse options
        options = ExecutionOptions(**queue_entry.options)
        
        logger.info(
            "execution_dequeued",
            execution_id=queue_entry.id,
            tool_id=queue_entry.tool_id,
            priority=queue_entry.priority
        )
        
        return ExecutionRequest(
            execution_id=UUID(queue_entry.id),
            tool_id=UUID(queue_entry.tool_id),
            user_id=UUID(queue_entry.user_id),
            tool_name=queue_entry.tool_name,
            arguments=queue_entry.arguments,
            options=options,
            priority=queue_entry.priority
        )
    
    async def get_queue_position(
        self,
        execution_id: UUID
    ) -> QueuePosition:
        """
        Get the current queue position for an execution.
        
        Args:
            execution_id: ID of the execution to query
            
        Returns:
            QueuePosition with current position and estimated wait time
            
        Raises:
            MCPExecutionError: If execution not found in queue
            
        **Validates: Requirements 6.3**
        """
        # Get queue entry
        stmt = select(ExecutionQueueModel).where(
            ExecutionQueueModel.id == str(execution_id)
        )
        result = await self.db.execute(stmt)
        queue_entry = result.scalar_one_or_none()
        
        if not queue_entry:
            raise MCPExecutionError(f"Execution {execution_id} not found in queue")
        
        if queue_entry.status != QueueStatus.QUEUED:
            raise MCPExecutionError(
                f"Execution {execution_id} is not queued (status: {queue_entry.status.value})"
            )
        
        # Calculate current position
        position = await self._calculate_queue_position(execution_id, queue_entry.priority)
        estimated_wait = self._estimate_wait_time(position)
        
        # Get total queued
        total_queued = await self._get_total_queued()
        
        logger.debug(
            "queue_position_queried",
            execution_id=str(execution_id),
            position=position,
            estimated_wait_seconds=estimated_wait,
            total_queued=total_queued
        )
        
        return QueuePosition(
            execution_id=execution_id,
            position=position,
            estimated_wait_seconds=estimated_wait,
            total_queued=total_queued
        )
    
    async def cancel_queued(
        self,
        execution_id: UUID
    ) -> bool:
        """
        Cancel a queued execution and update queue positions.
        
        Args:
            execution_id: ID of the execution to cancel
            
        Returns:
            True if cancellation successful, False if not found or already processing
            
        **Validates: Requirements 6.4**
        """
        # Get queue entry
        stmt = select(ExecutionQueueModel).where(
            ExecutionQueueModel.id == str(execution_id)
        )
        result = await self.db.execute(stmt)
        queue_entry = result.scalar_one_or_none()
        
        if not queue_entry:
            logger.warning(
                "cancel_queued_not_found",
                execution_id=str(execution_id)
            )
            return False
        
        if queue_entry.status != QueueStatus.QUEUED:
            logger.warning(
                "cancel_queued_wrong_status",
                execution_id=str(execution_id),
                status=queue_entry.status.value
            )
            return False
        
        # Update status to cancelled
        queue_entry.status = QueueStatus.CANCELLED
        queue_entry.completed_at = datetime.utcnow()
        await self.db.commit()
        
        # Remove from Redis
        if self.redis:
            await self.redis.zrem("queue:executions", str(execution_id))
        
        logger.info(
            "execution_cancelled_from_queue",
            execution_id=str(execution_id),
            tool_id=queue_entry.tool_id,
            user_id=queue_entry.user_id
        )
        
        # Note: Queue positions for other executions will be recalculated on next query
        # This is more efficient than updating all positions immediately
        
        return True
    
    async def get_queue_stats(self) -> QueueStats:
        """
        Get overall queue statistics.
        
        Returns:
            QueueStats with counts and averages
        """
        # Count by status
        from sqlalchemy import func
        
        stmt = select(
            ExecutionQueueModel.status,
            func.count(ExecutionQueueModel.id).label('count')
        ).group_by(ExecutionQueueModel.status)
        
        result = await self.db.execute(stmt)
        status_counts = {row.status: row.count for row in result}
        
        # Calculate average wait time for completed executions
        stmt = select(
            func.avg(
                func.timestampdiff(
                    'SECOND',
                    ExecutionQueueModel.queued_at,
                    ExecutionQueueModel.started_at
                )
            )
        ).where(
            and_(
                ExecutionQueueModel.status.in_([QueueStatus.COMPLETED, QueueStatus.PROCESSING]),
                ExecutionQueueModel.started_at.isnot(None)
            )
        )
        
        result = await self.db.execute(stmt)
        avg_wait = result.scalar() or 0.0
        
        return QueueStats(
            total_queued=status_counts.get(QueueStatus.QUEUED, 0),
            total_processing=status_counts.get(QueueStatus.PROCESSING, 0),
            total_completed=status_counts.get(QueueStatus.COMPLETED, 0),
            total_failed=status_counts.get(QueueStatus.FAILED, 0),
            total_cancelled=status_counts.get(QueueStatus.CANCELLED, 0),
            average_wait_time_seconds=float(avg_wait)
        )
    
    async def mark_completed(
        self,
        execution_id: UUID,
        success: bool
    ) -> None:
        """
        Mark an execution as completed or failed.
        
        Args:
            execution_id: ID of the execution
            success: True if successful, False if failed
        """
        stmt = update(ExecutionQueueModel).where(
            ExecutionQueueModel.id == str(execution_id)
        ).values(
            status=QueueStatus.COMPLETED if success else QueueStatus.FAILED,
            completed_at=datetime.utcnow()
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        logger.info(
            "execution_marked_completed",
            execution_id=str(execution_id),
            success=success
        )
    
    async def _get_total_queued(self) -> int:
        """Get total number of queued executions"""
        from sqlalchemy import func
        
        stmt = select(func.count(ExecutionQueueModel.id)).where(
            ExecutionQueueModel.status == QueueStatus.QUEUED
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _get_user_queued_count(self, user_id: UUID) -> int:
        """Get number of queued executions for a specific user"""
        from sqlalchemy import func
        
        stmt = select(func.count(ExecutionQueueModel.id)).where(
            and_(
                ExecutionQueueModel.user_id == str(user_id),
                ExecutionQueueModel.status == QueueStatus.QUEUED
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _calculate_queue_position(
        self,
        execution_id: UUID,
        priority: int
    ) -> int:
        """
        Calculate the current position in queue.
        
        Position is based on:
        1. Higher priority executions
        2. Same priority but older executions
        """
        stmt = select(ExecutionQueueModel).where(
            ExecutionQueueModel.id == str(execution_id)
        )
        result = await self.db.execute(stmt)
        target_entry = result.scalar_one_or_none()
        
        if not target_entry:
            return 0
        
        # Count executions ahead in queue
        stmt = select(func.count(ExecutionQueueModel.id)).where(
            and_(
                ExecutionQueueModel.status == QueueStatus.QUEUED,
                ExecutionQueueModel.id != str(execution_id),
                # Higher priority OR same priority but queued earlier
                (
                    (ExecutionQueueModel.priority > priority) |
                    (
                        (ExecutionQueueModel.priority == priority) &
                        (ExecutionQueueModel.queued_at < target_entry.queued_at)
                    )
                )
            )
        )
        
        result = await self.db.execute(stmt)
        ahead_count = result.scalar() or 0
        
        # Position is 1-indexed
        return ahead_count + 1
    
    def _estimate_wait_time(self, position: int) -> int:
        """
        Estimate wait time based on queue position.
        
        Simple estimation: position * average_execution_time
        """
        return max(0, (position - 1) * self.AVERAGE_EXECUTION_TIME)
