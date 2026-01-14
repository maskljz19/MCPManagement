"""
Elasticsearch Log Service for MCP Execution Logs

This service provides:
- Elasticsearch index creation with proper mappings
- Log indexing on execution
- Full-text search functionality
- Cursor-based pagination
- Log archival for old logs (90+ days)

Validates Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from elasticsearch import AsyncElasticsearch, NotFoundError
from elasticsearch.helpers import async_bulk

logger = logging.getLogger(__name__)


class ElasticsearchLogService:
    """
    Service for managing execution logs in Elasticsearch.
    
    Provides high-performance log storage, indexing, and querying
    with full-text search capabilities and cursor-based pagination.
    """
    
    # Index settings for optimal performance
    INDEX_SETTINGS = {
        "number_of_shards": 3,
        "number_of_replicas": 1,
        "refresh_interval": "5s",
        "max_result_window": 10000
    }
    
    # Index mappings for execution logs
    INDEX_MAPPINGS = {
        "properties": {
            "execution_id": {"type": "keyword"},
            "tool_id": {"type": "keyword"},
            "user_id": {"type": "keyword"},
            "tool_name": {"type": "keyword"},
            "status": {"type": "keyword"},
            "timestamp": {"type": "date"},
            "start_time": {"type": "date"},
            "end_time": {"type": "date"},
            "duration_ms": {"type": "integer"},
            "log_level": {"type": "keyword"},
            "log_message": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {"type": "keyword"}
                }
            },
            "error_type": {"type": "keyword"},
            "error_message": {
                "type": "text",
                "analyzer": "standard"
            },
            "arguments": {"type": "object", "enabled": False},
            "result": {"type": "object", "enabled": False},
            "mode": {"type": "keyword"},
            "priority": {"type": "integer"},
            "queued_at": {"type": "date"},
            "started_at": {"type": "date"},
            "completed_at": {"type": "date"},
            "queue_wait_ms": {"type": "integer"},
            "cpu_cores_used": {"type": "float"},
            "memory_mb_used": {"type": "integer"},
            "retry_count": {"type": "integer"},
            "cost_amount": {"type": "float"},
            "cache_hit": {"type": "boolean"},
            "cache_key": {"type": "keyword"},
            "ip_address": {"type": "ip"},
            "user_agent": {"type": "text"},
            "correlation_id": {"type": "keyword"},
            "logs": {
                "type": "nested",
                "properties": {
                    "timestamp": {"type": "date"},
                    "level": {"type": "keyword"},
                    "message": {"type": "text"},
                    "metadata": {"type": "object", "enabled": False}
                }
            }
        }
    }
    
    def __init__(
        self,
        es_client: AsyncElasticsearch,
        index_prefix: str = "mcp_logs"
    ):
        """
        Initialize Elasticsearch log service.
        
        Args:
            es_client: Async Elasticsearch client
            index_prefix: Prefix for index names (default: mcp_logs)
        """
        self.es = es_client
        self.index_prefix = index_prefix
        self.current_index = self._get_current_index_name()
    
    def _get_current_index_name(self) -> str:
        """Get the current index name based on date (monthly rotation)"""
        return f"{self.index_prefix}-{datetime.utcnow().strftime('%Y-%m')}"
    
    def _get_index_pattern(self) -> str:
        """Get the index pattern for searching across all indices"""
        return f"{self.index_prefix}-*"
    
    async def initialize_index(self) -> None:
        """
        Create Elasticsearch index with proper mappings if it doesn't exist.
        
        Validates: Requirements 11.1
        """
        try:
            index_name = self._get_current_index_name()
            
            # Check if index exists
            exists = await self.es.indices.exists(index=index_name)
            
            if not exists:
                # Create index with settings and mappings
                await self.es.indices.create(
                    index=index_name,
                    settings=self.INDEX_SETTINGS,
                    mappings=self.INDEX_MAPPINGS
                )
                logger.info(f"Created Elasticsearch index: {index_name}")
            else:
                logger.info(f"Elasticsearch index already exists: {index_name}")
            
            # Update current index reference
            self.current_index = index_name
            
        except Exception as e:
            logger.error(f"Failed to initialize Elasticsearch index: {str(e)}")
            raise
    
    async def index_execution_log(
        self,
        execution_log: Dict[str, Any]
    ) -> str:
        """
        Index an execution log entry in Elasticsearch.
        
        Args:
            execution_log: Execution log document to index
            
        Returns:
            Document ID of the indexed log
            
        Validates: Requirements 11.1
        """
        try:
            # Ensure index exists and is current
            current_index = self._get_current_index_name()
            if current_index != self.current_index:
                await self.initialize_index()
            
            # Prepare document
            doc = execution_log.copy()
            
            # Ensure timestamp field exists
            if "timestamp" not in doc:
                doc["timestamp"] = datetime.utcnow()
            
            # Convert UUID fields to strings
            for field in ["execution_id", "tool_id", "user_id"]:
                if field in doc and isinstance(doc[field], UUID):
                    doc[field] = str(doc[field])
            
            # Index the document
            response = await self.es.index(
                index=self.current_index,
                document=doc,
                id=doc.get("execution_id")  # Use execution_id as document ID
            )
            
            logger.debug(f"Indexed execution log: {doc.get('execution_id')}")
            return response["_id"]
            
        except Exception as e:
            logger.error(f"Failed to index execution log: {str(e)}")
            raise
    
    async def bulk_index_logs(
        self,
        execution_logs: List[Dict[str, Any]]
    ) -> Tuple[int, List[str]]:
        """
        Bulk index multiple execution logs.
        
        Args:
            execution_logs: List of execution log documents
            
        Returns:
            Tuple of (success_count, list of errors)
        """
        try:
            # Ensure index exists
            current_index = self._get_current_index_name()
            if current_index != self.current_index:
                await self.initialize_index()
            
            # Prepare bulk actions
            actions = []
            for log in execution_logs:
                doc = log.copy()
                
                # Ensure timestamp
                if "timestamp" not in doc:
                    doc["timestamp"] = datetime.utcnow()
                
                # Convert UUIDs
                for field in ["execution_id", "tool_id", "user_id"]:
                    if field in doc and isinstance(doc[field], UUID):
                        doc[field] = str(doc[field])
                
                actions.append({
                    "_index": self.current_index,
                    "_id": doc.get("execution_id"),
                    "_source": doc
                })
            
            # Perform bulk indexing
            success, errors = await async_bulk(
                self.es,
                actions,
                raise_on_error=False
            )
            
            logger.info(f"Bulk indexed {success} logs, {len(errors)} errors")
            return success, errors
            
        except Exception as e:
            logger.error(f"Failed to bulk index logs: {str(e)}")
            raise
    
    async def search_logs(
        self,
        query: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        size: int = 50,
        search_after: Optional[List[Any]] = None,
        sort_field: str = "timestamp",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Search execution logs with full-text search and filters.
        
        Args:
            query: Full-text search query
            filters: Field filters (e.g., {"status": "success", "tool_id": "..."})
            from_date: Start date for time range filter
            to_date: End date for time range filter
            size: Number of results to return (max 10000)
            search_after: Cursor for pagination (from previous result)
            sort_field: Field to sort by
            sort_order: Sort order ("asc" or "desc")
            
        Returns:
            Search results with hits and pagination cursor
            
        Validates: Requirements 11.2, 11.3, 11.4
        """
        try:
            # Build query
            must_clauses = []
            
            # Full-text search
            if query:
                must_clauses.append({
                    "multi_match": {
                        "query": query,
                        "fields": ["log_message", "error_message", "tool_name"],
                        "type": "best_fields",
                        "operator": "and"
                    }
                })
            
            # Field filters
            if filters:
                for field, value in filters.items():
                    if isinstance(value, list):
                        must_clauses.append({"terms": {field: value}})
                    else:
                        must_clauses.append({"term": {field: value}})
            
            # Date range filter
            if from_date or to_date:
                range_query = {}
                if from_date:
                    range_query["gte"] = from_date
                if to_date:
                    range_query["lte"] = to_date
                must_clauses.append({"range": {"timestamp": range_query}})
            
            # Build final query
            if must_clauses:
                es_query = {"bool": {"must": must_clauses}}
            else:
                es_query = {"match_all": {}}
            
            # Build search request
            search_body = {
                "query": es_query,
                "size": min(size, 10000),
                "sort": [{sort_field: sort_order}, {"_id": "asc"}]
            }
            
            # Add search_after for cursor-based pagination
            if search_after:
                search_body["search_after"] = search_after
            
            # Execute search
            response = await self.es.search(
                index=self._get_index_pattern(),
                body=search_body
            )
            
            # Extract results
            hits = response["hits"]["hits"]
            total = response["hits"]["total"]["value"]
            
            # Get next cursor
            next_cursor = None
            if hits:
                last_hit = hits[-1]
                next_cursor = last_hit["sort"]
            
            # Format results
            results = []
            for hit in hits:
                doc = hit["_source"]
                doc["_id"] = hit["_id"]
                doc["_score"] = hit.get("_score")
                results.append(doc)
            
            return {
                "total": total,
                "results": results,
                "next_cursor": next_cursor,
                "has_more": len(hits) == size
            }
            
        except Exception as e:
            logger.error(f"Failed to search logs: {str(e)}")
            raise
    
    async def get_log_by_execution_id(
        self,
        execution_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific execution log by execution ID.
        
        Args:
            execution_id: Execution ID to retrieve
            
        Returns:
            Execution log document or None if not found
        """
        try:
            response = await self.es.get(
                index=self._get_index_pattern(),
                id=str(execution_id)
            )
            
            doc = response["_source"]
            doc["_id"] = response["_id"]
            return doc
            
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get log by execution ID: {str(e)}")
            raise
    
    async def archive_old_logs(
        self,
        days_old: int = 90
    ) -> int:
        """
        Archive logs older than specified days to cold storage.
        
        This moves old indices to cold tier or deletes them based on
        retention policy.
        
        Args:
            days_old: Age threshold in days (default: 90)
            
        Returns:
            Number of indices archived/deleted
            
        Validates: Requirements 11.5
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            cutoff_month = cutoff_date.strftime("%Y-%m")
            
            # Get all indices matching pattern
            indices = await self.es.indices.get(index=self._get_index_pattern())
            
            archived_count = 0
            
            for index_name in indices.keys():
                # Extract date from index name
                try:
                    index_date_str = index_name.split("-")[-1]
                    
                    # Check if index is old enough
                    if index_date_str < cutoff_month:
                        # Option 1: Move to cold tier (if ILM is configured)
                        # await self.es.indices.put_settings(
                        #     index=index_name,
                        #     body={"index.routing.allocation.include._tier_preference": "data_cold"}
                        # )
                        
                        # Option 2: Delete old indices (simpler approach)
                        await self.es.indices.delete(index=index_name)
                        logger.info(f"Archived/deleted old index: {index_name}")
                        archived_count += 1
                        
                except (IndexError, ValueError) as e:
                    logger.warning(f"Could not parse date from index {index_name}: {e}")
                    continue
            
            return archived_count
            
        except Exception as e:
            logger.error(f"Failed to archive old logs: {str(e)}")
            raise
    
    async def get_log_statistics(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about execution logs.
        
        Args:
            from_date: Start date for statistics
            to_date: End date for statistics
            
        Returns:
            Dictionary with log statistics
        """
        try:
            # Build date range filter
            date_filter = {}
            if from_date or to_date:
                range_query = {}
                if from_date:
                    range_query["gte"] = from_date
                if to_date:
                    range_query["lte"] = to_date
                date_filter = {"range": {"timestamp": range_query}}
            
            # Aggregation query
            agg_body = {
                "query": date_filter if date_filter else {"match_all": {}},
                "size": 0,
                "aggs": {
                    "total_executions": {"value_count": {"field": "execution_id"}},
                    "by_status": {
                        "terms": {"field": "status", "size": 10}
                    },
                    "by_tool": {
                        "terms": {"field": "tool_name", "size": 20}
                    },
                    "avg_duration": {
                        "avg": {"field": "duration_ms"}
                    },
                    "total_cost": {
                        "sum": {"field": "cost_amount"}
                    }
                }
            }
            
            response = await self.es.search(
                index=self._get_index_pattern(),
                body=agg_body
            )
            
            aggs = response["aggregations"]
            
            return {
                "total_executions": aggs["total_executions"]["value"],
                "by_status": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs["by_status"]["buckets"]
                },
                "by_tool": {
                    bucket["key"]: bucket["doc_count"]
                    for bucket in aggs["by_tool"]["buckets"]
                },
                "avg_duration_ms": aggs["avg_duration"]["value"],
                "total_cost": aggs["total_cost"]["value"]
            }
            
        except Exception as e:
            logger.error(f"Failed to get log statistics: {str(e)}")
            raise
    
    async def close(self) -> None:
        """Close Elasticsearch client connection"""
        await self.es.close()
