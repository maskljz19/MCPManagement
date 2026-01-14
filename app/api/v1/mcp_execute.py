"""MCP Tool Execution API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from uuid import UUID
from typing import List, Optional

from app.core.database import get_db, get_mongodb, get_redis
from app.services.mcp_manager import MCPManager
from app.services.mcp_executor import MCPExecutor
from app.schemas.mcp_execution import (
    MCPToolExecuteRequest,
    MCPToolExecuteResponse,
    MCPExecutionLog,
    AsyncExecutionResponse,
    ExecutionStatus
)
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission
from app.core.exceptions import MCPExecutionError


router = APIRouter(prefix="/mcps", tags=["MCP Execution"])


async def get_mcp_executor(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> MCPExecutor:
    """Dependency to get MCPExecutor instance"""
    mongo = get_mongodb()
    mcp_manager = MCPManager(db_session=db, mongo_db=mongo, cache=redis)
    
    # Get Elasticsearch client (optional)
    es_client = None
    try:
        from app.core.database import get_elasticsearch
        es_client = get_elasticsearch()
    except RuntimeError:
        # Elasticsearch not initialized, continue without it
        pass
    
    return MCPExecutor(
        mcp_manager=mcp_manager,
        mongo_db=mongo,
        redis_client=redis,
        es_client=es_client
    )


@router.post("/{tool_id}/execute", response_model=MCPToolExecuteResponse)
@require_permission("mcps", "execute")
async def execute_mcp_tool(
    tool_id: UUID,
    request: MCPToolExecuteRequest,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Execute an MCP tool with the provided arguments.
    
    This endpoint executes a specific tool within an MCP server using the
    tool's configuration. The tool must be in ACTIVE status to be executed.
    
    The execution process:
    1. Retrieves the tool configuration from the database
    2. Validates the tool status and configuration
    3. Executes the tool using JSON-RPC over stdio
    4. Logs the execution result to MongoDB
    5. Returns the execution result
    
    Args:
        tool_id: ID of the MCP tool to execute
        request: Execution request with tool_name, arguments, and timeout
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Execution result with status, result data, and execution metadata
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks execute permission
        HTTPException 404: If tool not found
        HTTPException 500: If execution fails
        
    Example:
        ```json
        POST /api/v1/mcps/{tool_id}/execute
        {
            "tool_name": "get_weather",
            "arguments": {
                "location": "San Francisco",
                "units": "celsius"
            },
            "timeout": 30
        }
        ```
    """
    try:
        result = await executor.execute_tool(
            tool_id=tool_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
            user_id=current_user.id,
            timeout=request.timeout
        )
        
        return MCPToolExecuteResponse(**result)
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.get_api_response()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during tool execution: {str(e)}"
        )


@router.get("/{tool_id}/executions", response_model=List[MCPExecutionLog])
@require_permission("mcps", "read")
async def get_tool_execution_logs(
    tool_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of logs to return"),
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Get execution logs for a specific MCP tool.
    
    Returns a list of execution logs for the specified tool, including
    successful and failed executions. Logs are sorted by execution time
    in descending order (most recent first).
    
    Args:
        tool_id: ID of the MCP tool
        limit: Maximum number of logs to return (1-200)
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        List of execution log entries
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission
    """
    logs = await executor.get_execution_logs(tool_id=tool_id, limit=limit)
    return [MCPExecutionLog(**log) for log in logs]


@router.get("/executions/my", response_model=List[MCPExecutionLog])
@require_permission("mcps", "read")
async def get_my_execution_logs(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of logs to return"),
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Get execution logs for the current user.
    
    Returns a list of all tool executions performed by the current user,
    across all tools. Logs are sorted by execution time in descending order.
    
    Args:
        limit: Maximum number of logs to return (1-200)
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        List of execution log entries
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    logs = await executor.get_execution_logs(user_id=current_user.id, limit=limit)
    return [MCPExecutionLog(**log) for log in logs]


@router.post("/{tool_id}/execute/async", response_model=AsyncExecutionResponse)
@require_permission("mcps", "execute")
async def execute_mcp_tool_async(
    tool_id: UUID,
    request: MCPToolExecuteRequest,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Execute an MCP tool asynchronously.
    
    This endpoint queues the tool execution and returns immediately with an
    execution ID. The client can poll the status endpoint or use WebSocket
    to receive real-time updates.
    
    Args:
        tool_id: ID of the MCP tool to execute
        request: Execution request with tool_name, arguments, timeout, and options
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Async execution response with execution_id for tracking
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks execute permission
        HTTPException 404: If tool not found
        HTTPException 500: If execution cannot be queued
        
    Example:
        ```json
        POST /api/v1/mcps/{tool_id}/execute/async
        {
            "tool_name": "get_weather",
            "arguments": {
                "location": "San Francisco"
            },
            "timeout": 60,
            "options": {
                "mode": "async",
                "priority": 5,
                "notify_on_completion": true
            }
        }
        ```
    """
    try:
        # Use options from request or create default
        options = request.options
        if options:
            # Ensure mode is async
            options.mode = "async"
        
        result = await executor.execute_async(
            tool_id=tool_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
            user_id=current_user.id,
            options=options
        )
        
        return AsyncExecutionResponse(**result)
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=e.get_api_response()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during async execution: {str(e)}"
        )


