"""Pydantic schemas for Authentication"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from app.models.user import UserRole


class LoginRequest(BaseModel):
    """Schema for user login request"""
    username: str = Field(..., min_length=1, description="Username or email")
    password: str = Field(..., min_length=1, description="User password")


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry time in seconds")


class TokenPayload(BaseModel):
    """Schema for JWT token payload"""
    sub: UUID = Field(..., description="Subject (user ID)")
    user_id: UUID = Field(..., description="User ID")
    username: str = Field(..., description="Username")
    role: UserRole = Field(..., description="User role")
    permissions: List[str] = Field(default_factory=list, description="User permissions")
    exp: datetime = Field(..., description="Expiration timestamp")
    iat: datetime = Field(..., description="Issued at timestamp")
    jti: Optional[str] = Field(None, description="JWT ID for tracking")
    
    @field_validator('exp')
    @classmethod
    def validate_expiry(cls, v: datetime) -> datetime:
        """Ensure expiry is in the future"""
        if v < datetime.utcnow():
            raise ValueError('Token expiry must be in the future')
        return v


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str = Field(..., description="Refresh token to exchange for new access token")
