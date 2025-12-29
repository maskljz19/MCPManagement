"""GitHub Integration Schemas"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class GitHubConnectionCreate(BaseModel):
    """Schema for creating a GitHub connection"""
    repository_url: str = Field(
        ...,
        description="GitHub repository URL (HTTPS or SSH format)",
        examples=["https://github.com/owner/repo"]
    )
    access_token: str = Field(
        ...,
        description="GitHub personal access token",
        min_length=1
    )
    tool_id: Optional[UUID] = Field(
        None,
        description="Optional MCP tool to associate with this repository"
    )


class GitHubConnection(BaseModel):
    """Schema for GitHub connection response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    tool_id: Optional[UUID]
    repository_url: str
    last_sync_sha: Optional[str]
    last_sync_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class SyncTriggerResponse(BaseModel):
    """Schema for sync trigger response"""
    task_id: str = Field(..., description="Celery task identifier")
    status: str = Field(..., description="Task status")
    connection_id: str = Field(..., description="GitHub connection identifier")


class WebhookEvent(BaseModel):
    """Schema for GitHub webhook event"""
    event_type: str = Field(..., description="GitHub event type")
    payload: Dict[str, Any] = Field(..., description="Webhook payload")


class WebhookProcessResponse(BaseModel):
    """Schema for webhook processing response"""
    status: str = Field(..., description="Processing status")
    webhook_id: Optional[str] = Field(None, description="Webhook document ID")
    connection_id: Optional[str] = Field(None, description="GitHub connection ID")
    reason: Optional[str] = Field(None, description="Reason if ignored")


class SyncResult(BaseModel):
    """Schema for repository sync result"""
    connection_id: str
    status: str
    message: str
    files_updated: int
    last_sync_sha: Optional[str] = None
