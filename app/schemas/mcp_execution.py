"""Pydantic schemas for MCP Tool execution"""

from datetime import datetime
from typing import Dict, Any, Optional, Literal, List
from uuid import UUID
from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    """Configuration for execution retry behavior"""
    max_attempts: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum number of retry attempts (1-10)"
    )
    initial_delay_seconds: float = Field(
        default=1.0,
        ge=0.1,
        le=60.0,
        description="Initial delay before first retry in seconds (0.1-60)"
    )
    max_delay_seconds: float = Field(
        default=60.0,
        ge=1.0,
        le=300.0,
        description="Maximum delay between retries in seconds (1-300)"
    )
    backoff_multiplier: float = Field(
        default=2.0,
        ge=1.0,
        le=10.0,
        description="Multiplier for exponential backoff (1-10)"
    )
    retryable_errors: List[str] = Field(
        default_factory=lambda: [
            "timeout",
            "connection_error",
            "temporary_failure",
            "rate_limit_exceeded",
            "server_error"
        ],
        description="List of error types that should trigger retry"
    )


class ExecutionOptions(BaseModel):
    """Options for execution configuration"""
    mode: Literal["sync", "async"] = Field(
        default="sync",
        description="Execution mode: sync returns result immediately, async returns execution ID"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=3600,
        description="Execution timeout in seconds (1-3600)"
    )
    retry_policy: Optional[RetryPolicy] = Field(
        default=None,
        description="Retry policy for failed executions"
    )
    priority: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Execution priority (1=lowest, 10=highest)"
    )
    cache_enabled: bool = Field(
        default=True,
        description="Whether to use result caching"
    )
    notify_on_completion: bool = Field(
        default=False,
        description="Send notification when execution completes"
    )
    notification_channels: List[str] = Field(
        default_factory=list,
        description="Channels for notifications (e.g., 'websocket', 'email')"
    )


class MCPToolExecuteRequest(BaseModel):
    """Schema for executing an MCP tool"""
    tool_name: str = Field(
        ...,
        description="Name of the specific tool to execute within the MCP server"
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments to pass to the tool"
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Execution timeout in seconds (1-300)"
    )
    options: Optional[ExecutionOptions] = Field(
        default=None,
        description="Advanced execution options"
    )


class MCPToolExecuteResponse(BaseModel):
    """Schema for MCP tool execution response"""
    execution_id: str = Field(..., description="Unique execution ID")
    tool_id: str = Field(..., description="ID of the executed tool")
    tool_name: str = Field(..., description="Name of the executed tool")
    status: str = Field(..., description="Execution status (success/error)")
    result: Dict[str, Any] = Field(..., description="Tool execution result")
    executed_at: str = Field(..., description="Execution timestamp (ISO format)")


class AsyncExecutionResponse(BaseModel):
    """Schema for async execution response"""
    execution_id: str = Field(..., description="Unique execution ID for tracking")
    tool_id: str = Field(..., description="ID of the tool being executed")
    tool_name: str = Field(..., description="Name of the tool being executed")
    status: str = Field(..., description="Initial status (typically 'queued' or 'running')")
    queued_at: str = Field(..., description="Timestamp when execution was queued (ISO format)")
    message: str = Field(
        default="Execution queued successfully",
        description="Status message"
    )


class ExecutionStatus(BaseModel):
    """Schema for execution status query response"""
    execution_id: str = Field(..., description="Unique execution ID")
    tool_id: str = Field(..., description="ID of the executed tool")
    tool_name: str = Field(..., description="Name of the executed tool")
    user_id: str = Field(..., description="ID of the user who initiated execution")
    status: str = Field(
        ...,
        description="Current status: queued, running, success, error, cancelled, timeout"
    )
    progress: Optional[int] = Field(
        None,
        ge=0,
        le=100,
        description="Progress percentage (0-100) if available"
    )
    queued_at: Optional[str] = Field(None, description="When execution was queued")
    started_at: Optional[str] = Field(None, description="When execution started")
    completed_at: Optional[str] = Field(None, description="When execution completed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    retry_count: Optional[int] = Field(
        None,
        description="Number of retry attempts made"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional execution metadata"
    )


class MCPExecutionLog(BaseModel):
    """Schema for MCP execution log entry"""
    id: str = Field(..., alias="_id", description="Log entry ID")
    tool_id: str
    user_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Dict[str, Any]] = None
    status: str
    start_time: datetime
    end_time: datetime
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    error: Optional[str] = None
    
    class Config:
        populate_by_name = True
