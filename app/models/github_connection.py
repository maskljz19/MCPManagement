"""GitHub Connection model"""

from datetime import datetime
from sqlalchemy import Column, String, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from app.models.base import BaseModel


class GitHubConnectionModel(BaseModel):
    """
    GitHub Connection model for repository integration.
    
    Stores GitHub repository connection details and sync status.
    """
    __tablename__ = "github_connections"
    
    user_id = Column(
        CHAR(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    tool_id = Column(
        CHAR(36),
        ForeignKey("mcp_tools.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    repository_url = Column(String(512), nullable=False)
    last_sync_sha = Column(String(40), nullable=True)
    last_sync_at = Column(TIMESTAMP, nullable=True)
    
    # Relationships
    user = relationship("UserModel", back_populates="github_connections")
    
    # Indexes
    __table_args__ = (
        Index('idx_tool', 'tool_id'),
    )
    
    def __repr__(self) -> str:
        return f"<GitHubConnectionModel(id={self.id}, repository_url={self.repository_url})>"
