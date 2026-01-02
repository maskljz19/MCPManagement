"""Pydantic schemas for MCP Tool management"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
import re
from app.models.mcp_tool import ToolStatus


class MCPToolBase(BaseModel):
    """Base schema for MCP Tool with common fields"""
    name: str = Field(..., min_length=1, max_length=255, description="Tool name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r'^[a-z0-9-]+$',
        description="URL-friendly slug (lowercase, numbers, hyphens only)"
    )
    description: Optional[str] = Field(None, description="Tool description")
    version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Semantic version (e.g., 1.0.0)"
    )
    
    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """Validate slug format"""
        if not re.match(r'^[a-z0-9-]+$', v):
            raise ValueError('Slug must contain only lowercase letters, numbers, and hyphens')
        if v.startswith('-') or v.endswith('-'):
            raise ValueError('Slug cannot start or end with a hyphen')
        if '--' in v:
            raise ValueError('Slug cannot contain consecutive hyphens')
        return v
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate semantic version format"""
        if not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning (e.g., 1.0.0)')
        parts = v.split('.')
        if any(int(part) < 0 for part in parts):
            raise ValueError('Version numbers must be non-negative')
        return v


class MCPToolCreate(MCPToolBase):
    """Schema for creating a new MCP tool"""
    config: Dict[str, Any] = Field(
        ...,
        description="MCP configuration object"
    )
    # author_id is automatically set from the authenticated user, not provided by client
    status: Optional[ToolStatus] = Field(
        default=ToolStatus.DRAFT,
        description="Initial tool status"
    )


class MCPToolUpdate(BaseModel):
    """Schema for updating an existing MCP tool"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(None, pattern=r'^\d+\.\d+\.\d+$')
    config: Optional[Dict[str, Any]] = None
    status: Optional[ToolStatus] = None
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v: Optional[str]) -> Optional[str]:
        """Validate semantic version format"""
        if v is not None and not re.match(r'^\d+\.\d+\.\d+$', v):
            raise ValueError('Version must follow semantic versioning (e.g., 1.0.0)')
        return v


class MCPTool(MCPToolBase):
    """Schema for MCP tool response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    author_id: UUID
    status: ToolStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None


class MCPToolVersion(BaseModel):
    """Schema for MCP tool version history entry"""
    tool_id: UUID
    version: str
    config: Dict[str, Any]
    changed_by: UUID
    changed_at: datetime
    change_type: str = Field(..., pattern=r'^(create|update|delete)$')
    diff: Optional[Dict[str, Any]] = None
