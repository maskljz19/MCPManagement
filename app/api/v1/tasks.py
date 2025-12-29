"""Task Status API Endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import Dict, Any, Optional

from app.core.database import get_redis
from app.services.task_tracker import TaskTracker
from redis.asyncio import Redis


router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_tracker(redis: Redis = Depends(get_redis)) -> TaskTracker:
    """Dependency injection for TaskTracker"""
    return TaskTracker(redis=redis)


@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_status(
    task_id: UUID,
    tracker: TaskTracker = Depends(get_task_tracker)
) -> Dict[str, Any]:
    """
    Get task status and result.
    
    Returns task information including:
    - status: pending, running, completed, or failed
    - progress: percentage (0-100) if available
    - message: status message
    - result: task result if completed
    - updated_at: last update timestamp
    
    Args:
        task_id: Task identifier
    
    Returns:
        Task information dictionary
    
    Raises:
        404: Task not found
    
    Validates: Requirements 9.4
    """
    task_info = await tracker.get_task_info(task_id)
    
    if task_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found or expired"
        )
    
    return task_info


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: UUID,
    tracker: TaskTracker = Depends(get_task_tracker)
) -> None:
    """
    Delete task status and result from cache.
    
    Useful for cleanup after retrieving results.
    
    Args:
        task_id: Task identifier
    
    Returns:
        204 No Content on success
    
    Raises:
        404: Task not found
    """
    status_deleted = await tracker.delete_task_status(task_id)
    result_deleted = await tracker.delete_task_result(task_id)
    
    if not status_deleted and not result_deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
