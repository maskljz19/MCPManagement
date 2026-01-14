"""Batch Execution Model"""

from sqlalchemy import Column, Integer, Boolean, Enum, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class BatchStatus(str, enum.Enum):
    """Batch execution status enumeration"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BatchExecutionModel(Base):
    """
    Batch Executions table for managing multiple tool executions.
    
    Tracks batch execution requests with aggregated status and progress.
    """
    __tablename__ = "batch_executions"
    
    id = Column(CHAR(36), primary_key=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    total_tools = Column(Integer, nullable=False)
    completed_tools = Column(Integer, nullable=False, default=0, server_default="0")
    failed_tools = Column(Integer, nullable=False, default=0, server_default="0")
    status = Column(
        Enum(BatchStatus),
        nullable=False,
        default=BatchStatus.QUEUED,
        server_default="queued"
    )
    stop_on_error = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(TIMESTAMP, nullable=False)
    started_at = Column(TIMESTAMP, nullable=True)
    completed_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="batch_executions")
