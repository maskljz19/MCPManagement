"""Resource Quota Model"""

from sqlalchemy import Column, Float, Integer, TIMESTAMP, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship

from app.models.base import Base


class ResourceQuotaModel(Base):
    """
    Resource Quotas table for managing user execution limits.
    
    Defines resource limits per user including CPU, memory, and concurrency.
    """
    __tablename__ = "resource_quotas"
    
    id = Column(CHAR(36), primary_key=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    max_cpu_cores = Column(Float, nullable=False, default=4.0, server_default="4.0")
    max_memory_mb = Column(Integer, nullable=False, default=4096, server_default="4096")
    max_concurrent_executions = Column(Integer, nullable=False, default=5, server_default="5")
    max_daily_executions = Column(Integer, nullable=False, default=1000, server_default="1000")
    created_at = Column(TIMESTAMP, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False)
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', name='uk_user'),
    )
    
    # Relationships
    user = relationship("UserModel", back_populates="resource_quota", uselist=False)
