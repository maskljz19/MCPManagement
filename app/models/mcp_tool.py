"""MCP Tool model"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Text, Enum, TIMESTAMP, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class ToolStatus(str, enum.Enum):
    """Status of an MCP tool"""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DEPRECATED = "DEPRECATED"


class MCPToolModel(BaseModel):
    """
    MCP Tool model representing a Model Context Protocol tool.
    
    Stores tool metadata in MySQL with relationships to deployments and usage stats.
    Full configuration history is stored in MongoDB.
    """
    __tablename__ = "mcp_tools"
    
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False)
    author_id = Column(CHAR(36), nullable=False, index=True)
    status = Column(
        Enum(ToolStatus),
        default=ToolStatus.DRAFT,
        nullable=False,
        index=True
    )
    deleted_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    deployments = relationship(
        "MCPDeploymentModel",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    usage_stats = relationship(
        "MCPUsageStatModel",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    execution_queue = relationship(
        "ExecutionQueueModel",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    scheduled_executions = relationship(
        "ScheduledExecutionModel",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    execution_costs = relationship(
        "ExecutionCostModel",
        back_populates="tool",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_mcp_tools_slug', 'slug'),
        Index('idx_mcp_tools_author', 'author_id'),
        Index('idx_mcp_tools_status', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<MCPToolModel(id={self.id}, name={self.name}, slug={self.slug})>"
