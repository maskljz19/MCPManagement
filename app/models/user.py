"""User model"""

import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Enum, TIMESTAMP, Index
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import relationship
from passlib.context import CryptContext
from app.models.base import BaseModel

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserRole(str, enum.Enum):
    """User role for RBAC"""
    ADMIN = "admin"
    DEVELOPER = "developer"
    VIEWER = "viewer"


class UserModel(BaseModel):
    """
    User model for authentication and authorization.
    
    Stores user credentials with bcrypt password hashing.
    Implements role-based access control (RBAC).
    """
    __tablename__ = "users"
    
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole),
        default=UserRole.VIEWER,
        nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    api_keys = relationship(
        "APIKeyModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    github_connections = relationship(
        "GitHubConnectionModel",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index('idx_users_username', 'username'),
        Index('idx_users_email', 'email'),
    )
    
    def set_password(self, password: str) -> None:
        """Hash and set the user's password"""
        self.password_hash = pwd_context.hash(password)
    
    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash"""
        return pwd_context.verify(password, self.password_hash)
    
    def __repr__(self) -> str:
        return f"<UserModel(id={self.id}, username={self.username}, role={self.role})>"
