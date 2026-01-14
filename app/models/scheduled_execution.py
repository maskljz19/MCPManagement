"""Scheduled Execution Model"""

from sqlalchemy import Column, String, Boolean, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.models.base import Base


class ScheduledExecutionModel(Base):
    """
    Scheduled Executions table for managing recurring tool executions.
    
    Stores scheduled execution configurations with cron-like expressions.
    """
    __tablename__ = "scheduled_executions"
    
    id = Column(CHAR(36), primary_key=True)
    tool_id = Column(CHAR(36), ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tool_name = Column(String(255), nullable=False)
    arguments = Column(JSON, nullable=False)
    schedule_expression = Column(String(255), nullable=False)
    next_execution_at = Column(TIMESTAMP, nullable=False)
    last_execution_at = Column(TIMESTAMP, nullable=True)
    last_execution_status = Column(String(50), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(TIMESTAMP, nullable=False)
    
    # Relationships
    tool = relationship("MCPToolModel", back_populates="scheduled_executions")
    user = relationship("UserModel", back_populates="scheduled_executions")
