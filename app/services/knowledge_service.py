"""Knowledge Base Service - Document storage and management

Note: Vector search functionality has been removed due to hardware limitations.
This service now only handles document storage and retrieval in MongoDB.
"""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.schemas.knowledge import (
    DocumentCreate,
    DocumentUpdate,
    Document,
    SearchResult,
    SearchQuery
)


class KnowledgeBaseService:
    """
    Knowledge Base Service handles document storage and retrieval.
    
    Note: Vector search and embedding generation have been removed due to hardware limitations.
    
    Responsibilities:
    - Store and retrieve documents in MongoDB
    - Basic text search using MongoDB text indexes
    - Maintain document metadata
    """
    
    def __init__(
        self,
        mongo_db: AsyncIOMotorDatabase,
        redis: Redis,
        openai_api_key: Optional[str] = None
    ):
        self.mongo = mongo_db
        self.redis = redis
        self.documents_collection = mongo_db["knowledge_base"]
    
    # ========================================================================
    # Document Storage Operations
    # ========================================================================
    
    async def store_document(self, doc_data: DocumentCreate) -> Document:
        """
        Store a document in MongoDB.
        
        Args:
            doc_data: Document creation data
            
        Returns:
            Created document with IDs
            
        Raises:
            RuntimeError: If storage fails
        """
        document_id = uuid4()
        now = datetime.utcnow()
        
        # Prepare document for MongoDB
        mongo_document = {
            "document_id": str(document_id),
            "title": doc_data.title,
            "content": doc_data.content,
            "metadata": doc_data.metadata,
            "created_at": now,
            "updated_at": now
        }
        
        try:
            # Store in MongoDB
            await self.documents_collection.insert_one(mongo_document)
            
            # Return document
            return Document(
                document_id=document_id,
                title=doc_data.title,
                content=doc_data.content,
                metadata=doc_data.metadata,
                embedding_id=None,  # No embeddings generated
                created_at=now,
                updated_at=now
            )
            
        except Exception as e:
            # Rollback: try to clean up if partial storage occurred
            try:
                await self.documents_collection.delete_one(
                    {"document_id": str(document_id)}
                )
            except:
                pass  # Best effort cleanup
            
            raise RuntimeError(f"Failed to store document: {e}")
    
    async def get_document(self, doc_id: UUID) -> Optional[Document]:
        """
        Retrieve a document from MongoDB by ID.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document if found, None otherwise
        """
        mongo_doc = await self.documents_collection.find_one(
            {"document_id": str(doc_id)}
        )
        
        if not mongo_doc:
            return None
        
        return Document(
            document_id=UUID(mongo_doc["document_id"]),
            title=mongo_doc["title"],
            content=mongo_doc["content"],
            metadata=mongo_doc.get("metadata", {}),
            embedding_id=UUID(mongo_doc["embedding_id"]) if mongo_doc.get("embedding_id") else None,
            created_at=mongo_doc["created_at"],
            updated_at=mongo_doc["updated_at"]
        )
    
    async def delete_document(self, doc_id: UUID) -> bool:
        """
        Delete a document from MongoDB.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Delete from MongoDB
        result = await self.documents_collection.delete_one(
            {"document_id": str(doc_id)}
        )
        
        return result.deleted_count > 0
    
    # ========================================================================
    # Search Operations
    # ========================================================================
    
    async def search_documents(
        self,
        query: SearchQuery
    ) -> List[SearchResult]:
        """
        Perform basic text search using MongoDB.
        
        Note: This is a simple text-based search. Semantic search has been
        removed due to hardware limitations (no vector database available).
        
        Args:
            query: Search query with parameters
            
        Returns:
            List of search results ordered by relevance
        """
        # Build MongoDB query
        mongo_query = {
            "$or": [
                {"title": {"$regex": query.query, "$options": "i"}},
                {"content": {"$regex": query.query, "$options": "i"}}
            ]
        }
        
        # Add metadata filters if provided
        if query.filters:
            for key, value in query.filters.items():
                mongo_query[f"metadata.{key}"] = value
        
        # Execute search
        cursor = self.documents_collection.find(mongo_query).limit(query.limit)
        
        # Build results
        results = []
        async for mongo_doc in cursor:
            document_id = UUID(mongo_doc["document_id"])
            
            # Create content snippet (first 500 chars)
            content = mongo_doc["content"]
            snippet = content[:500] + "..." if len(content) > 500 else content
            
            results.append(SearchResult(
                document_id=document_id,
                title=mongo_doc["title"],
                content_snippet=snippet,
                similarity_score=0.0,  # No similarity scoring without vector search
                metadata=mongo_doc.get("metadata", {})
            ))
        
        return results
