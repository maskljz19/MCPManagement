"""Knowledge Base Service - Document storage, embedding generation, and semantic search"""

import json
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
from langchain_openai import OpenAIEmbeddings
from redis.asyncio import Redis

from app.schemas.knowledge import (
    DocumentCreate,
    DocumentUpdate,
    Document,
    SearchResult,
    SearchQuery
)
from app.core.database import QDRANT_COLLECTION_NAME, EMBEDDING_DIMENSION


class KnowledgeBaseService:
    """
    Knowledge Base Service handles document storage, embedding generation, and semantic search.
    
    Responsibilities:
    - Store and retrieve documents in MongoDB
    - Generate embeddings using LangChain + OpenAI
    - Store and search vectors in Qdrant
    - Maintain consistency between MongoDB and Qdrant
    """
    
    def __init__(
        self,
        mongo_db: AsyncIOMotorDatabase,
        qdrant_client: QdrantClient,
        redis: Redis,
        openai_api_key: str
    ):
        self.mongo = mongo_db
        self.qdrant = qdrant_client
        self.redis = redis
        self.documents_collection = mongo_db["knowledge_base"]
        
        # Initialize OpenAI embeddings via LangChain
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=openai_api_key,
            model="text-embedding-3-small",  # 1536 dimensions
            chunk_size=1000  # Batch size for embedding generation
        )
    
    # ========================================================================
    # Document Storage Operations
    # ========================================================================
    
    async def store_document(self, doc_data: DocumentCreate) -> Document:
        """
        Store a document in MongoDB and generate embeddings in Qdrant.
        
        This implements dual-store consistency: both MongoDB and Qdrant
        must contain the document for it to be considered successfully stored.
        
        Args:
            doc_data: Document creation data
            
        Returns:
            Created document with IDs
            
        Raises:
            RuntimeError: If storage fails in either database
        """
        document_id = uuid4()
        embedding_id = uuid4()
        now = datetime.utcnow()
        
        # Prepare document for MongoDB
        mongo_document = {
            "document_id": str(document_id),
            "title": doc_data.title,
            "content": doc_data.content,
            "metadata": doc_data.metadata,
            "embedding_id": str(embedding_id),
            "created_at": now,
            "updated_at": now
        }
        
        try:
            # Store in MongoDB first
            await self.documents_collection.insert_one(mongo_document)
            
            # Generate embedding for the content
            embedding_vector = await self.generate_embeddings(doc_data.content)
            
            # Store in Qdrant
            await self._store_vector(
                embedding_id=embedding_id,
                document_id=document_id,
                vector=embedding_vector,
                title=doc_data.title,
                metadata=doc_data.metadata
            )
            
            # Return document
            return Document(
                document_id=document_id,
                title=doc_data.title,
                content=doc_data.content,
                metadata=doc_data.metadata,
                embedding_id=embedding_id,
                created_at=now,
                updated_at=now
            )
            
        except Exception as e:
            # Rollback: try to clean up if partial storage occurred
            try:
                await self.documents_collection.delete_one(
                    {"document_id": str(document_id)}
                )
                await self._delete_vector(embedding_id)
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
        Delete a document from both MongoDB and Qdrant.
        
        This maintains dual-store consistency by removing from both databases.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            True if deleted, False if not found
        """
        # Get document to find embedding_id
        mongo_doc = await self.documents_collection.find_one(
            {"document_id": str(doc_id)}
        )
        
        if not mongo_doc:
            return False
        
        embedding_id = UUID(mongo_doc["embedding_id"]) if mongo_doc.get("embedding_id") else None
        
        # Delete from MongoDB
        result = await self.documents_collection.delete_one(
            {"document_id": str(doc_id)}
        )
        
        # Delete from Qdrant if embedding exists
        if embedding_id:
            await self._delete_vector(embedding_id)
        
        return result.deleted_count > 0
    
    # ========================================================================
    # Embedding Generation
    # ========================================================================
    
    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generate embeddings for text using LangChain + OpenAI.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector (1536 dimensions for text-embedding-3-small)
        """
        # LangChain's embed_query is synchronous, but we can await it
        # The underlying OpenAI client handles async internally
        embedding = await self.embeddings.aembed_query(text)
        return embedding
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.
        
        More efficient than calling generate_embeddings multiple times.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = await self.embeddings.aembed_documents(texts)
        return embeddings
    
    # ========================================================================
    # Vector Storage Operations
    # ========================================================================
    
    async def _store_vector(
        self,
        embedding_id: UUID,
        document_id: UUID,
        vector: List[float],
        title: str,
        metadata: Dict[str, Any]
    ) -> None:
        """
        Store vector in Qdrant with metadata.
        
        Args:
            embedding_id: Unique identifier for the vector
            document_id: Reference to the document in MongoDB
            vector: Embedding vector
            title: Document title
            metadata: Additional metadata for filtering
        """
        point = PointStruct(
            id=str(embedding_id),
            vector=vector,
            payload={
                "document_id": str(document_id),
                "title": title,
                **metadata  # Spread metadata for filtering
            }
        )
        
        self.qdrant.upsert(
            collection_name=QDRANT_COLLECTION_NAME,
            points=[point]
        )
    
    async def _delete_vector(self, embedding_id: UUID) -> None:
        """
        Delete vector from Qdrant.
        
        Args:
            embedding_id: Vector identifier
        """
        try:
            self.qdrant.delete(
                collection_name=QDRANT_COLLECTION_NAME,
                points_selector=[str(embedding_id)]
            )
        except Exception:
            # Vector might not exist, ignore errors
            pass
    
    # ========================================================================
    # Semantic Search
    # ========================================================================
    
    async def search_documents(
        self,
        query: SearchQuery
    ) -> List[SearchResult]:
        """
        Perform semantic search using vector similarity.
        
        Process:
        1. Convert query text to embedding vector
        2. Search Qdrant for similar vectors
        3. Fetch full documents from MongoDB
        4. Apply post-filtering and ranking
        5. Return enriched results
        
        Args:
            query: Search query with parameters
            
        Returns:
            List of search results ordered by similarity score (descending)
        """
        # Generate query embedding
        query_vector = await self.generate_embeddings(query.query)
        
        # Build Qdrant filter from metadata filters
        qdrant_filter = None
        if query.filters:
            conditions = []
            for key, value in query.filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            if conditions:
                qdrant_filter = Filter(must=conditions)
        
        # Search Qdrant for similar vectors
        search_results = self.qdrant.search(
            collection_name=QDRANT_COLLECTION_NAME,
            query_vector=query_vector,
            limit=query.limit,
            query_filter=qdrant_filter,
            score_threshold=query.min_similarity
        )
        
        # Fetch full documents from MongoDB and build results
        results = []
        for hit in search_results:
            document_id = UUID(hit.payload["document_id"])
            
            # Fetch full document from MongoDB
            mongo_doc = await self.documents_collection.find_one(
                {"document_id": str(document_id)}
            )
            
            if mongo_doc:
                # Create content snippet (first 500 chars)
                content = mongo_doc["content"]
                snippet = content[:500] + "..." if len(content) > 500 else content
                
                results.append(SearchResult(
                    document_id=document_id,
                    title=mongo_doc["title"],
                    content_snippet=snippet,
                    similarity_score=hit.score,
                    metadata=mongo_doc.get("metadata", {})
                ))
        
        # Results are already ordered by similarity score (descending) from Qdrant
        return results
