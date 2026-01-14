"""MCP Tool Executor Service - Handles actual execution of MCP tools"""

import asyncio
import json
import subprocess
import logging
from typing import Dict, Any, Optional, List
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from elasticsearch import AsyncElasticsearch

from app.services.mcp_manager import MCPManager
from app.services.parameter_validator import ParameterValidator, ValidationResult
from app.services.timeout_manager import TimeoutManager
from app.services.elasticsearch_log_service import ElasticsearchLogService
from app.core.exceptions import MCPExecutionError
from app.schemas.mcp_execution import ExecutionOptions, ExecutionStatus, RetryPolicy


logger = logging.getLogger(__name__)


class MCPExecutor:
    """
    MCP Executor handles the actual execution of MCP tools.
    
    Responsibilities:
    - Execute MCP tools using their configuration
    - Handle stdio communication with MCP servers
    - Parse and validate tool responses
    - Log execution history
    """
    
    def __init__(
        self,
        mcp_manager: MCPManager,
        mongo_db: AsyncIOMotorDatabase,
        redis_client: Optional[Redis] = None,
        es_client: Optional[AsyncElasticsearch] = None
    ):
        self.mcp_manager = mcp_manager
        self.mongo = mongo_db
        self.execution_log_collection = mongo_db["mcp_execution_logs"]
        self.redis = redis_client
        self.parameter_validator = ParameterValidator()
        self.timeout_manager = TimeoutManager()
        # Track running processes for cancellation
        self._running_processes: Dict[str, asyncio.subprocess.Process] = {}
        self._cancellation_events: Dict[str, asyncio.Event] = {}
        # Elasticsearch log service (optional)
        self.es_log_service = None
        if es_client:
            self.es_log_service = ElasticsearchLogService(es_client)
    
    async def execute_tool(
        self,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: UUID,
        timeout: int = 30,
        retry_policy: Optional[RetryPolicy] = None,
        user_tier: str = "viewer"
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool with the given arguments.
        
        Args:
            tool_id: ID of the MCP tool to execute
            tool_name: Name of the specific tool within the MCP server
            arguments: Arguments to pass to the tool
            user_id: ID of the user executing the tool
            timeout: Execution timeout in seconds
            retry_policy: Optional retry policy for failed executions
            user_tier: User tier for timeout validation
            
        Returns:
            Tool execution result
            
        Raises:
            MCPExecutionError: If execution fails
        """
        # Start execution
        start_time = datetime.utcnow()
        execution_id = None
        
        try:
            # Get tool configuration for validation
            tool = await self.mcp_manager.get_tool(tool_id)
            if not tool:
                raise MCPExecutionError(f"Tool with ID '{tool_id}' not found")
            
            # Determine and validate timeout
            validated_timeout = self.timeout_manager.get_timeout_for_execution(
                tool_config=tool.config,
                user_timeout=timeout,
                user_tier=user_tier
            )
            
            # Validate and sanitize parameters
            validation_result = await self._validate_and_sanitize_parameters(
                arguments,
                tool.config
            )
            
            if not validation_result.valid:
                # Format detailed error message
                error_details = []
                for error in validation_result.errors:
                    error_details.append(
                        f"{error.field}: {error.message}"
                    )
                raise MCPExecutionError(
                    f"Parameter validation failed: {'; '.join(error_details)}"
                )
            
            # Use sanitized parameters
            sanitized_arguments = validation_result.sanitized_params
            
            # Execute with retry logic and timeout enforcement
            result = await self._execute_with_retry(
                tool_id=tool_id,
                tool_name=tool_name,
                arguments=sanitized_arguments,
                user_id=user_id,
                timeout=validated_timeout,
                retry_policy=retry_policy
            )
            
            # Log successful execution
            execution_id = await self._log_execution(
                tool_id=tool_id,
                user_id=user_id,
                tool_name=tool_name,
                arguments=sanitized_arguments,
                result=result.get("result"),
                status="success",
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=None,
                timeout_seconds=validated_timeout
            )
            
            result["execution_id"] = str(execution_id)
            
            # Include validation warnings if any
            if validation_result.warnings:
                result["warnings"] = validation_result.warnings
            
            return result
            
        except asyncio.TimeoutError:
            # Handle timeout specifically
            error_message = f"Execution timed out after {timeout} seconds"
            execution_id = await self._log_execution(
                tool_id=tool_id,
                user_id=user_id,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status="timeout",
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=error_message,
                timeout_seconds=timeout
            )
            
            raise MCPExecutionError(
                error_message,
                execution_id=str(execution_id) if execution_id else None
            )
            
        except Exception as e:
            # Log failed execution
            error_message = str(e)
            status = "timeout" if "timed out" in error_message.lower() else "error"
            
            execution_id = await self._log_execution(
                tool_id=tool_id,
                user_id=user_id,
                tool_name=tool_name,
                arguments=arguments,
                result=None,
                status=status,
                start_time=start_time,
                end_time=datetime.utcnow(),
                error=error_message,
                timeout_seconds=timeout
            )
            
            raise MCPExecutionError(
                f"Failed to execute tool '{tool_name}': {error_message}",
                execution_id=str(execution_id) if execution_id else None
            )
    
    async def execute_async(
        self,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: UUID,
        options: Optional[ExecutionOptions] = None,
        user_tier: str = "viewer"
    ) -> Dict[str, Any]:
        """
        Execute an MCP tool asynchronously.
        
        Returns execution ID immediately and processes execution in background.
        
        Args:
            tool_id: ID of the MCP tool to execute
            tool_name: Name of the specific tool within the MCP server
            arguments: Arguments to pass to the tool
            user_id: ID of the user executing the tool
            options: Execution options (timeout, priority, etc.)
            user_tier: User tier for timeout validation
            
        Returns:
            Dict containing execution_id and initial status
            
        Raises:
            MCPExecutionError: If execution cannot be queued
        """
        if options is None:
            options = ExecutionOptions()
        
        # Get tool configuration for validation
        tool = await self.mcp_manager.get_tool(tool_id)
        if not tool:
            raise MCPExecutionError(f"Tool with ID '{tool_id}' not found")
        
        # Determine and validate timeout
        validated_timeout = self.timeout_manager.get_timeout_for_execution(
            tool_config=tool.config,
            user_timeout=options.timeout,
            user_tier=user_tier
        )
        
        # Validate and sanitize parameters
        validation_result = await self._validate_and_sanitize_parameters(
            arguments,
            tool.config
        )
        
        if not validation_result.valid:
            # Format detailed error message
            error_details = []
            for error in validation_result.errors:
                error_details.append(
                    f"{error.field}: {error.message}"
                )
            raise MCPExecutionError(
                f"Parameter validation failed: {'; '.join(error_details)}"
            )
        
        # Use sanitized parameters
        sanitized_arguments = validation_result.sanitized_params
        
        # Generate execution ID
        execution_id = uuid4()
        queued_at = datetime.utcnow()
        
        # Store initial execution metadata in Redis
        if self.redis:
            execution_key = f"execution:{execution_id}:status"
            metadata_key = f"execution:{execution_id}:metadata"
            
            # Store status
            await self.redis.set(
                execution_key,
                "queued",
                ex=86400  # Expire after 24 hours
            )
            
            # Store metadata
            metadata = {
                "execution_id": str(execution_id),
                "tool_id": str(tool_id),
                "tool_name": tool_name,
                "user_id": str(user_id),
                "arguments": json.dumps(sanitized_arguments),
                "status": "queued",
                "queued_at": queued_at.isoformat(),
                "timeout": str(validated_timeout),
                "priority": str(options.priority)
            }
            
            # Add validation warnings if any
            if validation_result.warnings:
                metadata["validation_warnings"] = json.dumps(validation_result.warnings)
            
            await self.redis.hset(
                metadata_key,
                mapping=metadata
            )
            await self.redis.expire(metadata_key, 86400)
        
        # Store in MongoDB for persistence
        await self._log_execution(
            tool_id=tool_id,
            user_id=user_id,
            tool_name=tool_name,
            arguments=sanitized_arguments,
            result=None,
            status="queued",
            start_time=queued_at,
            end_time=queued_at,
            error=None,
            execution_id=execution_id,
            timeout_seconds=validated_timeout
        )
        
        # Send WebSocket notification for queued status
        await self._notify_websocket_status_update(
            execution_id=execution_id,
            status="queued",
            metadata={
                "queued_at": queued_at.isoformat(),
                "timeout": validated_timeout
            }
        )
        
        # Start background execution task
        asyncio.create_task(
            self._execute_async_background(
                execution_id=execution_id,
                tool_id=tool_id,
                tool_name=tool_name,
                arguments=sanitized_arguments,
                user_id=user_id,
                timeout=validated_timeout,
                retry_policy=options.retry_policy
            )
        )
        
        response = {
            "execution_id": str(execution_id),
            "tool_id": str(tool_id),
            "tool_name": tool_name,
            "status": "queued",
            "queued_at": queued_at.isoformat(),
            "timeout": validated_timeout,
            "message": "Execution queued successfully"
        }
        
        # Include validation warnings if any
        if validation_result.warnings:
            response["warnings"] = validation_result.warnings
        
        return response
    
    async def _execute_async_background(
        self,
        execution_id: UUID,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: UUID,
        timeout: int,
        retry_policy: Optional[RetryPolicy] = None
    ) -> None:
        """
        Background task for async execution.
        
        This runs the actual execution and updates status in Redis and MongoDB.
        """
        execution_id_str = str(execution_id)
        start_time = datetime.utcnow()
        
        # Create cancellation event for this execution
        self._cancellation_events[execution_id_str] = asyncio.Event()
        
        try:
            # Check if already cancelled
            if self._cancellation_events[execution_id_str].is_set():
                await self._mark_execution_cancelled(execution_id, "Cancelled before execution started")
                return
            
            # Update status to running
            if self.redis:
                await self.redis.set(
                    f"execution:{execution_id}:status",
                    "running",
                    ex=86400
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "status",
                    "running"
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "started_at",
                    start_time.isoformat()
                )
            
            # Send WebSocket notification for status change to running
            await self._notify_websocket_status_update(
                execution_id=execution_id,
                status="running",
                metadata={"started_at": start_time.isoformat()}
            )
            
            # Execute the tool with retry logic
            result = await self._execute_with_retry(
                tool_id=tool_id,
                tool_name=tool_name,
                arguments=arguments,
                user_id=user_id,
                timeout=timeout,
                retry_policy=retry_policy,
                execution_id=execution_id
            )
            
            end_time = datetime.utcnow()
            
            # Check if cancelled during execution
            if self._cancellation_events[execution_id_str].is_set():
                await self._mark_execution_cancelled(execution_id, "Cancelled during execution")
                return
            
            # Update status to success
            if self.redis:
                await self.redis.set(
                    f"execution:{execution_id}:status",
                    "success",
                    ex=86400
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "status",
                    "success"
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "completed_at",
                    end_time.isoformat()
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "result",
                    json.dumps(result.get("result", {}))
                )
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "duration_ms",
                    str(duration_ms)
                )
            
            # Send WebSocket notification for successful completion
            await self._notify_websocket_execution_complete(
                execution_id=execution_id,
                status="success",
                result=result.get("result", {})
            )
            
            # Update MongoDB log
            await self.execution_log_collection.update_one(
                {"execution_id": str(execution_id)},
                {
                    "$set": {
                        "status": "success",
                        "result": result.get("result", {}),
                        "end_time": end_time,
                        "duration_ms": int((end_time - start_time).total_seconds() * 1000)
                    }
                }
            )
            
        except asyncio.TimeoutError:
            # Handle timeout specifically
            end_time = datetime.utcnow()
            elapsed_seconds = (end_time - start_time).total_seconds()
            error_message = f"Execution timed out after {timeout} seconds"
            
            # Record timeout event
            self.timeout_manager.record_timeout_event(
                execution_id=execution_id,
                tool_id=tool_id,
                tool_name=tool_name,
                timeout_seconds=timeout,
                elapsed_seconds=elapsed_seconds,
                context={"user_id": str(user_id)}
            )
            
            # Update status to timeout
            if self.redis:
                await self.redis.set(
                    f"execution:{execution_id}:status",
                    "timeout",
                    ex=86400
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "status",
                    "timeout"
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "completed_at",
                    end_time.isoformat()
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "error",
                    error_message
                )
                duration_ms = int(elapsed_seconds * 1000)
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "duration_ms",
                    str(duration_ms)
                )
            
            # Send WebSocket notification for timeout
            await self._notify_websocket_execution_complete(
                execution_id=execution_id,
                status="timeout",
                error=error_message
            )
            
            # Update MongoDB log
            await self.execution_log_collection.update_one(
                {"execution_id": str(execution_id)},
                {
                    "$set": {
                        "status": "timeout",
                        "error": error_message,
                        "end_time": end_time,
                        "duration_ms": int(elapsed_seconds * 1000)
                    }
                }
            )
            
        except Exception as e:
            end_time = datetime.utcnow()
            error_message = str(e)
            
            # Check if this was a cancellation
            if self._cancellation_events[execution_id_str].is_set():
                await self._mark_execution_cancelled(execution_id, f"Cancelled: {error_message}")
                return
            
            # Check if this is a timeout error
            status = "timeout" if "timed out" in error_message.lower() else "error"
            
            if status == "timeout":
                elapsed_seconds = (end_time - start_time).total_seconds()
                self.timeout_manager.record_timeout_event(
                    execution_id=execution_id,
                    tool_id=tool_id,
                    tool_name=tool_name,
                    timeout_seconds=timeout,
                    elapsed_seconds=elapsed_seconds,
                    context={"user_id": str(user_id), "error": error_message}
                )
            
            # Update status to error or timeout
            if self.redis:
                await self.redis.set(
                    f"execution:{execution_id}:status",
                    status,
                    ex=86400
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "status",
                    status
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "completed_at",
                    end_time.isoformat()
                )
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "error",
                    error_message
                )
                duration_ms = int((end_time - start_time).total_seconds() * 1000)
                await self.redis.hset(
                    f"execution:{execution_id}:metadata",
                    "duration_ms",
                    str(duration_ms)
                )
            
            # Send WebSocket notification for error/timeout
            await self._notify_websocket_execution_complete(
                execution_id=execution_id,
                status=status,
                error=error_message
            )
            
            # Update MongoDB log
            await self.execution_log_collection.update_one(
                {"execution_id": str(execution_id)},
                {
                    "$set": {
                        "status": status,
                        "error": error_message,
                        "end_time": end_time,
                        "duration_ms": int((end_time - start_time).total_seconds() * 1000)
                    }
                }
            )
        finally:
            # Clean up tracking
            if execution_id_str in self._cancellation_events:
                del self._cancellation_events[execution_id_str]
            if execution_id_str in self._running_processes:
                del self._running_processes[execution_id_str]
            # Clean up timeout event tracking
            self.timeout_manager.clear_timeout_event(execution_id)
    
    async def _execute_tool_with_cancellation(
        self,
        execution_id: UUID,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: UUID,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute tool with cancellation support.
        
        This is similar to execute_tool but tracks the process for cancellation.
        """
        execution_id_str = str(execution_id)
        
        # Get tool configuration
        tool = await self.mcp_manager.get_tool(tool_id)
        if not tool:
            raise MCPExecutionError(f"Tool with ID '{tool_id}' not found")
        
        if not tool.config:
            raise MCPExecutionError(f"Tool '{tool.name}' has no configuration")
        
        # Extract command and args from config
        command = tool.config.get("command")
        args = tool.config.get("args", [])
        env = tool.config.get("env", {})
        
        if not command:
            raise MCPExecutionError(f"Tool '{tool.name}' configuration missing 'command'")
        
        # Execute with process tracking
        result = await self._execute_mcp_command_with_tracking(
            execution_id=execution_id,
            command=command,
            args=args,
            env=env,
            tool_name=tool_name,
            arguments=arguments,
            timeout=timeout
        )
        
        return {
            "execution_id": str(execution_id),
            "tool_id": str(tool_id),
            "tool_name": tool_name,
            "status": "success",
            "result": result,
            "executed_at": datetime.utcnow().isoformat()
        }
    
    async def _execute_mcp_command_with_tracking(
        self,
        execution_id: UUID,
        command: str,
        args: List[str],
        env: Dict[str, str],
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute MCP command with process tracking for cancellation and timeout.
        """
        execution_id_str = str(execution_id)
        process = None
        
        # Build the command
        cmd = [command] + args
        
        # Prepare the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        request_json = json.dumps(request) + "\n"
        
        async def cleanup_resources():
            """Cleanup callback for timeout"""
            nonlocal process
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                    logger.info(f"Cleaned up process for execution {execution_id_str} after timeout")
                except Exception as e:
                    logger.error(f"Error cleaning up process: {str(e)}")
        
        try:
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**env}
            )
            
            # Track the process for cancellation
            self._running_processes[execution_id_str] = process
            
            # Check for cancellation before communicating
            if self._cancellation_events[execution_id_str].is_set():
                process.kill()
                await process.wait()
                raise MCPExecutionError("Execution cancelled")
            
            # Send request and get response with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=request_json.encode()),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Cleanup resources on timeout
                await cleanup_resources()
                raise MCPExecutionError(f"Tool execution timed out after {timeout} seconds")
            
            # Check return code
            if process.returncode != 0:
                error_output = stderr.decode() if stderr else "Unknown error"
                raise MCPExecutionError(f"Tool execution failed: {error_output}")
            
            # Parse response
            response_text = stdout.decode().strip()
            if not response_text:
                raise MCPExecutionError("Tool returned empty response")
            
            # Parse JSON-RPC response
            response = json.loads(response_text)
            
            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise MCPExecutionError(
                    f"Tool returned error: {error.get('message', 'Unknown error')}"
                )
            
            # Return the result
            return response.get("result", {})
            
        except json.JSONDecodeError as e:
            raise MCPExecutionError(f"Failed to parse tool response: {str(e)}")
        except FileNotFoundError:
            raise MCPExecutionError(f"Command '{command}' not found. Make sure it's installed.")
        except Exception as e:
            if isinstance(e, MCPExecutionError):
                raise
            raise MCPExecutionError(f"Unexpected error during execution: {str(e)}")
        finally:
            # Clean up process tracking
            if execution_id_str in self._running_processes:
                del self._running_processes[execution_id_str]
    
    async def get_execution_status(
        self,
        execution_id: UUID
    ) -> ExecutionStatus:
        """
        Get the current status of an async execution.
        
        Args:
            execution_id: ID of the execution to query
            
        Returns:
            ExecutionStatus with current execution state
            
        Raises:
            MCPExecutionError: If execution not found
        """
        # Try Redis first for fast lookup
        if self.redis:
            metadata_key = f"execution:{execution_id}:metadata"
            metadata = await self.redis.hgetall(metadata_key)
            
            if metadata:
                # Parse result if present
                result = None
                if "result" in metadata and metadata["result"]:
                    try:
                        result = json.loads(metadata["result"])
                    except json.JSONDecodeError:
                        result = None
                
                # Parse retry_count if present
                retry_count = None
                if "retry_count" in metadata and metadata["retry_count"]:
                    try:
                        retry_count = int(metadata["retry_count"])
                    except (ValueError, TypeError):
                        retry_count = None
                
                return ExecutionStatus(
                    execution_id=metadata.get("execution_id", str(execution_id)),
                    tool_id=metadata.get("tool_id", ""),
                    tool_name=metadata.get("tool_name", ""),
                    user_id=metadata.get("user_id", ""),
                    status=metadata.get("status", "unknown"),
                    progress=None,  # TODO: Implement progress tracking
                    queued_at=metadata.get("queued_at"),
                    started_at=metadata.get("started_at"),
                    completed_at=metadata.get("completed_at"),
                    duration_ms=int(metadata["duration_ms"]) if "duration_ms" in metadata else None,
                    result=result,
                    error=metadata.get("error"),
                    retry_count=retry_count,
                    metadata={}
                )
        
        # Fallback to MongoDB
        log_entry = await self.execution_log_collection.find_one(
            {"execution_id": str(execution_id)}
        )
        
        if not log_entry:
            raise MCPExecutionError(f"Execution with ID '{execution_id}' not found")
        
        return ExecutionStatus(
            execution_id=str(execution_id),
            tool_id=log_entry.get("tool_id", ""),
            tool_name=log_entry.get("tool_name", ""),
            user_id=log_entry.get("user_id", ""),
            status=log_entry.get("status", "unknown"),
            progress=None,
            queued_at=log_entry.get("start_time").isoformat() if log_entry.get("start_time") else None,
            started_at=log_entry.get("start_time").isoformat() if log_entry.get("start_time") else None,
            completed_at=log_entry.get("end_time").isoformat() if log_entry.get("end_time") else None,
            duration_ms=log_entry.get("duration_ms"),
            result=log_entry.get("result"),
            error=log_entry.get("error"),
            retry_count=log_entry.get("retry_count"),
            metadata={}
        )
    
    async def cancel_execution(
        self,
        execution_id: UUID,
        user_id: UUID
    ) -> bool:
        """
        Cancel a running or queued execution.
        
        Implements graceful termination with 30-second timeout and force-kill fallback.
        
        Args:
            execution_id: ID of the execution to cancel
            user_id: ID of the user requesting cancellation (for authorization)
            
        Returns:
            True if cancellation was successful, False otherwise
            
        Raises:
            MCPExecutionError: If execution not found or already completed
        """
        execution_id_str = str(execution_id)
        
        # Check if execution exists and get current status
        current_status = await self.get_execution_status(execution_id)
        
        # Verify user owns this execution
        if current_status.user_id != str(user_id):
            raise MCPExecutionError(
                f"User {user_id} does not have permission to cancel execution {execution_id}"
            )
        
        # Check if execution can be cancelled
        if current_status.status in ["success", "error", "cancelled", "timeout"]:
            raise MCPExecutionError(
                f"Cannot cancel execution with status '{current_status.status}'"
            )
        
        # Update status to "cancelling" immediately
        if self.redis:
            await self.redis.set(
                f"execution:{execution_id}:status",
                "cancelling",
                ex=86400
            )
            await self.redis.hset(
                f"execution:{execution_id}:metadata",
                "status",
                "cancelling"
            )
        
        # Send WebSocket notification for cancelling status
        await self._notify_websocket_status_update(
            execution_id=execution_id,
            status="cancelling",
            metadata={"cancellation_requested_at": datetime.utcnow().isoformat()}
        )
        
        # Update MongoDB
        await self.execution_log_collection.update_one(
            {"execution_id": execution_id_str},
            {
                "$set": {
                    "status": "cancelling",
                    "cancellation_requested_at": datetime.utcnow()
                }
            }
        )
        
        # If execution is only queued, mark as cancelled immediately
        if current_status.status == "queued":
            await self._mark_execution_cancelled(execution_id, "Cancelled by user before execution started")
            return True
        
        # For running executions, signal cancellation
        if execution_id_str in self._cancellation_events:
            self._cancellation_events[execution_id_str].set()
        
        # If we have a running process, try to terminate it gracefully
        if execution_id_str in self._running_processes:
            process = self._running_processes[execution_id_str]
            
            try:
                # Send SIGTERM for graceful shutdown
                process.terminate()
                
                # Wait up to 30 seconds for graceful termination
                try:
                    await asyncio.wait_for(process.wait(), timeout=30.0)
                    # Process terminated gracefully
                    await self._mark_execution_cancelled(execution_id, "Cancelled by user request")
                    return True
                    
                except asyncio.TimeoutError:
                    # Graceful termination failed, force kill
                    process.kill()
                    await process.wait()
                    await self._mark_execution_cancelled(
                        execution_id,
                        "Cancelled by user request (force killed after timeout)"
                    )
                    return True
                    
            except Exception as e:
                # Log error but still mark as cancelled
                await self._mark_execution_cancelled(
                    execution_id,
                    f"Cancellation attempted but encountered error: {str(e)}"
                )
                return False
            finally:
                # Clean up tracking
                if execution_id_str in self._running_processes:
                    del self._running_processes[execution_id_str]
                if execution_id_str in self._cancellation_events:
                    del self._cancellation_events[execution_id_str]
        
        # If no process found, mark as cancelled anyway
        await self._mark_execution_cancelled(execution_id, "Cancelled by user request")
        return True
    
    async def _mark_execution_cancelled(
        self,
        execution_id: UUID,
        message: str
    ) -> None:
        """
        Mark an execution as cancelled in both Redis and MongoDB.
        
        Args:
            execution_id: ID of the execution
            message: Cancellation message/reason
        """
        execution_id_str = str(execution_id)
        completed_at = datetime.utcnow()
        
        # Update Redis
        if self.redis:
            await self.redis.set(
                f"execution:{execution_id}:status",
                "cancelled",
                ex=86400
            )
            await self.redis.hset(
                f"execution:{execution_id}:metadata",
                "status",
                "cancelled"
            )
            await self.redis.hset(
                f"execution:{execution_id}:metadata",
                "completed_at",
                completed_at.isoformat()
            )
            await self.redis.hset(
                f"execution:{execution_id}:metadata",
                "cancellation_message",
                message
            )
        
        # Send WebSocket notification for cancellation
        await self._notify_websocket_execution_complete(
            execution_id=execution_id,
            status="cancelled",
            error=message
        )
        
        # Update MongoDB
        await self.execution_log_collection.update_one(
            {"execution_id": execution_id_str},
            {
                "$set": {
                    "status": "cancelled",
                    "end_time": completed_at,
                    "error": message
                }
            }
        )
    
    def _classify_error(self, error: Exception) -> str:
        """
        Classify an error to determine if it's retryable.
        
        Args:
            error: The exception that occurred
            
        Returns:
            Error type string (e.g., "timeout", "connection_error", "validation_error")
        """
        error_message = str(error).lower()
        
        # Timeout errors
        if isinstance(error, asyncio.TimeoutError) or "timeout" in error_message or "timed out" in error_message:
            return "timeout"
        
        # Connection errors
        if "connection" in error_message or "refused" in error_message or "unreachable" in error_message:
            return "connection_error"
        
        # Rate limit errors
        if "rate limit" in error_message or "too many requests" in error_message or "429" in error_message:
            return "rate_limit_exceeded"
        
        # Server errors (5xx)
        if "server error" in error_message or "500" in error_message or "503" in error_message:
            return "server_error"
        
        # Temporary failures
        if "temporary" in error_message or "unavailable" in error_message:
            return "temporary_failure"
        
        # Validation errors (non-retryable)
        if "validation" in error_message or "invalid" in error_message or "schema" in error_message:
            return "validation_error"
        
        # Permission errors (non-retryable)
        if "permission" in error_message or "forbidden" in error_message or "unauthorized" in error_message or "403" in error_message or "401" in error_message:
            return "permission_error"
        
        # Not found errors (non-retryable)
        if "not found" in error_message or "404" in error_message:
            return "not_found_error"
        
        # Default to unknown error
        return "unknown_error"
    
    def _is_retryable_error(self, error_type: str, retry_policy: RetryPolicy) -> bool:
        """
        Determine if an error type is retryable based on the retry policy.
        
        Args:
            error_type: The classified error type
            retry_policy: The retry policy configuration
            
        Returns:
            True if the error should be retried, False otherwise
        """
        return error_type in retry_policy.retryable_errors
    
    def _calculate_retry_delay(
        self,
        attempt: int,
        retry_policy: RetryPolicy
    ) -> float:
        """
        Calculate the delay before the next retry using exponential backoff.
        
        Args:
            attempt: The current attempt number (0-indexed)
            retry_policy: The retry policy configuration
            
        Returns:
            Delay in seconds before next retry
        """
        # Calculate exponential backoff: initial_delay * (multiplier ^ attempt)
        delay = retry_policy.initial_delay_seconds * (retry_policy.backoff_multiplier ** attempt)
        
        # Cap at max_delay_seconds
        return min(delay, retry_policy.max_delay_seconds)
    
    async def _execute_with_retry(
        self,
        tool_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        user_id: UUID,
        timeout: int,
        retry_policy: Optional[RetryPolicy] = None,
        execution_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Execute a tool with retry logic.
        
        Args:
            tool_id: ID of the MCP tool to execute
            tool_name: Name of the specific tool within the MCP server
            arguments: Arguments to pass to the tool
            user_id: ID of the user executing the tool
            timeout: Execution timeout in seconds
            retry_policy: Retry policy configuration (None = no retries)
            execution_id: Optional execution ID for tracking
            
        Returns:
            Tool execution result
            
        Raises:
            MCPExecutionError: If execution fails after all retries
        """
        # If no retry policy, execute once without retry
        if retry_policy is None:
            retry_policy = RetryPolicy(max_attempts=1)
        
        last_error = None
        retry_count = 0
        
        for attempt in range(retry_policy.max_attempts):
            try:
                # Execute the tool
                if execution_id:
                    result = await self._execute_tool_with_cancellation(
                        execution_id=execution_id,
                        tool_id=tool_id,
                        tool_name=tool_name,
                        arguments=arguments,
                        user_id=user_id,
                        timeout=timeout
                    )
                else:
                    # Get tool configuration
                    tool = await self.mcp_manager.get_tool(tool_id)
                    if not tool:
                        raise MCPExecutionError(f"Tool with ID '{tool_id}' not found")
                    
                    if not tool.config:
                        raise MCPExecutionError(f"Tool '{tool.name}' has no configuration")
                    
                    # Extract command and args from config
                    command = tool.config.get("command")
                    args = tool.config.get("args", [])
                    env = tool.config.get("env", {})
                    
                    if not command:
                        raise MCPExecutionError(f"Tool '{tool.name}' configuration missing 'command'")
                    
                    # Execute the MCP tool
                    result_data = await self._execute_mcp_command(
                        command=command,
                        args=args,
                        env=env,
                        tool_name=tool_name,
                        arguments=arguments,
                        timeout=timeout
                    )
                    
                    result = {
                        "execution_id": str(uuid4()),
                        "tool_id": str(tool_id),
                        "tool_name": tool_name,
                        "status": "success",
                        "result": result_data,
                        "executed_at": datetime.utcnow().isoformat()
                    }
                
                # Success! Record retry count if any retries were made
                if retry_count > 0 and execution_id:
                    await self._record_retry_metadata(execution_id, retry_count)
                
                return result
                
            except Exception as e:
                last_error = e
                retry_count = attempt + 1
                
                # Classify the error
                error_type = self._classify_error(e)
                
                # Check if we should retry
                should_retry = (
                    retry_count < retry_policy.max_attempts and
                    self._is_retryable_error(error_type, retry_policy)
                )
                
                if not should_retry:
                    # No more retries or non-retryable error
                    if execution_id:
                        await self._record_retry_metadata(execution_id, retry_count)
                    raise
                
                # Calculate delay before next retry
                delay = self._calculate_retry_delay(attempt, retry_policy)
                
                # Log retry attempt
                if execution_id and self.redis:
                    await self.redis.hset(
                        f"execution:{execution_id}:metadata",
                        f"retry_attempt_{retry_count}",
                        json.dumps({
                            "attempt": retry_count,
                            "error_type": error_type,
                            "error_message": str(e),
                            "delay_seconds": delay,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    )
                
                # Wait before retrying
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if execution_id:
            await self._record_retry_metadata(execution_id, retry_count)
        
        raise MCPExecutionError(
            f"Execution failed after {retry_count} attempts: {str(last_error)}"
        )
    
    async def _record_retry_metadata(
        self,
        execution_id: UUID,
        retry_count: int
    ) -> None:
        """
        Record retry metadata in Redis and MongoDB.
        
        Args:
            execution_id: ID of the execution
            retry_count: Total number of retry attempts made
        """
        execution_id_str = str(execution_id)
        
        # Update Redis
        if self.redis:
            await self.redis.hset(
                f"execution:{execution_id}:metadata",
                "retry_count",
                str(retry_count)
            )
        
        # Update MongoDB
        await self.execution_log_collection.update_one(
            {"execution_id": execution_id_str},
            {
                "$set": {
                    "retry_count": retry_count
                }
            }
        )
    
    async def _execute_mcp_command(
        self,
        command: str,
        args: List[str],
        env: Dict[str, str],
        tool_name: str,
        arguments: Dict[str, Any],
        timeout: int
    ) -> Dict[str, Any]:
        """
        Execute MCP command using stdio protocol with timeout and resource cleanup.
        
        MCP uses JSON-RPC 2.0 over stdio for communication.
        """
        process = None
        
        # Build the command
        cmd = [command] + args
        
        # Prepare the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        request_json = json.dumps(request) + "\n"
        
        try:
            # Execute the command
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**env}
            )
            
            # Send request and get response with timeout
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=request_json.encode()),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                # Kill process and cleanup on timeout
                if process.returncode is None:
                    process.kill()
                    await process.wait()
                    logger.warning(f"Process killed due to timeout after {timeout}s")
                raise MCPExecutionError(f"Tool execution timed out after {timeout} seconds")
            
            # Check return code
            if process.returncode != 0:
                error_output = stderr.decode() if stderr else "Unknown error"
                raise MCPExecutionError(f"Tool execution failed: {error_output}")
            
            # Parse response
            response_text = stdout.decode().strip()
            if not response_text:
                raise MCPExecutionError("Tool returned empty response")
            
            # Parse JSON-RPC response
            response = json.loads(response_text)
            
            # Check for JSON-RPC error
            if "error" in response:
                error = response["error"]
                raise MCPExecutionError(
                    f"Tool returned error: {error.get('message', 'Unknown error')}"
                )
            
            # Return the result
            return response.get("result", {})
            
        except json.JSONDecodeError as e:
            raise MCPExecutionError(f"Failed to parse tool response: {str(e)}")
        except FileNotFoundError:
            raise MCPExecutionError(f"Command '{command}' not found. Make sure it's installed.")
        except Exception as e:
            # Ensure process is cleaned up on any error
            if process and process.returncode is None:
                try:
                    process.kill()
                    await process.wait()
                except Exception as cleanup_error:
                    logger.error(f"Error cleaning up process: {str(cleanup_error)}")
            
            if isinstance(e, MCPExecutionError):
                raise
            raise MCPExecutionError(f"Unexpected error during execution: {str(e)}")
    
    async def _log_execution(
        self,
        tool_id: UUID,
        user_id: UUID,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Optional[Dict[str, Any]],
        status: str,
        start_time: datetime,
        end_time: datetime,
        error: Optional[str],
        execution_id: Optional[UUID] = None,
        timeout_seconds: Optional[int] = None
    ) -> Any:
        """Log tool execution to MongoDB and Elasticsearch with timeout information"""
        document = {
            "execution_id": str(execution_id) if execution_id else str(uuid4()),
            "tool_id": str(tool_id),
            "user_id": str(user_id),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
            "status": status,
            "start_time": start_time,
            "end_time": end_time,
            "duration_ms": int((end_time - start_time).total_seconds() * 1000),
            "error": error,
            "timestamp": end_time  # For Elasticsearch indexing
        }
        
        # Add timeout information if provided
        if timeout_seconds is not None:
            document["timeout_seconds"] = timeout_seconds
        
        # Insert to MongoDB
        insert_result = await self.execution_log_collection.insert_one(document)
        
        # Also index to Elasticsearch if available
        if self.es_log_service:
            try:
                await self.es_log_service.index_execution_log(document)
            except Exception as e:
                # Log error but don't fail the execution
                logger.warning(f"Failed to index log to Elasticsearch: {str(e)}")
        
        return insert_result.inserted_id
    
    async def _validate_and_sanitize_parameters(
        self,
        arguments: Dict[str, Any],
        tool_config: Optional[Dict[str, Any]]
    ) -> ValidationResult:
        """
        Validate and sanitize parameters before execution.
        
        Args:
            arguments: Parameters to validate
            tool_config: Tool configuration containing schema and defaults
            
        Returns:
            ValidationResult with validation status and sanitized parameters
        """
        # Extract schema from tool config if available
        schema = None
        if tool_config and "parameter_schema" in tool_config:
            schema = tool_config["parameter_schema"]
        
        # Validate parameters
        validation_result = await self.parameter_validator.validate_parameters(
            parameters=arguments,
            schema=schema,
            tool_config=tool_config
        )
        
        return validation_result
    
    async def get_execution_logs(
        self,
        tool_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get execution logs with optional filtering.
        
        Args:
            tool_id: Filter by tool ID
            user_id: Filter by user ID
            limit: Maximum number of logs to return
            
        Returns:
            List of execution log entries
        """
        query = {}
        if tool_id:
            query["tool_id"] = str(tool_id)
        if user_id:
            query["user_id"] = str(user_id)
        
        cursor = self.execution_log_collection.find(query).sort(
            "start_time", -1
        ).limit(limit)
        
        logs = []
        async for doc in cursor:
            # Convert ObjectId to string for JSON serialization
            doc["_id"] = str(doc["_id"])
            logs.append(doc)
        
        return logs

    
    async def _notify_websocket_status_update(
        self,
        execution_id: UUID,
        status: str,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Send WebSocket notification for execution status update.
        
        This method safely imports and calls the WebSocket notification function
        to avoid circular imports.
        
        Args:
            execution_id: Execution identifier
            status: Current execution status
            progress: Optional progress percentage
            metadata: Optional additional metadata
        
        Validates: Requirements 3.1, 3.2
        """
        try:
            # Import here to avoid circular dependency
            from app.api.v1.websocket import notify_execution_status_update
            
            await notify_execution_status_update(
                execution_id=str(execution_id),
                status=status,
                progress=progress,
                metadata=metadata
            )
        except Exception as e:
            # Log error but don't fail execution
            logger.warning(
                f"Failed to send WebSocket status update: {str(e)}",
                extra={
                    "execution_id": str(execution_id),
                    "status": status
                }
            )
    
    async def _notify_websocket_log_entry(
        self,
        execution_id: UUID,
        log_level: str,
        message: str,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Send WebSocket notification for log entry.
        
        Args:
            execution_id: Execution identifier
            log_level: Log level (info, warning, error, debug)
            message: Log message
            timestamp: Optional log timestamp
        
        Validates: Requirements 3.3
        """
        try:
            # Import here to avoid circular dependency
            from app.api.v1.websocket import notify_execution_log_entry
            
            await notify_execution_log_entry(
                execution_id=str(execution_id),
                log_level=log_level,
                message=message,
                timestamp=timestamp
            )
        except Exception as e:
            # Log error but don't fail execution
            logger.debug(
                f"Failed to send WebSocket log entry: {str(e)}",
                extra={
                    "execution_id": str(execution_id),
                    "log_level": log_level
                }
            )
    
    async def _notify_websocket_execution_complete(
        self,
        execution_id: UUID,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> None:
        """
        Send WebSocket notification for execution completion.
        
        Args:
            execution_id: Execution identifier
            status: Final execution status
            result: Optional execution result
            error: Optional error message
        
        Validates: Requirements 3.1, 3.2
        """
        try:
            # Import here to avoid circular dependency
            from app.api.v1.websocket import notify_execution_complete
            
            await notify_execution_complete(
                execution_id=str(execution_id),
                status=status,
                result=result,
                error=error
            )
        except Exception as e:
            # Log error but don't fail execution
            logger.warning(
                f"Failed to send WebSocket completion notification: {str(e)}",
                extra={
                    "execution_id": str(execution_id),
                    "status": status
                }
            )
