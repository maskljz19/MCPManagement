"""
Execution Logs API Endpoints

Provides endpoints for searching and retrieving execution logs
using Elasticsearch for high-performance queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from app.core.database import get_elasticsearch
from app.services.elasticsearch_log_service import ElasticsearchLogService
from app.models.user import UserModel
from app.api.v1.auth import get_current_user
from app.api.dependencies import require_permission
from pydantic import BaseModel, Field


router = APIRouter(prefix="/logs", tags=["Execution Logs"])


class LogSearchRequest(BaseModel):
    """Request model for log search"""
    query: Optional[str] = Field(None, description="Full-text search query")
    tool_id: Optional[str] = Field(None, description="Filter by tool ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID")
    status: Optional[str] = Field(None, description="Filter by execution status")
    from_date: Optional[datetime] = Field(None, description="Start date for time range")
    to_date: Optional[datetime] = Field(None, description="End date for time range")
    size: int = Field(50, ge=1, le=1000, description="Number of results to return")
    search_after: Optional[List] = Field(None, description="Cursor for pagination")
    sort_field: str = Field("timestamp", description="Field to sort by")
    sort_order: str = Field("desc", description="Sort order (asc or desc)")


class LogSearchResponse(BaseModel):
    """Response model for log search"""
    total: int = Field(..., description="Total number of matching logs")
    results: List[dict] = Field(..., description="Log entries")
    next_cursor: Optional[List] = Field(None, description="Cursor for next page")
    has_more: bool = Field(..., description="Whether more results are available")


class LogStatisticsResponse(BaseModel):
    """Response model for log statistics"""
    total_executions: int
    by_status: dict
    by_tool: dict
    avg_duration_ms: Optional[float]
    total_cost: Optional[float]


def get_es_log_service() -> ElasticsearchLogService:
    """Dependency to get Elasticsearch log service"""
    try:
        es_client = get_elasticsearch()
        return ElasticsearchLogService(es_client)
    except RuntimeError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch service is not available"
        )


@router.post("/search", response_model=LogSearchResponse)
@require_permission("mcps", "read")
async def search_execution_logs(
    request: LogSearchRequest,
    current_user: UserModel = Depends(get_current_user),
    es_service: ElasticsearchLogService = Depends(get_es_log_service)
):
    """
    Search execution logs with full-text search and filters.
    
    Supports:
    - Full-text search across log messages and errors
    - Filtering by tool, user, status, date range
    - Cursor-based pagination for consistent results
    - High-performance queries (< 500ms for 1M+ entries)
    
    **Validates: Requirements 11.2, 11.3, 11.4**
    """
    try:
        # Build filters
        filters = {}
        if request.tool_id:
            filters["tool_id"] = request.tool_id
        if request.user_id:
            filters["user_id"] = request.user_id
        if request.status:
            filters["status"] = request.status
        
        # Non-admin users can only see their own logs
        if current_user.role != "admin":
            filters["user_id"] = str(current_user.id)
        
        # Execute search
        results = await es_service.search_logs(
            query=request.query,
            filters=filters,
            from_date=request.from_date,
            to_date=request.to_date,
            size=request.size,
            search_after=request.search_after,
            sort_field=request.sort_field,
            sort_order=request.sort_order
        )
        
        return LogSearchResponse(**results)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search logs: {str(e)}"
        )


@router.get("/execution/{execution_id}")
@require_permission("mcps", "read")
async def get_execution_log(
    execution_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    es_service: ElasticsearchLogService = Depends(get_es_log_service)
):
    """
    Get a specific execution log by execution ID.
    
    **Validates: Requirements 11.1**
    """
    try:
        log = await es_service.get_log_by_execution_id(execution_id)
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Execution log not found: {execution_id}"
            )
        
        # Non-admin users can only see their own logs
        if current_user.role != "admin" and log.get("user_id") != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to view this execution log"
            )
        
        return log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get execution log: {str(e)}"
        )


@router.get("/statistics", response_model=LogStatisticsResponse)
@require_permission("mcps", "read")
async def get_log_statistics(
    from_date: Optional[datetime] = Query(None, description="Start date for statistics"),
    to_date: Optional[datetime] = Query(None, description="End date for statistics"),
    current_user: UserModel = Depends(get_current_user),
    es_service: ElasticsearchLogService = Depends(get_es_log_service)
):
    """
    Get statistics about execution logs.
    
    Returns aggregated metrics including:
    - Total executions
    - Breakdown by status
    - Breakdown by tool
    - Average duration
    - Total cost
    
    **Validates: Requirements 11.2**
    """
    try:
        stats = await es_service.get_log_statistics(
            from_date=from_date,
            to_date=to_date
        )
        
        return LogStatisticsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get log statistics: {str(e)}"
        )


@router.post("/archive")
@require_permission("mcps", "admin")
async def archive_old_logs(
    days_old: int = Query(90, ge=30, le=365, description="Age threshold in days"),
    current_user: UserModel = Depends(get_current_user),
    es_service: ElasticsearchLogService = Depends(get_es_log_service)
):
    """
    Archive logs older than specified days.
    
    This endpoint moves old indices to cold storage or deletes them
    based on retention policy. Only accessible by administrators.
    
    **Validates: Requirements 11.5**
    """
    try:
        archived_count = await es_service.archive_old_logs(days_old=days_old)
        
        return {
            "message": f"Successfully archived {archived_count} old log indices",
            "archived_count": archived_count,
            "days_old": days_old
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive old logs: {str(e)}"
        )
