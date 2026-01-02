"""MCP Deployment model"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Enum, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class DeploymentStatus(str, enum.Enum):
    """Status of an MCP deployment"""
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class HealthStatus(str, enum.Enum):
    """Health status of a deployment"""
    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class MCPDeploymentModel(BaseModel):
    """
    MCP Deployment model representing a deployed MCP server instance.
    
    Tracks deployment lifecycle, endpoint URLs, and health status.
    """
    __tablename__ = "mcp_deployments"
    
    tool_id = Column(
        CHAR(36),
        ForeignKey("mcp_tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    endpoint_url = Column(String(512), nullable=False)
    status = Column(
        Enum(DeploymentStatus),
        default=DeploymentStatus.STARTING,
        nullable=False,
        index=True
    )
    health_status = Column(
        Enum(HealthStatus),
        default=HealthStatus.UNKNOWN,
        nullable=False
    )
    last_health_check = Column(TIMESTAMP, nullable=True)
    deployed_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    stopped_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    tool = relationship("MCPToolModel", back_populates="deployments")
    
    # Indexes
    __table_args__ = (
        Index('idx_mcp_deployments_tool', 'tool_id'),
        Index('idx_mcp_deployments_status', 'status'),
    )
    
    def __repr__(self) -> str:
        return f"<MCPDeploymentModel(id={self.id}, tool_id={self.tool_id}, status={self.status})>"
