"""Base model with common fields"""

from datetime import datetime
from sqlalchemy import Column, TIMESTAMP
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()


class BaseModel(Base):
    """
    Abstract base model with common fields for all tables.
    
    Provides:
    - id: UUID primary key
    - created_at: Timestamp of creation
    - updated_at: Timestamp of last update
    """
    __abstract__ = True
    
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        TIMESTAMP,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