@router.get("/executions/{execution_id}/status", response_model=ExecutionStatus)
@require_permission("mcps", "read")
async def get_execution_status(
    execution_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Get the current status of an execution.
    
    Returns the current status, progress, and results (if completed) for
    an async execution. This endpoint can be polled to track execution progress.
    
    Args:
        execution_id: ID of the execution to query
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Execution status with current state and results
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission
        HTTPException 404: If execution not found
        
    Example:
        ```
        GET /api/v1/mcps/executions/{execution_id}/status
        ```
    """
    try:
        status_result = await executor.get_execution_status(execution_id)
        
        # Verify user owns this execution
        if status_result.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this execution"
            )
        
        return status_result
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving execution status: {str(e)}"
        )


@router.get("/executions/{execution_id}", response_model=ExecutionStatus)
@require_permission("mcps", "read")
async def get_execution_details(
    execution_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Get full execution details including status, results, and metadata.
    
    Returns comprehensive information about an execution including:
    - Current status and progress
    - Execution timestamps (queued, started, completed)
    - Results (if completed)
    - Error information (if failed)
    - Retry information
    - Duration and performance metrics
    
    Args:
        execution_id: ID of the execution to query
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Full execution details with all available information
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission or doesn't own execution
        HTTPException 404: If execution not found
        
    Example:
        ```
        GET /api/v1/mcps/executions/{execution_id}
        ```
    """
    try:
        execution_details = await executor.get_execution_status(execution_id)
        
        # Verify user owns this execution or is admin
        if execution_details.user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this execution"
            )
        
        return execution_details
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving execution details: {str(e)}"
        )


@router.get("/executions/{execution_id}/logs")
@require_permission("mcps", "read")
async def get_execution_logs(
    execution_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Get detailed logs for a specific execution.
    
    Returns log entries generated during the execution, including:
    - Execution start/end events
    - Tool invocation details
    - Error messages and stack traces
    - Performance metrics
    - Retry attempts (if any)
    
    This endpoint retrieves logs from MongoDB and optionally from Elasticsearch
    if available for enhanced search capabilities.
    
    Args:
        execution_id: ID of the execution to get logs for
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Execution log data with detailed information
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission or doesn't own execution
        HTTPException 404: If execution not found
        
    Example:
        ```
        GET /api/v1/mcps/executions/{execution_id}/logs
        ```
    """
    try:
        # First verify the execution exists and user has access
        execution_status = await executor.get_execution_status(execution_id)
        
        # Verify user owns this execution or is admin
        if execution_status.user_id != str(current_user.id) and current_user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view logs for this execution"
            )
        
        # Get the execution log from MongoDB
        log_entry = await executor.execution_log_collection.find_one(
            {"execution_id": str(execution_id)}
        )
        
        if not log_entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Logs not found for execution {execution_id}"
            )
        
        # Convert ObjectId to string for JSON serialization
        log_entry["_id"] = str(log_entry["_id"])
        
        # Format the response with structured log information
        response = {
            "execution_id": str(execution_id),
            "tool_id": log_entry.get("tool_id"),
            "tool_name": log_entry.get("tool_name"),
            "user_id": log_entry.get("user_id"),
            "status": log_entry.get("status"),
            "start_time": log_entry.get("start_time").isoformat() if log_entry.get("start_time") else None,
            "end_time": log_entry.get("end_time").isoformat() if log_entry.get("end_time") else None,
            "duration_ms": log_entry.get("duration_ms"),
            "arguments": log_entry.get("arguments"),
            "result": log_entry.get("result"),
            "error": log_entry.get("error"),
            "retry_count": log_entry.get("retry_count"),
            "timeout_seconds": log_entry.get("timeout_seconds"),
            "logs": log_entry.get("logs", []),
            "metadata": {
                "cancellation_requested_at": log_entry.get("cancellation_requested_at").isoformat() 
                    if log_entry.get("cancellation_requested_at") else None,
                "cancellation_message": log_entry.get("cancellation_message")
            }
        }
        
        # Try to get additional log details from Elasticsearch if available
        if executor.es_log_service:
            try:
                es_log = await executor.es_log_service.get_log_by_execution_id(execution_id)
                if es_log:
                    # Merge additional details from Elasticsearch
                    response["elasticsearch_available"] = True
                    if "logs" in es_log and es_log["logs"]:
                        response["logs"] = es_log["logs"]
            except Exception as e:
                # Log error but don't fail the request
                response["elasticsearch_available"] = False
                response["elasticsearch_error"] = str(e)
        else:
            response["elasticsearch_available"] = False
        
        return response
        
    except HTTPException:
        raise
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving execution logs: {str(e)}"
        )


@router.delete("/executions/{execution_id}", status_code=status.HTTP_200_OK)
@require_permission("mcps", "execute")
async def cancel_execution(
    execution_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    executor: MCPExecutor = Depends(get_mcp_executor)
):
    """
    Cancel a running or queued execution.
    
    Attempts to gracefully terminate the execution with a 30-second timeout.
    If graceful termination fails, the process is force-killed.
    
    Args:
        execution_id: ID of the execution to cancel
        current_user: Currently authenticated user
        executor: MCP Executor service
        
    Returns:
        Success message
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks execute permission or doesn't own execution
        HTTPException 404: If execution not found
        HTTPException 400: If execution cannot be cancelled (already completed)
        
    Example:
        ```
        DELETE /api/v1/mcps/executions/{execution_id}
        ```
    """
    try:
        success = await executor.cancel_execution(
            execution_id=execution_id,
            user_id=current_user.id
        )
        
        if success:
            return {
                "message": "Execution cancelled successfully",
                "execution_id": str(execution_id)
            }
        else:
            return {
                "message": "Execution cancellation attempted but may have failed",
                "execution_id": str(execution_id)
            }
        
    except MCPExecutionError as e:
        # Check if it's a permission error
        if "permission" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )
        # Check if it's a status error (already completed)
        elif "cannot cancel" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during cancellation: {str(e)}"
        )
