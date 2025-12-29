"""Common Pydantic schemas used across the application"""

from datetime import datetime
from typing import Generic, TypeVar, List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


T = TypeVar('T')


class Pagination(BaseModel):
    """Schema for pagination parameters"""
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of items per page"
    )
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Get limit for database queries"""
        return self.page_size


class Page(BaseModel, Generic[T]):
    """Schema for paginated response"""
    items: List[T] = Field(..., description="List of items for current page")
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @field_validator('total_pages')
    @classmethod
    def validate_total_pages(cls, v: int, info) -> int:
        """Ensure total_pages is consistent with total and page_size"""
        if 'total' in info.data and 'page_size' in info.data:
            expected_pages = (info.data['total'] + info.data['page_size'] - 1) // info.data['page_size']
            if v != expected_pages:
                raise ValueError(f'total_pages should be {expected_pages} based on total and page_size')
        return v


class ErrorDetail(BaseModel):
    """Schema for error detail"""
    field: Optional[str] = Field(None, description="Field that caused the error")
    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(None, description="Error type")


class ErrorResponse(BaseModel):
    """Schema for error response"""
    code: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional error details"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    errors: Optional[List[ErrorDetail]] = Field(
        None,
        description="Field-level validation errors"
    )


class HealthCheck(BaseModel):
    """Schema for health check response"""
    status: str = Field(..., pattern=r'^(healthy|unhealthy|degraded)$')
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    checks: Dict[str, bool] = Field(
        default_factory=dict,
        description="Status of individual service checks"
    )
    version: Optional[str] = Field(None, description="Application version")
