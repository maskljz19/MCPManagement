"""API Key model"""

from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class APIKeyModel(BaseModel):
    """
    API Key model for API key authentication.
    
    Stores hashed API keys for secure authentication.
    Supports expiration and revocation.
    """
    __tablename__ = "api_keys"
    
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    key_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    last_used_at = Column(TIMESTAMP, nullable=True)
    expires_at = Column(TIMESTAMP, nullable=True)
    revoked_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_keys_user', 'user_id'),
    )
    
    def is_valid(self) -> bool:
        """Check if the API key is valid (not expired or revoked)"""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        return True
    
    def __repr__(self) -> str:
        return f"<APIKeyModel(id={self.id}, name={self.name}, user_id={self.user_id})>"
