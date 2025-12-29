"""Task Status Tracking Service"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
from redis.asyncio import Redis
import json


class TaskTracker:
    """
    Service for tracking Celery task status in Redis.
    
    Provides:
    - Task status storage and retrieval
    - Task result caching with TTL
    - Task progress tracking
    """
    
    def __init__(self, redis: Redis):
        """
        Initialize TaskTracker with Redis client.
        
        Args:
            redis: Redis async client
        """
        self.redis = redis
        self.status_ttl = 3600  # 1 hour TTL for task status
        self.result_ttl = 3600  # 1 hour TTL for task results
    
    # ========================================================================
    # Task Status Operations
    # ========================================================================
    
    async def set_task_status(
        self,
        task_id: UUID,
        status: str,
        progress: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """
        Set task status in Redis.
        
        Args:
            task_id: Task identifier
            status: Task status (pending, running, completed, failed)
            progress: Optional progress percentage (0-100)
            message: Optional status message
        
        Validates: Requirements 9.4
        """
        key = f"task:{task_id}:status"
        
        status_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
        }
        
        if progress is not None:
            status_data["progress"] = progress
        
        if message is not None:
            status_data["message"] = message
        
        # Store as JSON string
        await self.redis.setex(
            key,
            self.status_ttl,
            json.dumps(status_data)
        )
    
    async def get_task_status(
        self,
        task_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get task status from Redis.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Task status data or None if not found
        
        Validates: Requirements 9.4
        """
        key = f"task:{task_id}:status"
        
        status_json = await self.redis.get(key)
        
        if status_json is None:
            return None
        
        return json.loads(status_json)
    
    async def delete_task_status(self, task_id: UUID) -> bool:
        """
        Delete task status from Redis.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if deleted, False if not found
        """
        key = f"task:{task_id}:status"
        result = await self.redis.delete(key)
        return result > 0
    
    # ========================================================================
    # Task Result Operations
    # ========================================================================
    
    async def set_task_result(
        self,
        task_id: UUID,
        result: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Store task result in Redis with TTL.
        
        Args:
            task_id: Task identifier
            result: Task result (will be JSON serialized)
            ttl: Time-to-live in seconds (default: 1 hour)
        
        Validates: Requirements 9.4
        """
        key = f"task:{task_id}:result"
        ttl = ttl or self.result_ttl
        
        # Serialize result
        if isinstance(result, (dict, list)):
            result_json = json.dumps(result)
        else:
            result_json = json.dumps({"value": str(result)})
        
        await self.redis.setex(key, ttl, result_json)
    
    async def get_task_result(
        self,
        task_id: UUID
    ) -> Optional[Any]:
        """
        Get task result from Redis.
        
        Args:
            task_id: Task identifier
        
        Returns:
            Task result or None if not found
        """
        key = f"task:{task_id}:result"
        
        result_json = await self.redis.get(key)
        
        if result_json is None:
            return None
        
        return json.loads(result_json)
    
    async def delete_task_result(self, task_id: UUID) -> bool:
        """
        Delete task result from Redis.
        
        Args:
            task_id: Task identifier
        
        Returns:
            True if deleted, False if not found
        """
        key = f"task:{task_id}:result"
        result = await self.redis.delete(key)
        return result > 0
    
    # ========================================================================
    # Combined Operations
    # ========================================================================
    
    async def get_task_info(
        self,
        task_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get complete task information (status + result).
        
        Args:
            task_id: Task identifier
        
        Returns:
            Combined task info or None if not found
        """
        status = await self.get_task_status(task_id)
        
        if status is None:
            return None
        
        result = await self.get_task_result(task_id)
        
        return {
            "task_id": str(task_id),
            "status": status.get("status"),
            "progress": status.get("progress"),
            "message": status.get("message"),
            "updated_at": status.get("updated_at"),
            "result": result
        }
    
    async def mark_task_pending(
        self,
        task_id: UUID,
        message: Optional[str] = None
    ) -> None:
        """
        Mark task as pending.
        
        Args:
            task_id: Task identifier
            message: Optional status message
        """
        await self.set_task_status(
            task_id=task_id,
            status="pending",
            progress=0,
            message=message or "Task queued for processing"
        )
    
    async def mark_task_running(
        self,
        task_id: UUID,
        progress: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """
        Mark task as running.
        
        Args:
            task_id: Task identifier
            progress: Optional progress percentage
            message: Optional status message
        """
        await self.set_task_status(
            task_id=task_id,
            status="running",
            progress=progress,
            message=message or "Task is running"
        )
    
    async def mark_task_completed(
        self,
        task_id: UUID,
        result: Any,
        message: Optional[str] = None
    ) -> None:
        """
        Mark task as completed and store result.
        
        Args:
            task_id: Task identifier
            result: Task result
            message: Optional status message
        
        Validates: Requirements 9.4
        """
        await self.set_task_status(
            task_id=task_id,
            status="completed",
            progress=100,
            message=message or "Task completed successfully"
        )
        
        await self.set_task_result(task_id=task_id, result=result)
    
    async def mark_task_failed(
        self,
        task_id: UUID,
        error: str,
        message: Optional[str] = None
    ) -> None:
        """
        Mark task as failed and store error.
        
        Args:
            task_id: Task identifier
            error: Error message
            message: Optional status message
        """
        await self.set_task_status(
            task_id=task_id,
            status="failed",
            message=message or f"Task failed: {error}"
        )
        
        await self.set_task_result(
            task_id=task_id,
            result={"error": error}
        )
