"""Queue Worker Process - Background worker for processing execution queue"""

import asyncio
import signal
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis

from app.services.execution_queue_manager import ExecutionQueueManager, ExecutionRequest
from app.services.mcp_executor import MCPExecutor
from app.services.mcp_manager import MCPManager
from app.core.config import settings
from app.core.logging_config import get_logger
from app.core.exceptions import MCPExecutionError

logger = get_logger(__name__)


class QueueWorker:
    """
    Background worker that processes execution queue.
    
    Responsibilities:
    - Continuously dequeue and execute tasks
    - Handle execution errors with retry logic
    - Implement graceful shutdown
    - Update queue status on completion
    
    **Validates: Requirements 6.2**
    """
    
    def __init__(
        self,
        queue_manager: ExecutionQueueManager,
        executor: MCPExecutor,
        poll_interval: float = 1.0,
        max_retries: int = 3
    ):
        self.queue_manager = queue_manager
        self.executor = executor
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._current_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """
        Start the queue worker.
        
        Runs continuously until shutdown is requested.
        """
        if self._running:
            logger.warning("queue_worker_already_running")
            return
        
        self._running = True
        self._shutdown_event.clear()
        
        logger.info("queue_worker_started", poll_interval=self.poll_interval)
        
        try:
            while self._running and not self._shutdown_event.is_set():
                try:
                    # Dequeue next execution
                    execution_request = await self.queue_manager.dequeue()
                    
                    if execution_request:
                        # Process execution in background
                        self._current_task = asyncio.create_task(
                            self._process_execution(execution_request)
                        )
                        
                        # Wait for completion or shutdown
                        done, pending = await asyncio.wait(
                            [self._current_task, asyncio.create_task(self._shutdown_event.wait())],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # If shutdown was signaled, cancel current task
                        if self._shutdown_event.is_set():
                            if self._current_task and not self._current_task.done():
                                self._current_task.cancel()
                                try:
                                    await self._current_task
                                except asyncio.CancelledError:
                                    logger.info("current_execution_cancelled_on_shutdown")
                            break
                    else:
                        # No executions in queue, wait before polling again
                        try:
                            await asyncio.wait_for(
                                self._shutdown_event.wait(),
                                timeout=self.poll_interval
                            )
                            if self._shutdown_event.is_set():
                                break
                        except asyncio.TimeoutError:
                            # Normal timeout, continue polling
                            pass
                
                except Exception as e:
                    logger.error(
                        "queue_worker_error",
                        error=str(e),
                        exc_info=True
                    )
                    # Wait a bit before retrying to avoid tight error loops
                    await asyncio.sleep(self.poll_interval)
        
        finally:
            self._running = False
            logger.info("queue_worker_stopped")
    
    async def stop(self, timeout: float = 30.0) -> None:
        """
        Stop the queue worker gracefully.
        
        Waits for current execution to complete or timeout.
        
        Args:
            timeout: Maximum time to wait for graceful shutdown (seconds)
        """
        if not self._running:
            logger.warning("queue_worker_not_running")
            return
        
        logger.info("queue_worker_stopping", timeout=timeout)
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Wait for current task to complete
        if self._current_task and not self._current_task.done():
            try:
                await asyncio.wait_for(self._current_task, timeout=timeout)
                logger.info("queue_worker_current_task_completed")
            except asyncio.TimeoutError:
                logger.warning("queue_worker_shutdown_timeout", timeout=timeout)
                self._current_task.cancel()
                try:
                    await self._current_task
                except asyncio.CancelledError:
                    logger.info("queue_worker_current_task_cancelled")
            except Exception as e:
                logger.error(
                    "queue_worker_shutdown_error",
                    error=str(e),
                    exc_info=True
                )
        
        self._running = False
        logger.info("queue_worker_stopped_gracefully")
    
    async def _process_execution(
        self,
        execution_request: ExecutionRequest
    ) -> None:
        """
        Process a single execution request with retry logic.
        
        Args:
            execution_request: The execution request to process
        """
        execution_id = execution_request.execution_id
        retry_count = 0
        last_error = None
        
        logger.info(
            "processing_execution",
            execution_id=str(execution_id),
            tool_id=str(execution_request.tool_id),
            tool_name=execution_request.tool_name,
            user_id=str(execution_request.user_id)
        )
        
        while retry_count <= self.max_retries:
            try:
                # Execute the tool
                result = await self.executor.execute_tool(
                    tool_id=execution_request.tool_id,
                    tool_name=execution_request.tool_name,
                    arguments=execution_request.arguments,
                    user_id=execution_request.user_id,
                    timeout=execution_request.options.timeout
                )
                
                # Mark as completed successfully
                await self.queue_manager.mark_completed(execution_id, success=True)
                
                logger.info(
                    "execution_completed_successfully",
                    execution_id=str(execution_id),
                    tool_name=execution_request.tool_name,
                    retry_count=retry_count
                )
                
                return
            
            except MCPExecutionError as e:
                last_error = e
                retry_count += 1
                
                # Check if error is retryable
                if self._is_retryable_error(e) and retry_count <= self.max_retries:
                    # Calculate exponential backoff
                    backoff_seconds = min(2 ** (retry_count - 1), 60)
                    
                    logger.warning(
                        "execution_failed_retrying",
                        execution_id=str(execution_id),
                        tool_name=execution_request.tool_name,
                        error=str(e),
                        retry_count=retry_count,
                        max_retries=self.max_retries,
                        backoff_seconds=backoff_seconds
                    )
                    
                    # Wait before retrying
                    await asyncio.sleep(backoff_seconds)
                else:
                    # Non-retryable error or max retries exceeded
                    logger.error(
                        "execution_failed_permanently",
                        execution_id=str(execution_id),
                        tool_name=execution_request.tool_name,
                        error=str(e),
                        retry_count=retry_count,
                        retryable=self._is_retryable_error(e),
                        exc_info=True
                    )
                    
                    # Mark as failed
                    await self.queue_manager.mark_completed(execution_id, success=False)
                    return
            
            except Exception as e:
                last_error = e
                retry_count += 1
                
                logger.error(
                    "execution_unexpected_error",
                    execution_id=str(execution_id),
                    tool_name=execution_request.tool_name,
                    error=str(e),
                    retry_count=retry_count,
                    exc_info=True
                )
                
                if retry_count <= self.max_retries:
                    # Retry on unexpected errors
                    backoff_seconds = min(2 ** (retry_count - 1), 60)
                    await asyncio.sleep(backoff_seconds)
                else:
                    # Max retries exceeded
                    await self.queue_manager.mark_completed(execution_id, success=False)
                    return
        
        # If we get here, all retries failed
        logger.error(
            "execution_failed_after_all_retries",
            execution_id=str(execution_id),
            tool_name=execution_request.tool_name,
            retry_count=retry_count,
            last_error=str(last_error)
        )
        
        await self.queue_manager.mark_completed(execution_id, success=False)
    
    def _is_retryable_error(self, error: MCPExecutionError) -> bool:
        """
        Determine if an error is retryable.
        
        Retryable errors:
        - Timeout errors
        - Connection errors
        - Temporary failures
        
        Non-retryable errors:
        - Validation errors
        - Permission errors
        - Tool not found
        """
        error_message = str(error).lower()
        
        # Non-retryable patterns
        non_retryable_patterns = [
            "not found",
            "permission denied",
            "invalid",
            "validation",
            "unauthorized",
            "forbidden"
        ]
        
        for pattern in non_retryable_patterns:
            if pattern in error_message:
                return False
        
        # Retryable patterns
        retryable_patterns = [
            "timeout",
            "connection",
            "temporary",
            "unavailable",
            "overload"
        ]
        
        for pattern in retryable_patterns:
            if pattern in error_message:
                return True
        
        # Default to retryable for unknown errors
        return True


async def create_queue_worker() -> QueueWorker:
    """
    Factory function to create a queue worker with all dependencies.
    
    Returns:
        Configured QueueWorker instance
    """
    # Create database engine and session
    database_url = (
        f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    )
    engine = create_async_engine(database_url, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    # Create MongoDB client
    mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
    mongo_db = mongo_client[settings.MONGODB_DATABASE]
    
    # Create Redis client
    redis_client = None
    if settings.REDIS_HOST:
        redis_client = Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=False
        )
    
    # Create session
    async with async_session_maker() as session:
        # Create dependencies
        mcp_manager = MCPManager(db_session=session)
        executor = MCPExecutor(
            mcp_manager=mcp_manager,
            mongo_db=mongo_db,
            redis_client=redis_client
        )
        queue_manager = ExecutionQueueManager(
            db_session=session,
            redis_client=redis_client
        )
        
        # Create worker
        worker = QueueWorker(
            queue_manager=queue_manager,
            executor=executor,
            poll_interval=1.0,
            max_retries=3
        )
        
        return worker


async def run_queue_worker():
    """
    Main entry point for running the queue worker as a standalone process.
    
    Handles graceful shutdown on SIGTERM and SIGINT.
    """
    logger.info("queue_worker_process_starting")
    
    # Create worker
    worker = await create_queue_worker()
    
    # Setup signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig, frame):
        logger.info("shutdown_signal_received", signal=sig)
        shutdown_event.set()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start worker
    worker_task = asyncio.create_task(worker.start())
    
    # Wait for shutdown signal
    await shutdown_event.wait()
    
    # Stop worker gracefully
    await worker.stop(timeout=30.0)
    
    # Wait for worker task to complete
    try:
        await asyncio.wait_for(worker_task, timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("worker_task_did_not_complete_in_time")
        worker_task.cancel()
    
    logger.info("queue_worker_process_stopped")


if __name__ == "__main__":
    # Run the worker
    asyncio.run(run_queue_worker())
