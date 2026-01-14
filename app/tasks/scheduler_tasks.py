"""Celery tasks for scheduled execution management"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from app.core.celery_app import celery_app
from app.core.database import async_session_factory, init_mysql
from app.core.logging_config import get_logger
from app.services.execution_scheduler import ExecutionScheduler
from app.services.execution_queue_manager import ExecutionQueueManager

logger = get_logger(__name__)


@celery_app.task(name="scheduler.check_and_trigger_due_schedules")
def check_and_trigger_due_schedules():
    """
    Celery task to check for due scheduled executions and trigger them.
    
    This task should be run periodically (e.g., every minute) via Celery Beat.
    
    **Validates: Requirements 20.2, 20.3**
    """
    asyncio.run(_check_and_trigger_due_schedules_async())


async def _check_and_trigger_due_schedules_async():
    """
    Async implementation of scheduled execution checking and triggering.
    """
    # Ensure database is initialized
    if async_session_factory is None:
        await init_mysql()
    
    async with async_session_factory() as db_session:
        try:
            scheduler = ExecutionScheduler(db_session)
            queue_manager = ExecutionQueueManager(db_session)
            
            # Get due schedules
            due_schedules = await scheduler.get_due_schedules(limit=100)
            
            if not due_schedules:
                logger.debug("no_due_schedules_found")
                return
            
            logger.info(
                "processing_due_schedules",
                count=len(due_schedules)
            )
            
            # Trigger each due schedule
            for schedule_info in due_schedules:
                try:
                    # Default retry policy for scheduled executions
                    retry_policy = {
                        "max_attempts": 3,
                        "initial_delay_seconds": 1.0,
                        "max_delay_seconds": 60.0,
                        "backoff_multiplier": 2.0,
                        "retryable_errors": [
                            "timeout",
                            "connection_error",
                            "temporary_failure"
                        ]
                    }
                    
                    # Trigger the execution
                    execution_id = await scheduler.trigger_scheduled_execution(
                        schedule_info,
                        queue_manager,
                        retry_policy
                    )
                    
                    # Update schedule with success status
                    await scheduler.update_schedule_after_execution(
                        schedule_info.schedule_id,
                        "queued"
                    )
                    
                    logger.info(
                        "scheduled_execution_triggered_successfully",
                        schedule_id=str(schedule_info.schedule_id),
                        execution_id=str(execution_id),
                        tool_name=schedule_info.tool_name
                    )
                    
                except Exception as e:
                    logger.error(
                        "failed_to_trigger_scheduled_execution",
                        schedule_id=str(schedule_info.schedule_id),
                        tool_name=schedule_info.tool_name,
                        error=str(e),
                        exc_info=True
                    )
                    
                    # Update schedule with failed status
                    await scheduler.update_schedule_after_execution(
                        schedule_info.schedule_id,
                        "failed"
                    )
            
            logger.info(
                "completed_processing_due_schedules",
                processed_count=len(due_schedules)
            )
            
        except Exception as e:
            logger.error(
                "error_in_scheduled_execution_task",
                error=str(e),
                exc_info=True
            )
            raise


@celery_app.task(name="scheduler.cleanup_old_schedules")
def cleanup_old_schedules():
    """
    Celery task to clean up old inactive schedules.
    
    This task should be run periodically (e.g., daily) via Celery Beat.
    Removes schedules that have been inactive for more than 90 days.
    """
    asyncio.run(_cleanup_old_schedules_async())


async def _cleanup_old_schedules_async():
    """
    Async implementation of old schedule cleanup.
    """
    from datetime import timedelta
    from sqlalchemy import and_, delete
    from app.models.scheduled_execution import ScheduledExecutionModel
    
    # Ensure database is initialized
    if async_session_factory is None:
        await init_mysql()
    
    async with async_session_factory() as db_session:
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=90)
            
            # Delete inactive schedules older than 90 days
            stmt = delete(ScheduledExecutionModel).where(
                and_(
                    ScheduledExecutionModel.is_active == False,
                    ScheduledExecutionModel.created_at < cutoff_date
                )
            )
            
            result = await db_session.execute(stmt)
            await db_session.commit()
            
            deleted_count = result.rowcount
            
            logger.info(
                "cleaned_up_old_schedules",
                deleted_count=deleted_count,
                cutoff_date=cutoff_date.isoformat()
            )
            
        except Exception as e:
            logger.error(
                "error_in_cleanup_old_schedules",
                error=str(e),
                exc_info=True
            )
            raise
