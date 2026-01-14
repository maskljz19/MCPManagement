"""Schedules API Endpoints"""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_current_user, require_permission
from app.core.database import get_db
from app.models.user import UserModel
from app.schemas.schedule import (
    ScheduleCreateRequest,
    ScheduleResponse,
    ScheduleListResponse,
    ScheduleDeleteResponse
)
from app.services.execution_scheduler import ExecutionScheduler
from app.core.exceptions import MCPExecutionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/schedule", tags=["schedules"])


@router.post(
    "",
    response_model=ScheduleResponse,
    status_code=status.HTTP_201_CREATED
)
@require_permission("mcps", "execute")
async def create_schedule(
    request: ScheduleCreateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new scheduled execution.
    
    Schedule a tool to be executed automatically at specified times using cron expressions.
    
    **Cron Expression Format:**
    - Minute (0-59)
    - Hour (0-23)
    - Day of month (1-31)
    - Month (1-12)
    - Day of week (0-6, Sunday=0)
    
    **Examples:**
    - `0 0 * * *` - Daily at midnight
    - `*/5 * * * *` - Every 5 minutes
    - `0 9 * * 1-5` - Weekdays at 9 AM
    - `0 0 1 * *` - First day of every month at midnight
    
    **Requirements: 20.1, 20.4**
    """
    try:
        scheduler = ExecutionScheduler(db)
        
        schedule_info = await scheduler.create_schedule(
            tool_id=request.tool_id,
            user_id=UUID(current_user.id),
            tool_name=request.tool_name,
            arguments=request.arguments,
            schedule_expression=request.schedule_expression
        )
        
        logger.info(
            "schedule_created_via_api",
            schedule_id=str(schedule_info.schedule_id),
            user_id=current_user.id,
            tool_id=str(request.tool_id),
            schedule_expression=request.schedule_expression
        )
        
        return ScheduleResponse(
            schedule_id=schedule_info.schedule_id,
            tool_id=schedule_info.tool_id,
            user_id=schedule_info.user_id,
            tool_name=schedule_info.tool_name,
            arguments=schedule_info.arguments,
            schedule_expression=schedule_info.schedule_expression,
            next_execution_at=schedule_info.next_execution_at,
            last_execution_at=schedule_info.last_execution_at,
            last_execution_status=schedule_info.last_execution_status,
            is_active=schedule_info.is_active,
            created_at=schedule_info.created_at
        )
        
    except MCPExecutionError as e:
        logger.error(
            "failed_to_create_schedule",
            user_id=current_user.id,
            tool_id=str(request.tool_id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "unexpected_error_creating_schedule",
            user_id=current_user.id,
            tool_id=str(request.tool_id),
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create schedule"
        )


@router.get(
    "",
    response_model=ScheduleListResponse
)
@require_permission("mcps", "read")
async def list_schedules(
    tool_id: Optional[UUID] = None,
    is_active: Optional[bool] = None,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List scheduled executions for the current user.
    
    Returns all schedules created by the current user, with optional filters.
    
    **Query Parameters:**
    - `tool_id`: Filter by specific tool ID
    - `is_active`: Filter by active status (true/false)
    
    **Requirements: 20.4**
    """
    try:
        scheduler = ExecutionScheduler(db)
        
        schedules = await scheduler.list_schedules(
            user_id=UUID(current_user.id),
            tool_id=tool_id,
            is_active=is_active
        )
        
        logger.info(
            "schedules_listed",
            user_id=current_user.id,
            count=len(schedules),
            tool_id=str(tool_id) if tool_id else None,
            is_active=is_active
        )
        
        return ScheduleListResponse(
            schedules=[
                ScheduleResponse(
                    schedule_id=s.schedule_id,
                    tool_id=s.tool_id,
                    user_id=s.user_id,
                    tool_name=s.tool_name,
                    arguments=s.arguments,
                    schedule_expression=s.schedule_expression,
                    next_execution_at=s.next_execution_at,
                    last_execution_at=s.last_execution_at,
                    last_execution_status=s.last_execution_status,
                    is_active=s.is_active,
                    created_at=s.created_at
                )
                for s in schedules
            ],
            total=len(schedules)
        )
        
    except Exception as e:
        logger.error(
            "unexpected_error_listing_schedules",
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list schedules"
        )


@router.get(
    "/{schedule_id}",
    response_model=ScheduleResponse
)
@require_permission("mcps", "read")
async def get_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific scheduled execution by ID.
    
    Returns details of a single schedule. Users can only access their own schedules.
    
    **Requirements: 20.4**
    """
    try:
        scheduler = ExecutionScheduler(db)
        
        schedule_info = await scheduler.get_schedule(schedule_id)
        
        if not schedule_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found"
            )
        
        # Verify user owns this schedule
        if str(schedule_info.user_id) != current_user.id:
            logger.warning(
                "unauthorized_schedule_access",
                schedule_id=str(schedule_id),
                user_id=current_user.id,
                owner_id=str(schedule_info.user_id)
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this schedule"
            )
        
        logger.info(
            "schedule_retrieved",
            schedule_id=str(schedule_id),
            user_id=current_user.id
        )
        
        return ScheduleResponse(
            schedule_id=schedule_info.schedule_id,
            tool_id=schedule_info.tool_id,
            user_id=schedule_info.user_id,
            tool_name=schedule_info.tool_name,
            arguments=schedule_info.arguments,
            schedule_expression=schedule_info.schedule_expression,
            next_execution_at=schedule_info.next_execution_at,
            last_execution_at=schedule_info.last_execution_at,
            last_execution_status=schedule_info.last_execution_status,
            is_active=schedule_info.is_active,
            created_at=schedule_info.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "unexpected_error_getting_schedule",
            schedule_id=str(schedule_id),
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get schedule"
        )


@router.delete(
    "/{schedule_id}",
    response_model=ScheduleDeleteResponse
)
@require_permission("mcps", "execute")
async def delete_schedule(
    schedule_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete (cancel) a scheduled execution.
    
    Removes a schedule so it will no longer execute. Users can only delete their own schedules.
    
    **Requirements: 20.5**
    """
    try:
        scheduler = ExecutionScheduler(db)
        
        success = await scheduler.delete_schedule(
            schedule_id=schedule_id,
            user_id=UUID(current_user.id)
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found or you do not have permission to delete it"
            )
        
        logger.info(
            "schedule_deleted_via_api",
            schedule_id=str(schedule_id),
            user_id=current_user.id
        )
        
        return ScheduleDeleteResponse(
            success=True,
            message=f"Schedule {schedule_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "unexpected_error_deleting_schedule",
            schedule_id=str(schedule_id),
            user_id=current_user.id,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete schedule"
        )
