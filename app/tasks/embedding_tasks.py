"""Embedding Generation Celery Tasks

Note: Embedding generation has been disabled due to hardware limitations.
This file is kept for compatibility but tasks will not generate embeddings.
"""

import asyncio
from typing import List, Dict, Any
from uuid import UUID

from app.core.celery_app import celery_app
from app.core.database import get_mongodb_client, get_redis_client
from app.services.knowledge_service import KnowledgeBaseService
from app.core.config import settings


def get_knowledge_service() -> KnowledgeBaseService:
    """Get KnowledgeBaseService instance with dependencies"""
    mongo_client = get_mongodb_client()
    mongo_db = mongo_client[settings.MONGODB_DATABASE]
    redis_client = get_redis_client()
    
    return KnowledgeBaseService(
        mongo_db=mongo_db,
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
    
    Note: This task is disabled due to hardware limitations.
    It will return immediately without processing.
    
    Args:
        document_ids: List of document IDs to generate embeddings for
        batch_size: Number of documents to process in each batch
    
    Returns:
        Result indicating task is disabled
    
    Validates: Requirements 9.3
    """
    return {
        "total": len(document_ids),
        "processed": 0,
        "failed": 0,
        "status": "disabled",
        "message": "Embedding generation disabled due to hardware limitations"
    }
