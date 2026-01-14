"""Execution Queue Model"""

from sqlalchemy import Column, String, Integer, JSON, Enum, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class QueueStatus(str, enum.Enum):
    """Execution queue status enumeration"""
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionQueueModel(Base):
    """
    Execution Queue table for managing MCP tool execution requests.
    
    Stores queued execution requests with priority ordering and status tracking.
    """
    __tablename__ = "execution_queue"
    
    id = Column(CHAR(36), primary_key=True)
    tool_id = Column(CHAR(36), ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(255), nullable=False)
    arguments = Column(JSON, nullable=False)
    options = Column(JSON, nullable=False)
    priority = Column(Integer, nullable=False)
    status = Column(
        Enum(QueueStatus),
        nullable=False,
        default=QueueStatus.QUEUED,
        server_default="queued"
    )
    queue_position = Column(Integer, nullable=True)
    estimated_wait_seconds = Column(Integer, nullable=True)
    queued_at = Column(TIMESTAMP, nullable=False)
    started_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    tool = relationship("MCPToolModel", back_populates="execution_queue")
    user = relationship("UserModel", back_populates="execution_queue")
