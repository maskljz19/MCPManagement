"""Queue Management API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from uuid import UUID
from typing import Optional, List

from app.core.database import get_db, get_redis
from app.services.execution_queue_manager import ExecutionQueueManager
from app.models.user import UserModel
from app.models.execution_queue import QueueStatus
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission
from app.core.exceptions import MCPExecutionError
from pydantic import BaseModel, Field


router = APIRouter(prefix="/executions", tags=["Queue Management"])


class QueuedExecutionSchema(BaseModel):
    """Schema for a queued execution"""
    execution_id: str = Field(..., description="Unique execution ID")
    tool_id: str = Field(..., description="ID of the tool to execute")
    user_id: str = Field(..., description="ID of the user who queued the execution")
    tool_name: str = Field(..., description="Name of the tool")
    status: str = Field(..., description="Queue status: queued, processing, completed, failed, cancelled")
    priority: int = Field(..., description="Execution priority (1-15)")
    queue_position: Optional[int] = Field(None, description="Current position in queue (1-indexed)")
    estimated_wait_seconds: Optional[int] = Field(None, description="Estimated wait time in seconds")
    queued_at: str = Field(..., description="When the execution was queued (ISO format)")


class QueueListResponse(BaseModel):
    """Schema for queue list response"""
    total: int = Field(..., description="Total number of executions matching filters")
    queued: int = Field(..., description="Number of queued executions")
    processing: int = Field(..., description="Number of processing executions")
    executions: List[QueuedExecutionSchema] = Field(
        ...,
        description="List of queued/processing executions"
    )


class QueuePositionResponse(BaseModel):
    """Schema for queue position response"""
    execution_id: str = Field(..., description="Unique execution ID")
    position: int = Field(..., description="Current position in queue (1-indexed)")
    estimated_wait_seconds: int = Field(..., description="Estimated wait time in seconds")
    total_queued: int = Field(..., description="Total number of queued executions")
    message: str = Field(
        default="Queue position retrieved successfully",
        description="Status message"
    )


async def get_queue_manager(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> ExecutionQueueManager:
    """Dependency to get ExecutionQueueManager instance"""
    return ExecutionQueueManager(db_session=db, redis_client=redis)


@router.get("/queue", response_model=QueueListResponse)
@require_permission("mcps", "read")
async def get_queue(
    status_filter: Optional[str] = Query(
        None,
        description="Filter by status: queued, processing, completed, failed, cancelled"
    ),
    user_filter: Optional[UUID] = Query(
        None,
        description="Filter by user ID (admins only)"
    ),
    limit: int = Query(
        50,
        ge=1,
        le=200,
        description="Maximum number of results to return (1-200)"
    ),
    offset: int = Query(
        0,
        ge=0,
        description="Number of results to skip for pagination"
    ),
    current_user: UserModel = Depends(get_current_user),
    queue_manager: ExecutionQueueManager = Depends(get_queue_manager)
):
    """
    Get list of queued and processing executions.
    
    Returns a list of executions currently in the queue or being processed.
    Users can see their own executions, while admins can see all executions
    and filter by user.
    
    Features:
    - Filter by status (queued, processing, completed, failed, cancelled)
    - Filter by user (admin only)
    - Pagination support
    - Queue position and estimated wait time for queued executions
    
    Args:
        status_filter: Optional status filter
        user_filter: Optional user ID filter (admin only)
        limit: Maximum number of results (1-200)
        offset: Number of results to skip
        current_user: Currently authenticated user
        queue_manager: Queue manager service
        
    Returns:
        List of queued/processing executions with metadata
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission or tries to filter by other users
        HTTPException 422: If invalid status filter provided
        
    Example:
        ```
        GET /api/v1/executions/queue?status_filter=queued&limit=20
        ```
        
    **Validates: Requirements 6.3**
    """
    try:
        from sqlalchemy import select, and_, func
        from app.models.execution_queue import ExecutionQueueModel
        
        # Build query
        conditions = []
        
        # Status filter
        if status_filter:
            try:
                status_enum = QueueStatus(status_filter)
                conditions.append(ExecutionQueueModel.status == status_enum)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Invalid status filter: {status_filter}. Must be one of: queued, processing, completed, failed, cancelled"
                )
        else:
            # Default: show queued and processing only
            conditions.append(
                ExecutionQueueModel.status.in_([QueueStatus.QUEUED, QueueStatus.PROCESSING])
            )
        
        # User filter
        if user_filter:
            # Only admins can filter by other users
            from app.models.user import UserRole
            if current_user.role != UserRole.ADMIN and user_filter != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only admins can view other users' queue entries"
                )
            conditions.append(ExecutionQueueModel.user_id == str(user_filter))
        else:
            # Non-admins can only see their own executions
            from app.models.user import UserRole
            if current_user.role != UserRole.ADMIN:
                conditions.append(ExecutionQueueModel.user_id == str(current_user.id))
        
        # Get total count
        count_stmt = select(func.count(ExecutionQueueModel.id)).where(and_(*conditions))
        count_result = await queue_manager.db.execute(count_stmt)
        total = count_result.scalar() or 0
        
        # Get executions
        stmt = select(ExecutionQueueModel).where(
            and_(*conditions)
        ).order_by(
            ExecutionQueueModel.priority.desc(),
            ExecutionQueueModel.queued_at.asc()
        ).limit(limit).offset(offset)
        
        result = await queue_manager.db.execute(stmt)
        executions = result.scalars().all()
        
        # Count by status for summary
        queued_count = 0
        processing_count = 0
        
        # Convert to response schema
        execution_schemas = []
        for execution in executions:
            if execution.status == QueueStatus.QUEUED:
                queued_count += 1
            elif execution.status == QueueStatus.PROCESSING:
                processing_count += 1
            
            execution_schemas.append(
                QueuedExecutionSchema(
                    execution_id=execution.id,
                    tool_id=execution.tool_id,
                    user_id=execution.user_id,
                    tool_name=execution.tool_name,
                    status=execution.status.value,
                    priority=execution.priority,
                    queue_position=execution.queue_position,
                    estimated_wait_seconds=execution.estimated_wait_seconds,
                    queued_at=execution.queued_at.isoformat()
                )
            )
        
        return QueueListResponse(
            total=total,
            queued=queued_count,
            processing=processing_count,
            executions=execution_schemas
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving queue: {str(e)}"
        )


@router.get("/queue/position", response_model=QueuePositionResponse)
@require_permission("mcps", "read")
async def get_queue_position(
    execution_id: UUID = Query(..., description="Execution ID to query"),
    current_user: UserModel = Depends(get_current_user),
    queue_manager: ExecutionQueueManager = Depends(get_queue_manager)
):
    """
    Get the current queue position for a specific execution.
    
    Returns the current position in the queue, estimated wait time, and total
    number of queued executions. This endpoint can be polled to track queue
    progress for long-running operations.
    
    The position is calculated based on:
    - Execution priority (higher priority = earlier position)
    - Queue time (older executions = earlier position within same priority)
    
    Args:
        execution_id: ID of the execution to query
        current_user: Currently authenticated user
        queue_manager: Queue manager service
        
    Returns:
        Queue position information with estimated wait time
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission or doesn't own execution
        HTTPException 404: If execution not found in queue
        HTTPException 400: If execution is not in queued status
        
    Example:
        ```
        GET /api/v1/executions/queue/position?execution_id=uuid-here
        ```
        
    **Validates: Requirements 6.3**
    """
    try:
        # Verify user owns this execution (unless admin)
        from sqlalchemy import select
        from app.models.execution_queue import ExecutionQueueModel
        from app.models.user import UserRole
        
        stmt = select(ExecutionQueueModel).where(
            ExecutionQueueModel.id == str(execution_id)
        )
        result = await queue_manager.db.execute(stmt)
        execution = result.scalar_one_or_none()
        
        if not execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution {execution_id} not found in queue"
            )
        
        # Check ownership
        if current_user.role != UserRole.ADMIN and execution.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view queue position for your own executions"
            )
        
        # Get queue position
        queue_position = await queue_manager.get_queue_position(execution_id)
        
        return QueuePositionResponse(
            execution_id=str(queue_position.execution_id),
            position=queue_position.position,
            estimated_wait_seconds=queue_position.estimated_wait_seconds,
            total_queued=queue_position.total_queued,
            message="Queue position retrieved successfully"
        )
        
    except HTTPException:
        raise
    except MCPExecutionError as e:
        # Check if it's a not found error
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        # Check if it's a status error
        elif "not queued" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving queue position: {str(e)}"
        )
