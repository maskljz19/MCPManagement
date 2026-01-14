"""Execution Cost Model"""

from sqlalchemy import Column, String, Integer, Float, BigInteger, DECIMAL, TIMESTAMP, ForeignKey
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.models.base import Base


class ExecutionCostModel(Base):
    """
    Execution Costs table for tracking resource usage and billing.
    
    Records cost calculations for each execution based on duration and resources.
    """
    __tablename__ = "execution_costs"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    execution_id = Column(CHAR(36), nullable=False)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tool_id = Column(CHAR(36), ForeignKey("mcp_tools.id", ondelete="CASCADE"), nullable=False)
    cost_amount = Column(DECIMAL(10, 4), nullable=False)
    currency = Column(String(3), nullable=False, default="USD", server_default="USD")
    duration_seconds = Column(Float, nullable=False)
    cpu_cores = Column(Float, nullable=False)
    memory_mb = Column(Integer, nullable=False)
    calculated_at = Column(TIMESTAMP, nullable=False)
    
    # Relationships
    user = relationship("UserModel", back_populates="execution_costs")
    tool = relationship("MCPToolModel", back_populates="execution_costs")
