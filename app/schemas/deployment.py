"""Pydantic schemas for MCP Deployment management"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, HttpUrl
from app.models.deployment import DeploymentStatus, HealthStatus


class DeploymentConfig(BaseModel):
    """Configuration for deploying an MCP server"""
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the deployment"
    )
    port: Optional[int] = Field(
        None,
        ge=1024,
        le=65535,
        description="Port to bind the server to (auto-assigned if not provided)"
    )
    resources: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Resource limits (memory, CPU)"
    )


class DeploymentCreate(BaseModel):
    """Schema for creating a new deployment"""
    tool_id: UUID = Field(..., description="ID of the MCP tool to deploy")
    config: DeploymentConfig = Field(
        default_factory=DeploymentConfig,
        description="Deployment configuration"
    )


class Deployment(BaseModel):
    """Schema for deployment response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tool_id: UUID
    endpoint_url: str
    status: DeploymentStatus
    health_status: HealthStatus
    last_health_check: Optional[datetime] = None
    deployed_at: datetime
    stopped_at: Optional[datetime] = None


class HealthCheckResult(BaseModel):
    """Schema for health check result"""
    deployment_id: UUID
    status: HealthStatus
    checked_at: datetime
    details: Optional[Dict[str, Any]] = None
