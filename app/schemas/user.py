"""Pydantic schemas for User management"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, ConfigDict, field_validator
import re
from app.models.user import UserRole


class UserBase(BaseModel):
    """Base schema for User with common fields"""
    username: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique username"
    )
    email: EmailStr = Field(..., description="User email address")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format"""
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        if v.startswith('_') or v.startswith('-'):
            raise ValueError('Username cannot start with underscore or hyphen')
        return v


class UserCreate(UserBase):
    """Schema for creating a new user"""
    model_config = ConfigDict(use_enum_values=True)
    
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="User password (min 8 characters)"
    )
    role: Optional[UserRole] = Field(
        default=UserRole.VIEWER,
        description="User role for RBAC"
    )
    
    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v):
        """
        Normalize role value before validation.
        
        Handles case-insensitive role normalization and provides
        helpful error messages for invalid roles.
        
        **Requirements: 5.1, 5.2**
        """
        from app.core.exceptions import RoleValidationError
        from pydantic import ValidationError
        
        if v is None:
            return UserRole.VIEWER
        
        if isinstance(v, str):
            try:
                return UserRole.normalize(v)
            except RoleValidationError as e:
                # Convert to Pydantic ValidationError with helpful message
                raise ValueError(
                    f"Invalid role: '{e.invalid_role}'. Valid options: {e.valid_roles}"
                ) from e
        
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength"""
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        return v


class UserUpdate(BaseModel):
    """Schema for updating an existing user"""
    model_config = ConfigDict(use_enum_values=True)
    
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    
    @field_validator('role', mode='before')
    @classmethod
    def normalize_role(cls, v):
        """
        Normalize role value before validation.
        
        Handles case-insensitive role normalization and provides
        helpful error messages for invalid roles.
        
        **Requirements: 5.1, 5.2**
        """
        from app.core.exceptions import RoleValidationError
        from pydantic import ValidationError
        
        if v is None:
            return None
        
        if isinstance(v, str):
            try:
                return UserRole.normalize(v)
            except RoleValidationError as e:
                # Convert to Pydantic ValidationError with helpful message
                raise ValueError(
                    f"Invalid role: '{e.invalid_role}'. Valid options: {e.valid_roles}"
                ) from e
        
        return v
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        """Validate username format"""
        if v is not None and not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError('Username can only contain letters, numbers, underscores, and hyphens')
        return v
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: Optional[str]) -> Optional[str]:
        """Validate password strength"""
        if v is not None:
            if len(v) < 8:
                raise ValueError('Password must be at least 8 characters long')
            if not re.search(r'[A-Z]', v):
                raise ValueError('Password must contain at least one uppercase letter')
            if not re.search(r'[a-z]', v):
                raise ValueError('Password must contain at least one lowercase letter')
            if not re.search(r'[0-9]', v):
                raise ValueError('Password must contain at least one digit')
        return v


class User(UserBase):
    """Schema for user response (excludes password)"""
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,  # Serialize enums as their string values (lowercase)
        json_encoders={
            UserRole: lambda v: v.value  # Ensure lowercase serialization
        }
    )
    
    id: UUID
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
