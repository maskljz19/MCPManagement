"""Embedding Generation Celery Tasks"""

import asyncio
from typing import List, Dict, Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import get_mongodb_client, get_qdrant_client, get_redis_client
from app.services.knowledge_service import KnowledgeBaseService
from app.core.config import settings


def get_knowledge_service() -> KnowledgeBaseService:
    """Get KnowledgeBaseService instance with dependencies"""
    mongo_client = get_mongodb_client()
    mongo_db = mongo_client[settings.MONGODB_DATABASE]
    qdrant_client = get_qdrant_client()
    redis_client = get_redis_client()
    
    return KnowledgeBaseService(
        mongo_db=mongo_db,
        qdrant_client=qdrant_client,
        redis=redis_client,
        openai_api_key=settings.OPENAI_API_KEY
    )


@celery_app.task(
    bind=True,
    name="app.tasks.embedding_tasks.generate_embeddings",
    max_retries=3,
    default_retry_delay=60
)
def generate_embeddings_task(
    self,
    document_ids: List[str],
    batch_size: int = 10
) -> Dict[str, Any]:
    """
    Celery task for batch embedding generation.
    
    This task runs asynchronously to generate embeddings for multiple
    documents. Useful for bulk operations or re-indexing.
    
    Args:
        document_ids: List of document IDs to generate embeddings for
        batch_size: Number of documents to process in each batch
    
    Returns:
        Result with count of successfully processed documents
    
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 60s * (2 ** retry_count)
    
    Validates: Requirements 9.3
    """
    try:
        # Get knowledge service instance
        service = get_knowledge_service()
        
        # Process documents in batches
        loop = asyncio.get_event_loop()
        processed_count = 0
        failed_count = 0
        
        for i in range(0, len(document_ids), batch_size):
            batch = document_ids[i:i + batch_size]
            
            for doc_id_str in batch:
                try:
                    doc_id = UUID(doc_id_str)
                    
                    # Fetch document
                    document = loop.run_until_complete(
                        service.get_document(doc_id)
                    )
                    
                    if document:
                        # Generate embedding
                        embedding = loop.run_until_complete(
                            service.generate_embeddings(document.content)
                        )
                        
                        # Store in Qdrant
                        loop.run_until_complete(
                            service._store_vector(
                                embedding_id=document.embedding_id or UUID(doc_id_str),
                                document_id=doc_id,
                                vector=embedding,
                                title=document.title,
                                metadata=document.metadata
                            )
                        )
                        
                        processed_count += 1
                    else:
                        failed_count += 1
                        
                except Exception as e:
                    failed_count += 1
                    # Log error but continue processing other documents
                    print(f"Failed to process document {doc_id_str}: {e}")
        
        return {
            "total": len(document_ids),
            "processed": processed_count,
            "failed": failed_count,
            "status": "completed"
        }
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 60 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
