"""Pydantic schemas for API Key management"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class APIKeyBase(BaseModel):
    """Base schema for API Key"""
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Descriptive name for the API key"
    )


class APIKeyCreate(APIKeyBase):
    """Schema for creating a new API key"""
    expires_at: Optional[datetime] = Field(
        None,
        description="Optional expiration timestamp"
    )
    
    @field_validator('expires_at')
    @classmethod
    def validate_expiry_future(cls, v: Optional[datetime]) -> Optional[datetime]:
        """Ensure expiry is in the future"""
        if v is not None and v < datetime.utcnow():
            raise ValueError('Expiration date must be in the future')
        return v


class APIKey(APIKeyBase):
    """Schema for API key response (without the actual key)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: UUID
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    @property
    def is_valid(self) -> bool:
        """Check if the API key is valid"""
        if self.revoked_at is not None:
            return False
        if self.expires_at is not None and self.expires_at < datetime.utcnow():
            return False
        return True


class APIKeyResponse(APIKey):
    """Schema for API key creation response (includes the actual key once)"""
    key: str = Field(..., description="The actual API key (only shown once at creation)")
