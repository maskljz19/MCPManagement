"""Execution Scheduler Service - Manages scheduled MCP tool executions"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
from croniter import croniter

from app.models.scheduled_execution import ScheduledExecutionModel
from app.models.user import UserModel, UserRole
from app.schemas.mcp_execution import ExecutionOptions
from app.core.exceptions import MCPExecutionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ScheduleInfo:
    """Schedule information"""
    def __init__(
        self,
        schedule_id: UUID,
        tool_id: UUID,
        user_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        schedule_expression: str,
        next_execution_at: datetime,
        last_execution_at: Optional[datetime],
        last_execution_status: Optional[str],
        is_active: bool,
        created_at: datetime
    ):
        self.schedule_id = schedule_id
        self.tool_id = tool_id
        self.user_id = user_id
        self.tool_name = tool_name
        self.arguments = arguments
        self.schedule_expression = schedule_expression
        self.next_execution_at = next_execution_at
        self.last_execution_at = last_execution_at
        self.last_execution_status = last_execution_status
        self.is_active = is_active
        self.created_at = created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "schedule_id": str(self.schedule_id),
            "tool_id": str(self.tool_id),
            "user_id": str(self.user_id),
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "schedule_expression": self.schedule_expression,
            "next_execution_at": self.next_execution_at.isoformat(),
            "last_execution_at": self.last_execution_at.isoformat() if self.last_execution_at else None,
            "last_execution_status": self.last_execution_status,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat()
        }


class ExecutionScheduler:
    """
    Manages scheduled executions of MCP tools using cron-like expressions.
    
    Responsibilities:
    - Validate cron schedule expressions
    - Create, list, and delete scheduled executions
    - Trigger scheduled executions at the appropriate time
    - Integrate with retry mechanism for failed scheduled executions
    - Calculate next execution times
    
    **Validates: Requirements 20.1, 20.2, 20.3, 20.4, 20.5**
    """
    
    def __init__(
        self,
        db_session: AsyncSession
    ):
        self.db = db_session
    
    @staticmethod
    def validate_schedule_expression(expression: str) -> bool:
        """
        Validate a cron schedule expression.
        
        Supports standard cron format:
        - Minute (0-59)
        - Hour (0-23)
        - Day of month (1-31)
        - Month (1-12)
        - Day of week (0-6, Sunday=0)
        
        Examples:
        - "0 0 * * *" - Daily at midnight
        - "*/5 * * * *" - Every 5 minutes
        - "0 9 * * 1-5" - Weekdays at 9 AM
        
        Args:
            expression: Cron expression to validate
            
        Returns:
            True if valid, False otherwise
            
        **Validates: Requirements 20.1**
        """
        try:
            # Try to create a croniter instance
            croniter(expression)
            return True
        except (ValueError, KeyError) as e:
            logger.debug(
                "invalid_cron_expression",
                expression=expression,
                error=str(e)
            )
            return False
    
    @staticmethod
    def calculate_next_execution(
        expression: str,
        base_time: Optional[datetime] = None
    ) -> datetime:
        """
        Calculate the next execution time based on cron expression.
        
        Args:
            expression: Cron expression
            base_time: Base time to calculate from (defaults to now)
            
        Returns:
            Next execution datetime
            
        Raises:
            ValueError: If expression is invalid
        """
        if base_time is None:
            base_time = datetime.utcnow()
        
        try:
            cron = croniter(expression, base_time)
            next_time = cron.get_next(datetime)
            return next_time
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression: {expression}") from e
    
    async def create_schedule(
        self,
        tool_id: UUID,
        user_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        schedule_expression: str
    ) -> ScheduleInfo:
        """
        Create a new scheduled execution.
        
        Args:
            tool_id: ID of the tool to execute
            user_id: ID of the user creating the schedule
            tool_name: Name of the tool
            arguments: Arguments to pass to the tool
            schedule_expression: Cron expression for scheduling
            
        Returns:
            ScheduleInfo with schedule details
            
        Raises:
            MCPExecutionError: If schedule expression is invalid
            
        **Validates: Requirements 20.1, 20.4**
        """
        # Validate schedule expression
        if not self.validate_schedule_expression(schedule_expression):
            raise MCPExecutionError(
                f"Invalid schedule expression: {schedule_expression}. "
                "Must be a valid cron expression (e.g., '0 0 * * *' for daily at midnight)."
            )
        
        # Calculate next execution time
        next_execution_at = self.calculate_next_execution(schedule_expression)
        
        # Create schedule entry
        schedule_id = uuid4()
        created_at = datetime.utcnow()
        
        schedule_entry = ScheduledExecutionModel(
            id=str(schedule_id),
            tool_id=str(tool_id),
            user_id=str(user_id),
            tool_name=tool_name,
            arguments=arguments,
            schedule_expression=schedule_expression,
            next_execution_at=next_execution_at,
            is_active=True,
            created_at=created_at
        )
        
        self.db.add(schedule_entry)
        await self.db.commit()
        await self.db.refresh(schedule_entry)
        
        logger.info(
            "schedule_created",
            schedule_id=str(schedule_id),
            tool_id=str(tool_id),
            user_id=str(user_id),
            schedule_expression=schedule_expression,
            next_execution_at=next_execution_at.isoformat()
        )
        
        return ScheduleInfo(
            schedule_id=schedule_id,
            tool_id=tool_id,
            user_id=user_id,
            tool_name=tool_name,
            arguments=arguments,
            schedule_expression=schedule_expression,
            next_execution_at=next_execution_at,
            last_execution_at=None,
            last_execution_status=None,
            is_active=True,
            created_at=created_at
        )
    
    async def list_schedules(
        self,
        user_id: Optional[UUID] = None,
        tool_id: Optional[UUID] = None,
        is_active: Optional[bool] = None
    ) -> List[ScheduleInfo]:
        """
        List scheduled executions with optional filters.
        
        Args:
            user_id: Filter by user ID (optional)
            tool_id: Filter by tool ID (optional)
            is_active: Filter by active status (optional)
            
        Returns:
            List of ScheduleInfo objects
            
        **Validates: Requirements 20.4**
        """
        # Build query with filters
        conditions = []
        
        if user_id is not None:
            conditions.append(ScheduledExecutionModel.user_id == str(user_id))
        
        if tool_id is not None:
            conditions.append(ScheduledExecutionModel.tool_id == str(tool_id))
        
        if is_active is not None:
            conditions.append(ScheduledExecutionModel.is_active == is_active)
        
        stmt = select(ScheduledExecutionModel)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.order_by(ScheduledExecutionModel.next_execution_at.asc())
        
        result = await self.db.execute(stmt)
        schedules = result.scalars().all()
        
        return [
            ScheduleInfo(
                schedule_id=UUID(s.id),
                tool_id=UUID(s.tool_id),
                user_id=UUID(s.user_id),
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
        ]
    
    async def get_schedule(
        self,
        schedule_id: UUID
    ) -> Optional[ScheduleInfo]:
        """
        Get a specific scheduled execution by ID.
        
        Args:
            schedule_id: ID of the schedule
            
        Returns:
            ScheduleInfo if found, None otherwise
            
        **Validates: Requirements 20.4**
        """
        stmt = select(ScheduledExecutionModel).where(
            ScheduledExecutionModel.id == str(schedule_id)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return None
        
        return ScheduleInfo(
            schedule_id=UUID(schedule.id),
            tool_id=UUID(schedule.tool_id),
            user_id=UUID(schedule.user_id),
            tool_name=schedule.tool_name,
            arguments=schedule.arguments,
            schedule_expression=schedule.schedule_expression,
            next_execution_at=schedule.next_execution_at,
            last_execution_at=schedule.last_execution_at,
            last_execution_status=schedule.last_execution_status,
            is_active=schedule.is_active,
            created_at=schedule.created_at
        )
    
    async def delete_schedule(
        self,
        schedule_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Delete (cancel) a scheduled execution.
        
        Args:
            schedule_id: ID of the schedule to delete
            user_id: ID of the user requesting deletion (for authorization)
            
        Returns:
            True if deleted, False if not found or unauthorized
            
        **Validates: Requirements 20.5**
        """
        # Get schedule to verify ownership
        stmt = select(ScheduledExecutionModel).where(
            ScheduledExecutionModel.id == str(schedule_id)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            logger.warning(
                "delete_schedule_not_found",
                schedule_id=str(schedule_id)
            )
            return False
        
        # Verify user owns this schedule
        if schedule.user_id != str(user_id):
            logger.warning(
                "delete_schedule_unauthorized",
                schedule_id=str(schedule_id),
                user_id=str(user_id),
                owner_id=schedule.user_id
            )
            return False
        
        # Delete the schedule
        await self.db.delete(schedule)
        await self.db.commit()
        
        logger.info(
            "schedule_deleted",
            schedule_id=str(schedule_id),
            tool_id=schedule.tool_id,
            user_id=str(user_id)
        )
        
        return True
    
    async def deactivate_schedule(
        self,
        schedule_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Deactivate a scheduled execution without deleting it.
        
        Args:
            schedule_id: ID of the schedule to deactivate
            user_id: ID of the user requesting deactivation
            
        Returns:
            True if deactivated, False if not found or unauthorized
        """
        stmt = select(ScheduledExecutionModel).where(
            ScheduledExecutionModel.id == str(schedule_id)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            return False
        
        if schedule.user_id != str(user_id):
            return False
        
        schedule.is_active = False
        await self.db.commit()
        
        logger.info(
            "schedule_deactivated",
            schedule_id=str(schedule_id),
            user_id=str(user_id)
        )
        
        return True
    
    async def get_due_schedules(
        self,
        limit: int = 100
    ) -> List[ScheduleInfo]:
        """
        Get schedules that are due for execution.
        
        Args:
            limit: Maximum number of schedules to return
            
        Returns:
            List of ScheduleInfo objects that are due
            
        **Validates: Requirements 20.2**
        """
        now = datetime.utcnow()
        
        stmt = select(ScheduledExecutionModel).where(
            and_(
                ScheduledExecutionModel.is_active == True,
                ScheduledExecutionModel.next_execution_at <= now
            )
        ).order_by(
            ScheduledExecutionModel.next_execution_at.asc()
        ).limit(limit)
        
        result = await self.db.execute(stmt)
        schedules = result.scalars().all()
        
        return [
            ScheduleInfo(
                schedule_id=UUID(s.id),
                tool_id=UUID(s.tool_id),
                user_id=UUID(s.user_id),
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
        ]
    
    async def update_schedule_after_execution(
        self,
        schedule_id: UUID,
        execution_status: str
    ) -> None:
        """
        Update schedule after an execution completes.
        
        Calculates the next execution time and updates the schedule.
        
        Args:
            schedule_id: ID of the schedule
            execution_status: Status of the completed execution
            
        **Validates: Requirements 20.2**
        """
        stmt = select(ScheduledExecutionModel).where(
            ScheduledExecutionModel.id == str(schedule_id)
        )
        result = await self.db.execute(stmt)
        schedule = result.scalar_one_or_none()
        
        if not schedule:
            logger.warning(
                "update_schedule_not_found",
                schedule_id=str(schedule_id)
            )
            return
        
        # Calculate next execution time
        try:
            next_execution_at = self.calculate_next_execution(
                schedule.schedule_expression,
                datetime.utcnow()
            )
        except ValueError as e:
            logger.error(
                "failed_to_calculate_next_execution",
                schedule_id=str(schedule_id),
                expression=schedule.schedule_expression,
                error=str(e)
            )
            # Deactivate schedule if expression is invalid
            schedule.is_active = False
            await self.db.commit()
            return
        
        # Update schedule
        schedule.last_execution_at = datetime.utcnow()
        schedule.last_execution_status = execution_status
        schedule.next_execution_at = next_execution_at
        
        await self.db.commit()
        
        logger.info(
            "schedule_updated_after_execution",
            schedule_id=str(schedule_id),
            execution_status=execution_status,
            next_execution_at=next_execution_at.isoformat()
        )
    
    async def trigger_scheduled_execution(
        self,
        schedule_info: ScheduleInfo,
        execution_queue_manager,
        retry_policy: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Trigger a scheduled execution by enqueueing it.
        
        Args:
            schedule_info: Schedule information
            execution_queue_manager: Queue manager to enqueue the execution
            retry_policy: Optional retry policy for the execution
            
        Returns:
            Execution ID of the triggered execution
            
        **Validates: Requirements 20.2, 20.3**
        """
        from app.services.execution_queue_manager import ExecutionRequest
        
        # Create execution options with retry policy
        execution_options = ExecutionOptions(
            mode="async",
            priority=5,  # Default priority for scheduled executions
            retry_policy=retry_policy
        )
        
        # Create execution request
        execution_id = uuid4()
        execution_request = ExecutionRequest(
            execution_id=execution_id,
            tool_id=schedule_info.tool_id,
            user_id=schedule_info.user_id,
            tool_name=schedule_info.tool_name,
            arguments=schedule_info.arguments,
            options=execution_options,
            priority=5
        )
        
        # Get user role for queue management
        stmt = select(UserModel).where(UserModel.id == str(schedule_info.user_id))
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            logger.error(
                "scheduled_execution_user_not_found",
                schedule_id=str(schedule_info.schedule_id),
                user_id=str(schedule_info.user_id)
            )
            raise MCPExecutionError(f"User {schedule_info.user_id} not found")
        
        # Enqueue the execution
        try:
            queued_execution = await execution_queue_manager.enqueue(
                execution_request,
                user.role
            )
            
            logger.info(
                "scheduled_execution_triggered",
                schedule_id=str(schedule_info.schedule_id),
                execution_id=str(execution_id),
                tool_id=str(schedule_info.tool_id),
                user_id=str(schedule_info.user_id)
            )
            
            return execution_id
            
        except MCPExecutionError as e:
            logger.error(
                "failed_to_trigger_scheduled_execution",
                schedule_id=str(schedule_info.schedule_id),
                error=str(e)
            )
            # Update schedule with failed status
            await self.update_schedule_after_execution(
                schedule_info.schedule_id,
                "failed_to_queue"
            )
            raise
