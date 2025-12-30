"""Knowledge Base API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from uuid import UUID
from typing import List

from app.core.database import get_mongodb, get_redis
from app.core.config import settings
from app.services.knowledge_service import KnowledgeBaseService
from app.schemas.knowledge import (
    DocumentCreate,
    Document,
    SearchQuery,
    SearchResult
)
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission


router = APIRouter(prefix="/knowledge", tags=["Knowledge Base"])


async def get_knowledge_service(
    redis: Redis = Depends(get_redis)
) -> KnowledgeBaseService:
    """Dependency to get KnowledgeBaseService instance"""
    mongo = get_mongodb()
    
    return KnowledgeBaseService(
        mongo_db=mongo,
        redis=redis,
        openai_api_key=settings.OPENAI_API_KEY
    )


@router.post("/documents", response_model=Document, status_code=status.HTTP_201_CREATED)
@require_permission("knowledge", "create")
async def upload_document(
    doc_data: DocumentCreate,
    current_user: UserModel = Depends(get_current_user),
    knowledge_service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Upload a new document to the knowledge base.
    
    Stores the document in MongoDB for later retrieval and text search.
    
    Args:
        doc_data: Document creation data (title, content, metadata)
        current_user: Currently authenticated user
        knowledge_service: Knowledge Base service
        
    Returns:
        Created document object with IDs
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks permission
        HTTPException 422: If validation fails
        HTTPException 500: If storage fails
    """
    try:
        document = await knowledge_service.store_document(doc_data)
        return document
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to store document: {str(e)}"
        )


@router.get("/documents/{doc_id}", response_model=Document)
@require_permission("knowledge", "read")
async def get_document(
    doc_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    knowledge_service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Get document details by ID.
    
    Retrieves a specific document from MongoDB by its unique identifier.
    
    Args:
        doc_id: Document unique identifier
        current_user: Currently authenticated user
        knowledge_service: Knowledge Base service
        
    Returns:
        Document object with full content
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks permission
        HTTPException 404: If document not found
    """
    document = await knowledge_service.get_document(doc_id)
    
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found"
        )
    
    return document


@router.delete("/documents/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_permission("knowledge", "delete")
async def delete_document(
    doc_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    knowledge_service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Delete a document from the knowledge base.
    
    Removes the document from MongoDB.
    
    Args:
        doc_id: Document unique identifier
        current_user: Currently authenticated user
        knowledge_service: Knowledge Base service
        
    Returns:
        No content (204)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks permission
        HTTPException 404: If document not found
    """
    deleted = await knowledge_service.delete_document(doc_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{doc_id}' not found"
        )
    
    return None


@router.post("/search", response_model=List[SearchResult])
@require_permission("knowledge", "read")
async def search_documents(
    query: SearchQuery,
    current_user: UserModel = Depends(get_current_user),
    knowledge_service: KnowledgeBaseService = Depends(get_knowledge_service)
):
    """
    Perform text search on the knowledge base.
    
    Searches for documents matching the query text using MongoDB text search.
    Results are ordered by relevance.
    
    Note: Semantic search has been disabled due to hardware limitations.
    
    Args:
        query: Search query with parameters (query text, limit, filters)
        current_user: Currently authenticated user
        knowledge_service: Knowledge Base service
        
    Returns:
        List of search results ordered by relevance
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 403: If user lacks permission
        HTTPException 422: If validation fails
    """
    try:
        results = await knowledge_service.search_documents(query)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )
