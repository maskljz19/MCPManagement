"""Batch Execution API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from uuid import UUID
from typing import List, Dict, Any

from app.core.database import get_db, get_mongodb, get_redis
from app.services.mcp_manager import MCPManager
from app.services.mcp_executor import MCPExecutor
from app.services.batch_executor import (
    BatchExecutor,
    BatchExecutionRequest,
    ToolExecutionConfig
)
from app.schemas.mcp_execution import ExecutionOptions
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission
from app.core.exceptions import MCPExecutionError
from pydantic import BaseModel, Field


router = APIRouter(prefix="/batch", tags=["Batch Execution"])


class ToolExecutionConfigSchema(BaseModel):
    """Schema for a single tool execution within a batch"""
    tool_id: UUID = Field(..., description="ID of the MCP tool to execute")
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool"
    )


class BatchExecuteRequest(BaseModel):
    """Schema for batch execution request"""
    tools: List[ToolExecutionConfigSchema] = Field(
        ...,
        min_length=1,
        max_length=50,
        description="List of tools to execute (1-50)"
    )
    concurrency_limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of tools to execute concurrently (1-20)"
    )
    stop_on_error: bool = Field(
        default=False,
        description="Stop executing remaining tools if any tool fails"
    )
    execution_options: ExecutionOptions = Field(
        default_factory=ExecutionOptions,
        description="Execution options applied to all tools"
    )


class BatchExecuteResponse(BaseModel):
    """Schema for batch execution response"""
    batch_id: str = Field(..., description="Unique batch execution ID")
    user_id: str = Field(..., description="ID of the user who initiated the batch")
    total_tools: int = Field(..., description="Total number of tools in the batch")
    completed_tools: int = Field(..., description="Number of completed tools")
    failed_tools: int = Field(..., description="Number of failed tools")
    status: str = Field(..., description="Batch status: queued, running, completed, failed, cancelled")
    stop_on_error: bool = Field(..., description="Whether batch stops on first error")
    created_at: str = Field(..., description="When the batch was created (ISO format)")
    started_at: str = Field(None, description="When the batch started executing (ISO format)")
    completed_at: str = Field(None, description="When the batch completed (ISO format)")
    message: str = Field(
        default="Batch execution queued successfully",
        description="Status message"
    )


class ToolStatusSchema(BaseModel):
    """Schema for individual tool status within a batch"""
    tool_id: str = Field(..., description="ID of the tool")
    tool_name: str = Field(..., description="Name of the tool")
    execution_id: str = Field(None, description="Execution ID if tool has been executed")
    status: str = Field(..., description="Tool status: queued, running, success, failed, skipped")
    result: Dict[str, Any] = Field(None, description="Tool execution result if completed")
    error: str = Field(None, description="Error message if failed")
    duration_ms: int = Field(None, description="Execution duration in milliseconds")


class BatchStatusResponse(BaseModel):
    """Schema for batch status response"""
    batch_id: str = Field(..., description="Unique batch execution ID")
    status: str = Field(..., description="Batch status: queued, running, completed, failed, cancelled")
    total_tools: int = Field(..., description="Total number of tools in the batch")
    completed_tools: int = Field(..., description="Number of completed tools")
    failed_tools: int = Field(..., description="Number of failed tools")
    tool_statuses: List[ToolStatusSchema] = Field(
        ...,
        description="Status of each individual tool in the batch"
    )


async def get_batch_executor(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> BatchExecutor:
    """Dependency to get BatchExecutor instance"""
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
    
    mcp_executor = MCPExecutor(
        mcp_manager=mcp_manager,
        mongo_db=mongo,
        redis_client=redis,
        es_client=es_client
    )
    
    return BatchExecutor(
        mcp_executor=mcp_executor,
        db_session=db,
        mongo_db=mongo,
        redis_client=redis
    )


@router.post("/execute", response_model=BatchExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
@require_permission("mcps", "execute")
async def execute_batch(
    request: BatchExecuteRequest,
    current_user: UserModel = Depends(get_current_user),
    batch_executor: BatchExecutor = Depends(get_batch_executor)
):
    """
    Execute multiple MCP tools in a batch operation.
    
    This endpoint allows executing multiple tools in parallel with configurable
    concurrency limits. The batch execution is queued and returns immediately
    with a batch ID for tracking.
    
    Features:
    - Execute 1-50 tools in a single batch
    - Configurable concurrency limit (1-20 parallel executions)
    - Optional stop-on-error behavior
    - Individual tool status tracking
    - Aggregated batch results
    
    The batch execution process:
    1. Validates all tool configurations
    2. Creates batch execution record
    3. Queues batch for execution
    4. Returns batch ID immediately
    5. Executes tools in parallel (background)
    6. Tracks individual tool status
    7. Aggregates results on completion
    
    Args:
        request: Batch execution request with tools and options
        current_user: Currently authenticated user
        batch_executor: Batch executor service
        
    Returns:
        Batch execution response with batch_id for tracking
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks execute permission
        HTTPException 422: If validation fails
        HTTPException 500: If batch cannot be created
        
    Example:
        ```json
        POST /api/v1/batch/execute
        {
            "tools": [
                {
                    "tool_id": "uuid-1",
                    "tool_name": "get_weather",
                    "arguments": {"location": "San Francisco"}
                },
                {
                    "tool_id": "uuid-2",
                    "tool_name": "get_weather",
                    "arguments": {"location": "New York"}
                }
            ],
            "concurrency_limit": 5,
            "stop_on_error": false,
            "execution_options": {
                "timeout": 60,
                "retry_policy": {
                    "max_attempts": 3
                }
            }
        }
        ```
        
    **Validates: Requirements 7.1, 7.4, 7.5**
    """
    try:
        # Convert schema to internal format
        tool_configs = [
            ToolExecutionConfig(
                tool_id=tool.tool_id,
                tool_name=tool.tool_name,
                arguments=tool.arguments
            )
            for tool in request.tools
        ]
        
        batch_request = BatchExecutionRequest(
            tools=tool_configs,
            concurrency_limit=request.concurrency_limit,
            stop_on_error=request.stop_on_error,
            execution_options=request.execution_options
        )
        
        # Execute batch
        batch_execution = await batch_executor.execute_batch(
            batch_request=batch_request,
            user_id=current_user.id
        )
        
        # Convert to response schema
        return BatchExecuteResponse(
            batch_id=str(batch_execution.batch_id),
            user_id=str(batch_execution.user_id),
            total_tools=batch_execution.total_tools,
            completed_tools=batch_execution.completed_tools,
            failed_tools=batch_execution.failed_tools,
            status=batch_execution.status.value,
            stop_on_error=batch_execution.stop_on_error,
            created_at=batch_execution.created_at.isoformat(),
            started_at=batch_execution.started_at.isoformat() if batch_execution.started_at else None,
            completed_at=batch_execution.completed_at.isoformat() if batch_execution.completed_at else None,
            message="Batch execution queued successfully"
        )
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error during batch execution: {str(e)}"
        )


@router.get("/{batch_id}", response_model=BatchStatusResponse)
@require_permission("mcps", "read")
async def get_batch_status(
    batch_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    batch_executor: BatchExecutor = Depends(get_batch_executor)
):
    """
    Get the current status of a batch execution.
    
    Returns comprehensive status information including:
    - Overall batch status (queued, running, completed, failed, cancelled)
    - Progress metrics (total, completed, failed tools)
    - Individual tool statuses with results or errors
    - Execution timing information
    
    This endpoint can be polled to track batch execution progress.
    
    Args:
        batch_id: ID of the batch to query
        current_user: Currently authenticated user
        batch_executor: Batch executor service
        
    Returns:
        Batch status with individual tool statuses
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks read permission
        HTTPException 404: If batch not found
        
    Example:
        ```
        GET /api/v1/batch/{batch_id}
        ```
        
    **Validates: Requirements 7.4, 7.5**
    """
    try:
        batch_status = await batch_executor.get_batch_status(batch_id)
        
        # Convert tool statuses to schema
        tool_statuses = [
            ToolStatusSchema(
                tool_id=tool["tool_id"],
                tool_name=tool["tool_name"],
                execution_id=tool.get("execution_id"),
                status=tool["status"],
                result=tool.get("result"),
                error=tool.get("error"),
                duration_ms=tool.get("duration_ms")
            )
            for tool in batch_status.tool_statuses
        ]
        
        return BatchStatusResponse(
            batch_id=str(batch_status.batch_id),
            status=batch_status.status.value,
            total_tools=batch_status.total_tools,
            completed_tools=batch_status.completed_tools,
            failed_tools=batch_status.failed_tools,
            tool_statuses=tool_statuses
        )
        
    except MCPExecutionError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error retrieving batch status: {str(e)}"
        )


@router.delete("/{batch_id}", status_code=status.HTTP_200_OK)
@require_permission("mcps", "execute")
async def cancel_batch(
    batch_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    batch_executor: BatchExecutor = Depends(get_batch_executor)
):
    """
    Cancel a batch execution.
    
    Cancels all running and queued tools in the batch. Tools that have already
    completed will not be affected. Running tools will continue to completion
    but no new tools will be started.
    
    Note: This cancels the batch coordination but does not force-kill individual
    tool processes that are already running. Those will complete normally.
    
    Args:
        batch_id: ID of the batch to cancel
        current_user: Currently authenticated user
        batch_executor: Batch executor service
        
    Returns:
        Success message
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks execute permission or doesn't own batch
        HTTPException 404: If batch not found
        HTTPException 400: If batch cannot be cancelled (already completed)
        
    Example:
        ```
        DELETE /api/v1/batch/{batch_id}
        ```
    """
    try:
        success = await batch_executor.cancel_batch(
            batch_id=batch_id,
            user_id=current_user.id
        )
        
        if success:
            return {
                "message": "Batch execution cancelled successfully",
                "batch_id": str(batch_id)
            }
        else:
            return {
                "message": "Batch cancellation attempted but may have failed",
                "batch_id": str(batch_id)
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
            detail=f"Unexpected error during batch cancellation: {str(e)}"
        )
