"""Pydantic schemas for Knowledge Base service"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class DocumentBase(BaseModel):
    """Base schema for documents"""
    title: str = Field(..., min_length=1, max_length=500, description="Document title")
    content: str = Field(..., min_length=1, description="Document content")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (source, author, tags, etc.)"
    )


class DocumentCreate(DocumentBase):
    """Schema for creating a new document"""
    pass


class DocumentUpdate(BaseModel):
    """Schema for updating an existing document"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    content: Optional[str] = Field(None, min_length=1)
    metadata: Optional[Dict[str, Any]] = None


class Document(DocumentBase):
    """Schema for document response"""
    model_config = ConfigDict(from_attributes=True)
    
    document_id: UUID
    embedding_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class SearchQuery(BaseModel):
    """Schema for semantic search query"""
    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100, description="Maximum number of results")
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata filters for search results"
    )
    min_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )


class SearchResult(BaseModel):
    """Schema for search result"""
    document_id: UUID
    title: str
    content_snippet: str = Field(..., description="Excerpt from document content")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('content_snippet')
    @classmethod
    def validate_snippet_length(cls, v: str) -> str:
        """Ensure snippet is not too long"""
        max_length = 500
        if len(v) > max_length:
            return v[:max_length] + "..."
        return v
