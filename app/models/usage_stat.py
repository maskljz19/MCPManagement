"""MCP Usage Statistics model"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, TIMESTAMP, ForeignKey, Index, BigInteger
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class MCPUsageStatModel(BaseModel):
    """
    MCP Usage Statistics model for tracking API usage.
    
    Records each API request to MCP tools with performance metrics.
    Uses auto-incrementing BIGINT for high-volume data.
    """
    __tablename__ = "mcp_usage_stats"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tool_id = Column(
        CHAR(36),
        ForeignKey("mcp_tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    deployment_id = Column(CHAR(36), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    method = Column(String(10), nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Integer, nullable=False)
    user_id = Column(CHAR(36), nullable=True)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    tool = relationship("MCPToolModel", back_populates="usage_stats")
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_stats_tool_timestamp', 'tool_id', 'timestamp'),
        Index('idx_usage_stats_deployment', 'deployment_id'),
    )
    
    def __repr__(self) -> str:
        return f"<MCPUsageStatModel(id={self.id}, tool_id={self.tool_id}, endpoint={self.endpoint})>"
