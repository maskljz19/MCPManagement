"""
Initialize Elasticsearch indices for MCP execution logs.

This script creates the necessary Elasticsearch indices with proper
mappings and settings for optimal log storage and querying.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import init_elasticsearch, get_elasticsearch, close_elasticsearch
from app.services.elasticsearch_log_service import ElasticsearchLogService


async def main():
    """Initialize Elasticsearch indices"""
    print("Initializing Elasticsearch connection...")
    
    try:
        # Initialize Elasticsearch
        await init_elasticsearch()
        es_client = get_elasticsearch()
        
        print(f"Connected to Elasticsearch at {settings.ELASTICSEARCH_HOST}:{settings.ELASTICSEARCH_PORT}")
        
        # Create log service
        log_service = ElasticsearchLogService(
            es_client=es_client,
            index_prefix=settings.ELASTICSEARCH_INDEX_PREFIX
        )
        
        print(f"Creating index with prefix: {settings.ELASTICSEARCH_INDEX_PREFIX}")
        
        # Initialize index
        await log_service.initialize_index()
        
        print(f"✓ Successfully created index: {log_service.current_index}")
        print("\nIndex settings:")
        print(f"  - Shards: {log_service.INDEX_SETTINGS['number_of_shards']}")
        print(f"  - Replicas: {log_service.INDEX_SETTINGS['number_of_replicas']}")
        print(f"  - Refresh interval: {log_service.INDEX_SETTINGS['refresh_interval']}")
        
        print("\nElasticsearch initialization complete!")
        
    except Exception as e:
        print(f"✗ Error initializing Elasticsearch: {str(e)}")
        sys.exit(1)
    
    finally:
        # Close connection
        await close_elasticsearch()
        print("\nClosed Elasticsearch connection")


if __name__ == "__main__":
    asyncio.run(main())
