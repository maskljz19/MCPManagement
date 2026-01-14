"""Batch Executor Service - Handles parallel execution of multiple MCP tools"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.models.batch_execution import BatchExecutionModel, BatchStatus
from app.services.mcp_executor import MCPExecutor
from app.schemas.mcp_execution import ExecutionOptions
from app.core.exceptions import MCPExecutionError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ToolExecutionConfig:
    """Configuration for a single tool execution within a batch"""
    def __init__(
        self,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any]
    ):
        self.tool_id = tool_id
        self.tool_name = tool_name
        self.arguments = arguments


class BatchExecutionRequest:
    """Request for batch execution"""
    def __init__(
        self,
        tools: List[ToolExecutionConfig],
        concurrency_limit: int = 5,
        stop_on_error: bool = False,
        execution_options: Optional[ExecutionOptions] = None
    ):
        self.tools = tools
        self.concurrency_limit = concurrency_limit
        self.stop_on_error = stop_on_error
        self.execution_options = execution_options or ExecutionOptions()


class BatchExecution:
    """Batch execution information"""
    def __init__(
        self,
        batch_id: UUID,
        user_id: UUID,
        total_tools: int,
        completed_tools: int,
        failed_tools: int,
        status: BatchStatus,
        stop_on_error: bool,
        created_at: datetime,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        tool_results: Optional[List[Dict[str, Any]]] = None
    ):
        self.batch_id = batch_id
        self.user_id = user_id
        self.total_tools = total_tools
        self.completed_tools = completed_tools
        self.failed_tools = failed_tools
        self.status = status
        self.stop_on_error = stop_on_error
        self.created_at = created_at
        self.started_at = started_at
        self.completed_at = completed_at
        self.tool_results = tool_results or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "user_id": str(self.user_id),
            "total_tools": self.total_tools,
            "completed_tools": self.completed_tools,
            "failed_tools": self.failed_tools,
            "status": self.status.value,
            "stop_on_error": self.stop_on_error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tool_results": self.tool_results
        }


class BatchStatusInfo:
    """Batch execution status information"""
    def __init__(
        self,
        batch_id: UUID,
        status: BatchStatus,
        total_tools: int,
        completed_tools: int,
        failed_tools: int,
        tool_statuses: List[Dict[str, Any]]
    ):
        self.batch_id = batch_id
        self.status = status
        self.total_tools = total_tools
        self.completed_tools = completed_tools
        self.failed_tools = failed_tools
        self.tool_statuses = tool_statuses
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": str(self.batch_id),
            "status": self.status.value,
            "total_tools": self.total_tools,
            "completed_tools": self.completed_tools,
            "failed_tools": self.failed_tools,
            "tool_statuses": self.tool_statuses
        }


class BatchExecutor:
    """
    Batch Executor handles parallel execution of multiple MCP tools.
    
    Responsibilities:
    - Execute multiple tools in parallel with concurrency control
    - Track individual tool status within batch
    - Implement stop-on-error logic
    - Aggregate batch results
    - Store batch execution metadata
    
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
    """
    
    def __init__(
        self,
        mcp_executor: MCPExecutor,
        db_session: AsyncSession,
        mongo_db: AsyncIOMotorDatabase,
        redis_client: Optional[Redis] = None
    ):
        self.executor = mcp_executor
        self.db = db_session
        self.mongo = mongo_db
        self.batch_collection = mongo_db["batch_execution_details"]
        self.redis = redis_client
    
    async def execute_batch(
        self,
        batch_request: BatchExecutionRequest,
        user_id: UUID
    ) -> BatchExecution:
        """
        Execute multiple tools in a batch with concurrency control.
        
        Validates all tool configurations before starting execution.
        Executes tools in parallel up to concurrency limit.
        Implements stop-on-error logic if configured.
        Aggregates results on completion.
        
        Args:
            batch_request: Batch execution configuration
            user_id: ID of the user executing the batch
            
        Returns:
            BatchExecution with batch ID and initial status
            
        Raises:
            MCPExecutionError: If validation fails or batch cannot be created
            
        **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**
        """
        # Validate batch request
        if not batch_request.tools:
            raise MCPExecutionError("Batch request must contain at least one tool")
        
        if len(batch_request.tools) > 50:
            raise MCPExecutionError("Batch request cannot exceed 50 tools")
        
        if batch_request.concurrency_limit < 1 or batch_request.concurrency_limit > 20:
            raise MCPExecutionError("Concurrency limit must be between 1 and 20")
        
        # Validate all tool configurations before starting
        # **Validates: Requirement 7.1**
        for i, tool_config in enumerate(batch_request.tools):
            if not tool_config.tool_id:
                raise MCPExecutionError(f"Tool {i}: tool_id is required")
            if not tool_config.tool_name:
                raise MCPExecutionError(f"Tool {i}: tool_name is required")
            if not isinstance(tool_config.arguments, dict):
                raise MCPExecutionError(f"Tool {i}: arguments must be a dictionary")
        
        # Generate batch ID
        batch_id = uuid4()
        created_at = datetime.utcnow()
        
        # Create batch execution record in MySQL
        batch_model = BatchExecutionModel(
            id=str(batch_id),
            user_id=str(user_id),
            total_tools=len(batch_request.tools),
            completed_tools=0,
            failed_tools=0,
            status=BatchStatus.QUEUED,
            stop_on_error=batch_request.stop_on_error,
            created_at=created_at
        )
        
        self.db.add(batch_model)
        await self.db.commit()
        await self.db.refresh(batch_model)
        
        # Store detailed batch configuration in MongoDB
        batch_document = {
            "batch_id": str(batch_id),
            "user_id": str(user_id),
            "tools": [
                {
                    "tool_id": str(tool.tool_id),
                    "tool_name": tool.tool_name,
                    "arguments": tool.arguments,
                    "execution_id": None,
                    "status": "queued",
                    "result": None,
                    "error": None,
                    "duration_ms": None
                }
                for tool in batch_request.tools
            ],
            "status": BatchStatus.QUEUED.value,
            "concurrency_limit": batch_request.concurrency_limit,
            "stop_on_error": batch_request.stop_on_error,
            "created_at": created_at,
            "completed_at": None,
            "total_duration_ms": None
        }
        
        await self.batch_collection.insert_one(batch_document)
        
        # Store batch status in Redis for fast access
        if self.redis:
            await self.redis.hset(
                f"batch:{batch_id}:status",
                mapping={
                    "status": BatchStatus.QUEUED.value,
                    "total_tools": str(len(batch_request.tools)),
                    "completed_tools": "0",
                    "failed_tools": "0"
                }
            )
            await self.redis.expire(f"batch:{batch_id}:status", 86400)  # 24 hours
        
        logger.info(
            "batch_execution_created",
            batch_id=str(batch_id),
            user_id=str(user_id),
            total_tools=len(batch_request.tools),
            concurrency_limit=batch_request.concurrency_limit,
            stop_on_error=batch_request.stop_on_error
        )
        
        # Start background execution
        asyncio.create_task(
            self._execute_batch_background(
                batch_id=batch_id,
                user_id=user_id,
                batch_request=batch_request
            )
        )
        
        return BatchExecution(
            batch_id=batch_id,
            user_id=user_id,
            total_tools=len(batch_request.tools),
            completed_tools=0,
            failed_tools=0,
            status=BatchStatus.QUEUED,
            stop_on_error=batch_request.stop_on_error,
            created_at=created_at
        )
    
    async def _execute_batch_background(
        self,
        batch_id: UUID,
        user_id: UUID,
        batch_request: BatchExecutionRequest
    ) -> None:
        """
        Background task for batch execution.
        
        Executes tools in parallel with concurrency control.
        Implements stop-on-error logic.
        Updates status in real-time.
        """
        batch_id_str = str(batch_id)
        start_time = datetime.utcnow()
        
        try:
            # Update status to running
            await self._update_batch_status(batch_id, BatchStatus.RUNNING)
            
            # Update MySQL
            stmt = update(BatchExecutionModel).where(
                BatchExecutionModel.id == batch_id_str
            ).values(
                status=BatchStatus.RUNNING,
                started_at=start_time
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Execute tools with concurrency control
            # **Validates: Requirement 7.2**
            semaphore = asyncio.Semaphore(batch_request.concurrency_limit)
            stop_flag = asyncio.Event()
            
            async def execute_tool_with_semaphore(index: int, tool_config: ToolExecutionConfig):
                """Execute a single tool with semaphore for concurrency control"""
                async with semaphore:
                    # Check stop flag if stop_on_error is enabled
                    if batch_request.stop_on_error and stop_flag.is_set():
                        logger.info(
                            "batch_tool_skipped",
                            batch_id=batch_id_str,
                            tool_index=index,
                            reason="stop_on_error"
                        )
                        return {
                            "index": index,
                            "status": "skipped",
                            "error": "Skipped due to previous error"
                        }
                    
                    tool_start = datetime.utcnow()
                    
                    try:
                        # Execute the tool
                        result = await self.executor.execute_tool(
                            tool_id=tool_config.tool_id,
                            tool_name=tool_config.tool_name,
                            arguments=tool_config.arguments,
                            user_id=user_id,
                            timeout=batch_request.execution_options.timeout,
                            retry_policy=batch_request.execution_options.retry_policy
                        )
                        
                        tool_end = datetime.utcnow()
                        duration_ms = int((tool_end - tool_start).total_seconds() * 1000)
                        
                        # Update tool status in MongoDB
                        await self.batch_collection.update_one(
                            {"batch_id": batch_id_str},
                            {
                                "$set": {
                                    f"tools.{index}.execution_id": result.get("execution_id"),
                                    f"tools.{index}.status": "success",
                                    f"tools.{index}.result": result.get("result"),
                                    f"tools.{index}.duration_ms": duration_ms
                                }
                            }
                        )
                        
                        # Increment completed count
                        await self._increment_completed(batch_id)
                        
                        logger.info(
                            "batch_tool_completed",
                            batch_id=batch_id_str,
                            tool_index=index,
                            tool_id=str(tool_config.tool_id),
                            duration_ms=duration_ms
                        )
                        
                        return {
                            "index": index,
                            "status": "success",
                            "result": result,
                            "duration_ms": duration_ms
                        }
                        
                    except Exception as e:
                        tool_end = datetime.utcnow()
                        duration_ms = int((tool_end - tool_start).total_seconds() * 1000)
                        error_message = str(e)
                        
                        # Update tool status in MongoDB
                        await self.batch_collection.update_one(
                            {"batch_id": batch_id_str},
                            {
                                "$set": {
                                    f"tools.{index}.status": "failed",
                                    f"tools.{index}.error": error_message,
                                    f"tools.{index}.duration_ms": duration_ms
                                }
                            }
                        )
                        
                        # Increment failed count
                        await self._increment_failed(batch_id)
                        
                        # Set stop flag if stop_on_error is enabled
                        # **Validates: Requirement 7.3**
                        if batch_request.stop_on_error:
                            stop_flag.set()
                            logger.warning(
                                "batch_stop_on_error",
                                batch_id=batch_id_str,
                                tool_index=index,
                                error=error_message
                            )
                        
                        logger.error(
                            "batch_tool_failed",
                            batch_id=batch_id_str,
                            tool_index=index,
                            tool_id=str(tool_config.tool_id),
                            error=error_message,
                            duration_ms=duration_ms
                        )
                        
                        return {
                            "index": index,
                            "status": "failed",
                            "error": error_message,
                            "duration_ms": duration_ms
                        }
            
            # Execute all tools in parallel with concurrency control
            tasks = [
                execute_tool_with_semaphore(i, tool)
                for i, tool in enumerate(batch_request.tools)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            end_time = datetime.utcnow()
            total_duration_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Determine final batch status
            failed_count = sum(1 for r in results if r["status"] == "failed")
            success_count = sum(1 for r in results if r["status"] == "success")
            
            if failed_count > 0:
                final_status = BatchStatus.FAILED
            else:
                final_status = BatchStatus.COMPLETED
            
            # Update batch status
            await self._update_batch_status(batch_id, final_status)
            
            # Update MySQL
            stmt = update(BatchExecutionModel).where(
                BatchExecutionModel.id == batch_id_str
            ).values(
                status=final_status,
                completed_at=end_time
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Update MongoDB with final status
            await self.batch_collection.update_one(
                {"batch_id": batch_id_str},
                {
                    "$set": {
                        "status": final_status.value,
                        "completed_at": end_time,
                        "total_duration_ms": total_duration_ms
                    }
                }
            )
            
            logger.info(
                "batch_execution_completed",
                batch_id=batch_id_str,
                status=final_status.value,
                total_tools=len(batch_request.tools),
                completed_tools=success_count,
                failed_tools=failed_count,
                total_duration_ms=total_duration_ms
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = str(e)
            
            # Update status to failed
            await self._update_batch_status(batch_id, BatchStatus.FAILED)
            
            # Update MySQL
            stmt = update(BatchExecutionModel).where(
                BatchExecutionModel.id == batch_id_str
            ).values(
                status=BatchStatus.FAILED,
                completed_at=end_time
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Update MongoDB
            await self.batch_collection.update_one(
                {"batch_id": batch_id_str},
                {
                    "$set": {
                        "status": BatchStatus.FAILED.value,
                        "completed_at": end_time,
                        "error": error_message
                    }
                }
            )
            
            logger.error(
                "batch_execution_failed",
                batch_id=batch_id_str,
                error=error_message
            )
    
    async def get_batch_status(
        self,
        batch_id: UUID
    ) -> BatchStatusInfo:
        """
        Get the current status of a batch execution.
        
        Returns status for each individual tool in the batch.
        
        Args:
            batch_id: ID of the batch to query
            
        Returns:
            BatchStatusInfo with current batch state and tool statuses
            
        Raises:
            MCPExecutionError: If batch not found
            
        **Validates: Requirements 7.4, 7.5**
        """
        batch_id_str = str(batch_id)
        
        # Try Redis first for fast lookup
        if self.redis:
            status_data = await self.redis.hgetall(f"batch:{batch_id}:status")
            if status_data:
                # Get detailed tool statuses from MongoDB
                batch_doc = await self.batch_collection.find_one({"batch_id": batch_id_str})
                
                if batch_doc:
                    tool_statuses = [
                        {
                            "tool_id": tool["tool_id"],
                            "tool_name": tool["tool_name"],
                            "execution_id": tool.get("execution_id"),
                            "status": tool["status"],
                            "result": tool.get("result"),
                            "error": tool.get("error"),
                            "duration_ms": tool.get("duration_ms")
                        }
                        for tool in batch_doc["tools"]
                    ]
                    
                    return BatchStatusInfo(
                        batch_id=batch_id,
                        status=BatchStatus[status_data["status"].upper()],
                        total_tools=int(status_data["total_tools"]),
                        completed_tools=int(status_data["completed_tools"]),
                        failed_tools=int(status_data["failed_tools"]),
                        tool_statuses=tool_statuses
                    )
        
        # Fallback to database
        stmt = select(BatchExecutionModel).where(
            BatchExecutionModel.id == batch_id_str
        )
        result = await self.db.execute(stmt)
        batch_model = result.scalar_one_or_none()
        
        if not batch_model:
            raise MCPExecutionError(f"Batch execution {batch_id} not found")
        
        # Get detailed tool statuses from MongoDB
        batch_doc = await self.batch_collection.find_one({"batch_id": batch_id_str})
        
        tool_statuses = []
        if batch_doc:
            tool_statuses = [
                {
                    "tool_id": tool["tool_id"],
                    "tool_name": tool["tool_name"],
                    "execution_id": tool.get("execution_id"),
                    "status": tool["status"],
                    "result": tool.get("result"),
                    "error": tool.get("error"),
                    "duration_ms": tool.get("duration_ms")
                }
                for tool in batch_doc["tools"]
            ]
        
        return BatchStatusInfo(
            batch_id=batch_id,
            status=batch_model.status,
            total_tools=batch_model.total_tools,
            completed_tools=batch_model.completed_tools,
            failed_tools=batch_model.failed_tools,
            tool_statuses=tool_statuses
        )
    
    async def cancel_batch(
        self,
        batch_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Cancel a batch execution.
        
        Cancels all running and queued tools in the batch.
        
        Args:
            batch_id: ID of the batch to cancel
            user_id: ID of the user requesting cancellation (for authorization)
            
        Returns:
            True if cancellation successful, False otherwise
            
        Raises:
            MCPExecutionError: If batch not found or user not authorized
        """
        batch_id_str = str(batch_id)
        
        # Get batch from database
        stmt = select(BatchExecutionModel).where(
            BatchExecutionModel.id == batch_id_str
        )
        result = await self.db.execute(stmt)
        batch_model = result.scalar_one_or_none()
        
        if not batch_model:
            raise MCPExecutionError(f"Batch execution {batch_id} not found")
        
        # Verify user owns this batch
        if batch_model.user_id != str(user_id):
            raise MCPExecutionError(
                f"User {user_id} does not have permission to cancel batch {batch_id}"
            )
        
        # Check if batch can be cancelled
        if batch_model.status in [BatchStatus.COMPLETED, BatchStatus.FAILED, BatchStatus.CANCELLED]:
            raise MCPExecutionError(
                f"Cannot cancel batch with status '{batch_model.status.value}'"
            )
        
        # Update status to cancelled
        await self._update_batch_status(batch_id, BatchStatus.CANCELLED)
        
        # Update MySQL
        stmt = update(BatchExecutionModel).where(
            BatchExecutionModel.id == batch_id_str
        ).values(
            status=BatchStatus.CANCELLED,
            completed_at=datetime.utcnow()
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Update MongoDB
        await self.batch_collection.update_one(
            {"batch_id": batch_id_str},
            {
                "$set": {
                    "status": BatchStatus.CANCELLED.value,
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(
            "batch_execution_cancelled",
            batch_id=batch_id_str,
            user_id=str(user_id)
        )
        
        # Note: Individual tool executions that are already running
        # will continue to completion. This cancels the batch coordination
        # but not individual tool processes.
        
        return True
    
    async def _update_batch_status(
        self,
        batch_id: UUID,
        status: BatchStatus
    ) -> None:
        """
        Update batch status in Redis.
        
        Args:
            batch_id: ID of the batch
            status: New status
        """
        if self.redis:
            await self.redis.hset(
                f"batch:{batch_id}:status",
                "status",
                status.value
            )
    
    async def _increment_completed(
        self,
        batch_id: UUID
    ) -> None:
        """
        Increment completed tools count.
        
        Args:
            batch_id: ID of the batch
        """
        batch_id_str = str(batch_id)
        
        # Update MySQL
        stmt = update(BatchExecutionModel).where(
            BatchExecutionModel.id == batch_id_str
        ).values(
            completed_tools=BatchExecutionModel.completed_tools + 1
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Update Redis
        if self.redis:
            await self.redis.hincrby(
                f"batch:{batch_id}:status",
                "completed_tools",
                1
            )
    
    async def _increment_failed(
        self,
        batch_id: UUID
    ) -> None:
        """
        Increment failed tools count.
        
        Args:
            batch_id: ID of the batch
        """
        batch_id_str = str(batch_id)
        
        # Update MySQL
        stmt = update(BatchExecutionModel).where(
            BatchExecutionModel.id == batch_id_str
        ).values(
            failed_tools=BatchExecutionModel.failed_tools + 1
        )
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Update Redis
        if self.redis:
            await self.redis.hincrby(
                f"batch:{batch_id}:status",
                "failed_tools",
                1
            )
