"""Admin API Endpoints - Metrics, Audit Trail, and Statistics"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import UUID

from app.core.database import get_db, get_redis, get_mongodb
from app.api.v1.auth import get_current_user
from app.models.user import UserModel, UserRole
from app.services.execution_monitor import (
    ExecutionMonitor,
    MetricFilters,
    AnomalyType
)
from app.services.audit_trail_manager import (
    AuditTrailManager,
    AuditFilters,
    AuditEventType
)
from app.core.logging_config import get_logger


logger = get_logger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])


# ============================================================================
# Dependencies
# ============================================================================


async def require_admin(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Dependency to require admin role.
    
    Args:
        current_user: Currently authenticated user
        
    Returns:
        User model if admin
        
    Raises:
        HTTPException 403: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        logger.warning(
            "admin_access_denied",
            user_id=str(current_user.id),
            username=current_user.username,
            role=current_user.role.value
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_execution_monitor(
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongodb),
    redis: Redis = Depends(get_redis)
) -> ExecutionMonitor:
    """Dependency to get ExecutionMonitor instance"""
    return ExecutionMonitor(mongo_db=mongo_db, redis_client=redis)


async def get_audit_trail_manager(
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongodb)
) -> AuditTrailManager:
    """Dependency to get AuditTrailManager instance"""
    return AuditTrailManager(mongo_db=mongo_db)


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/metrics", response_model=Dict[str, Any])
async def get_admin_metrics(
    current_user: UserModel = Depends(require_admin),
    execution_monitor: ExecutionMonitor = Depends(get_execution_monitor),
    tool_id: Optional[str] = Query(None, description="Filter by tool ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    time_period: str = Query("day", description="Time period: hour, day, week, month"),
    start_date: Optional[datetime] = Query(None, description="Start date for metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for metrics")
):
    """
    Get comprehensive execution metrics for administrators.
    
    Returns aggregated metrics including:
    - Total executions
    - Success/failure rates
    - Duration statistics (average, p50, p95, p99)
    - Resource usage (CPU, memory)
    - Error breakdown by type
    - Executions by status
    - Detected anomalies
    
    **Requirements: 8.2**
    **Validates: Property 26 - Metrics Aggregation Accuracy**
    
    Args:
        current_user: Currently authenticated admin user
        execution_monitor: Execution monitor instance
        tool_id: Optional tool ID filter
        user_id: Optional user ID filter
        status: Optional status filter
        time_period: Time period for aggregation
        start_date: Optional start date
        end_date: Optional end date
        
    Returns:
        Dictionary with comprehensive metrics
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 500: If metrics retrieval fails
    """
    try:
        # Build filters
        filters = MetricFilters(
            tool_id=UUID(tool_id) if tool_id else None,
            user_id=UUID(user_id) if user_id else None,
            status=status,
            start_date=start_date,
            end_date=end_date,
            time_period=time_period
        )
        
        # Get execution metrics
        metrics = await execution_monitor.get_execution_metrics(filters)
        
        # Detect anomalies
        anomalies = await execution_monitor.detect_anomalies()
        
        logger.info(
            "admin_metrics_retrieved",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            total_executions=metrics.total_executions,
            success_rate=metrics.success_rate,
            anomaly_count=len(anomalies)
        )
        
        return {
            "metrics": {
                "total_executions": metrics.total_executions,
                "successful_executions": metrics.successful_executions,
                "failed_executions": metrics.failed_executions,
                "success_rate": metrics.success_rate,
                "duration": {
                    "average_ms": metrics.avg_duration_ms,
                    "p50_ms": metrics.p50_duration_ms,
                    "p95_ms": metrics.p95_duration_ms,
                    "p99_ms": metrics.p99_duration_ms
                },
                "resource_usage": {
                    "average_cpu_cores": metrics.avg_cpu_cores,
                    "average_memory_mb": metrics.avg_memory_mb
                },
                "error_breakdown": metrics.error_breakdown,
                "executions_by_status": metrics.executions_by_status
            },
            "anomalies": [
                {
                    "type": anomaly.anomaly_type.value,
                    "severity": anomaly.severity,
                    "description": anomaly.description,
                    "metric_value": anomaly.metric_value,
                    "threshold_value": anomaly.threshold_value,
                    "tool_id": str(anomaly.tool_id) if anomaly.tool_id else None,
                    "user_id": str(anomaly.user_id) if anomaly.user_id else None,
                    "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None
                }
                for anomaly in anomalies
            ],
            "filters": {
                "tool_id": tool_id,
                "user_id": user_id,
                "status": status,
                "time_period": time_period,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except Exception as e:
        logger.error(
            "admin_metrics_retrieval_failed",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve metrics"
        )


@router.get("/audit-trail", response_model=Dict[str, Any])
async def get_admin_audit_trail(
    current_user: UserModel = Depends(require_admin),
    audit_manager: AuditTrailManager = Depends(get_audit_trail_manager),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tool_id: Optional[str] = Query(None, description="Filter by tool ID"),
    execution_id: Optional[str] = Query(None, description="Filter by execution ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date for audit trail"),
    end_date: Optional[datetime] = Query(None, description="End date for audit trail"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    skip: int = Query(0, ge=0, description="Number of events to skip for pagination")
):
    """
    Get audit trail for administrators.
    
    Returns audit events with filtering and pagination:
    - Event ID and timestamp
    - Event type (initiated, status_changed, completed, etc.)
    - User, tool, and execution IDs
    - Parameters and results
    - Status and duration
    - Resource usage
    - IP address and user agent
    
    **Requirements: 17.4**
    **Validates: Property 69 - Audit Query Filtering**
    
    Args:
        current_user: Currently authenticated admin user
        audit_manager: Audit trail manager instance
        user_id: Optional user ID filter
        tool_id: Optional tool ID filter
        execution_id: Optional execution ID filter
        event_type: Optional event type filter
        status: Optional status filter
        start_date: Optional start date
        end_date: Optional end date
        limit: Maximum number of events
        skip: Number of events to skip
        
    Returns:
        Dictionary with audit events and pagination info
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 400: If invalid event type specified
        HTTPException 500: If audit trail retrieval fails
    """
    try:
        # Validate event type if provided
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type)
            except ValueError:
                valid_types = [e.value for e in AuditEventType]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}. Must be one of: {', '.join(valid_types)}"
                )
        else:
            event_type_enum = None
        
        # Build filters
        filters = AuditFilters(
            user_id=UUID(user_id) if user_id else None,
            tool_id=UUID(tool_id) if tool_id else None,
            execution_id=UUID(execution_id) if execution_id else None,
            event_type=event_type_enum,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            skip=skip
        )
        
        # Query audit trail
        events = await audit_manager.query_audit_trail(filters)
        
        # Convert events to serializable format
        serializable_events = []
        for event in events:
            serializable_event = {}
            for key, value in event.items():
                if key == "_id":
                    continue  # Skip MongoDB internal ID
                elif isinstance(value, datetime):
                    serializable_event[key] = value.isoformat()
                else:
                    serializable_event[key] = value
            serializable_events.append(serializable_event)
        
        logger.info(
            "admin_audit_trail_retrieved",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            event_count=len(events),
            filters_applied=bool(user_id or tool_id or execution_id or event_type or status)
        )
        
        return {
            "events": serializable_events,
            "pagination": {
                "limit": limit,
                "skip": skip,
                "returned": len(events),
                "has_more": len(events) == limit
            },
            "filters": {
                "user_id": user_id,
                "tool_id": tool_id,
                "execution_id": execution_id,
                "event_type": event_type,
                "status": status,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "admin_audit_trail_retrieval_failed",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve audit trail"
        )


@router.get("/statistics", response_model=Dict[str, Any])
async def get_admin_statistics(
    current_user: UserModel = Depends(require_admin),
    execution_monitor: ExecutionMonitor = Depends(get_execution_monitor),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    mongo_db: AsyncIOMotorDatabase = Depends(get_mongodb)
):
    """
    Get comprehensive platform statistics for administrators.
    
    Returns high-level statistics including:
    - Total users, tools, and executions
    - Active executions and queue depth
    - System health metrics
    - Recent activity summary
    - Top tools by usage
    - Top users by execution count
    - Error rates and trends
    
    **Requirements: 8.2, 17.4**
    
    Args:
        current_user: Currently authenticated admin user
        execution_monitor: Execution monitor instance
        db: Database session
        redis: Redis client
        mongo_db: MongoDB database
        
    Returns:
        Dictionary with comprehensive platform statistics
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 500: If statistics retrieval fails
    """
    try:
        from sqlalchemy import select, func
        from app.models.user import UserModel as User
        from app.models.mcp_tool import MCPToolModel
        
        # Get user statistics
        user_count_result = await db.execute(select(func.count(User.id)))
        total_users = user_count_result.scalar() or 0
        
        # Get tool statistics
        tool_count_result = await db.execute(select(func.count(MCPToolModel.id)))
        total_tools = tool_count_result.scalar() or 0
        
        # Get execution statistics from MongoDB
        execution_log_collection = mongo_db["mcp_execution_logs"]
        
        # Total executions
        total_executions = await execution_log_collection.count_documents({})
        
        # Recent executions (last 24 hours)
        one_day_ago = datetime.utcnow() - timedelta(days=1)
        recent_executions = await execution_log_collection.count_documents({
            "completed_at": {"$gte": one_day_ago}
        })
        
        # Active executions (status = running)
        active_executions = await execution_log_collection.count_documents({
            "status": "running"
        })
        
        # Get queue depth from Redis
        queue_depth = 0
        try:
            queue_keys = await redis.keys("queue:executions*")
            for key in queue_keys:
                depth = await redis.zcard(key)
                queue_depth += depth
        except Exception as e:
            logger.warning(f"Failed to get queue depth: {e}")
        
        # Get metrics for last 24 hours
        filters_24h = MetricFilters(
            start_date=one_day_ago,
            end_date=datetime.utcnow(),
            time_period="day"
        )
        metrics_24h = await execution_monitor.get_execution_metrics(filters_24h)
        
        # Get top tools by execution count
        top_tools_pipeline = [
            {
                "$match": {
                    "completed_at": {"$gte": one_day_ago}
                }
            },
            {
                "$group": {
                    "_id": {
                        "tool_id": "$tool_id",
                        "tool_name": "$tool_name"
                    },
                    "execution_count": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                    },
                    "avg_duration_ms": {"$avg": "$duration_ms"}
                }
            },
            {
                "$sort": {"execution_count": -1}
            },
            {
                "$limit": 10
            }
        ]
        
        top_tools_cursor = execution_log_collection.aggregate(top_tools_pipeline)
        top_tools = await top_tools_cursor.to_list(length=10)
        
        # Get top users by execution count
        top_users_pipeline = [
            {
                "$match": {
                    "completed_at": {"$gte": one_day_ago}
                }
            },
            {
                "$group": {
                    "_id": "$user_id",
                    "execution_count": {"$sum": 1},
                    "success_count": {
                        "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                    }
                }
            },
            {
                "$sort": {"execution_count": -1}
            },
            {
                "$limit": 10
            }
        ]
        
        top_users_cursor = execution_log_collection.aggregate(top_users_pipeline)
        top_users = await top_users_cursor.to_list(length=10)
        
        # Get error trends (last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        error_trends_pipeline = [
            {
                "$match": {
                    "completed_at": {"$gte": seven_days_ago},
                    "status": "failed"
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$completed_at"
                            }
                        },
                        "error_type": "$error_type"
                    },
                    "count": {"$sum": 1}
                }
            },
            {
                "$sort": {"_id.date": 1}
            }
        ]
        
        error_trends_cursor = execution_log_collection.aggregate(error_trends_pipeline)
        error_trends = await error_trends_cursor.to_list(length=None)
        
        # Format error trends
        error_trends_formatted = {}
        for trend in error_trends:
            date = trend["_id"]["date"]
            error_type = trend["_id"]["error_type"] or "unknown"
            count = trend["count"]
            
            if date not in error_trends_formatted:
                error_trends_formatted[date] = {}
            error_trends_formatted[date][error_type] = count
        
        logger.info(
            "admin_statistics_retrieved",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            total_users=total_users,
            total_tools=total_tools,
            total_executions=total_executions
        )
        
        return {
            "overview": {
                "total_users": total_users,
                "total_tools": total_tools,
                "total_executions": total_executions,
                "active_executions": active_executions,
                "queue_depth": queue_depth
            },
            "recent_activity": {
                "period": "last_24_hours",
                "executions": recent_executions,
                "success_rate": metrics_24h.success_rate,
                "average_duration_ms": metrics_24h.avg_duration_ms,
                "error_count": metrics_24h.failed_executions
            },
            "top_tools": [
                {
                    "tool_id": tool["_id"]["tool_id"],
                    "tool_name": tool["_id"]["tool_name"],
                    "execution_count": tool["execution_count"],
                    "success_count": tool["success_count"],
                    "success_rate": tool["success_count"] / tool["execution_count"] if tool["execution_count"] > 0 else 0,
                    "average_duration_ms": tool["avg_duration_ms"]
                }
                for tool in top_tools
            ],
            "top_users": [
                {
                    "user_id": user["_id"],
                    "execution_count": user["execution_count"],
                    "success_count": user["success_count"],
                    "success_rate": user["success_count"] / user["execution_count"] if user["execution_count"] > 0 else 0
                }
                for user in top_users
            ],
            "error_trends": error_trends_formatted,
            "system_health": {
                "success_rate_24h": metrics_24h.success_rate,
                "p95_duration_ms": metrics_24h.p95_duration_ms,
                "p99_duration_ms": metrics_24h.p99_duration_ms,
                "average_cpu_cores": metrics_24h.avg_cpu_cores,
                "average_memory_mb": metrics_24h.avg_memory_mb
            }
        }
        
    except Exception as e:
        logger.error(
            "admin_statistics_retrieval_failed",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    current_user: UserModel = Depends(require_admin),
    execution_monitor: ExecutionMonitor = Depends(get_execution_monitor)
):
    """
    Export metrics in Prometheus format.
    
    Returns metrics in Prometheus text exposition format for scraping.
    
    **Requirements: 8.4**
    **Validates: Property 27 - Prometheus Metrics Format**
    
    Args:
        current_user: Currently authenticated admin user
        execution_monitor: Execution monitor instance
        
    Returns:
        Metrics in Prometheus text format
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 500: If metrics export fails
    """
    try:
        from fastapi.responses import PlainTextResponse
        
        metrics_text = await execution_monitor.export_prometheus_metrics()
        
        logger.info(
            "prometheus_metrics_exported",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username
        )
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )
        
    except Exception as e:
        logger.error(
            "prometheus_metrics_export_failed",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export Prometheus metrics"
        )


@router.get("/audit-trail/export")
async def export_audit_trail(
    current_user: UserModel = Depends(require_admin),
    audit_manager: AuditTrailManager = Depends(get_audit_trail_manager),
    format: str = Query("json", description="Export format: json or csv"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    tool_id: Optional[str] = Query(None, description="Filter by tool ID"),
    execution_id: Optional[str] = Query(None, description="Filter by execution ID"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    status: Optional[str] = Query(None, description="Filter by status"),
    start_date: Optional[datetime] = Query(None, description="Start date for audit trail"),
    end_date: Optional[datetime] = Query(None, description="End date for audit trail")
):
    """
    Export audit trail in tamper-evident format.
    
    Exports audit events with checksums for tamper detection.
    Supports JSON and CSV formats.
    
    **Requirements: 17.5**
    **Validates: Property 70 - Audit Export Tamper-Evidence**
    
    Args:
        current_user: Currently authenticated admin user
        audit_manager: Audit trail manager instance
        format: Export format (json or csv)
        user_id: Optional user ID filter
        tool_id: Optional tool ID filter
        execution_id: Optional execution ID filter
        event_type: Optional event type filter
        status: Optional status filter
        start_date: Optional start date
        end_date: Optional end date
        
    Returns:
        Audit trail export file
        
    Raises:
        HTTPException 403: If user is not admin
        HTTPException 400: If invalid format or event type
        HTTPException 500: If export fails
    """
    try:
        from fastapi.responses import Response
        
        # Validate format
        if format not in ["json", "csv"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid format: {format}. Must be 'json' or 'csv'"
            )
        
        # Validate event type if provided
        if event_type:
            try:
                event_type_enum = AuditEventType(event_type)
            except ValueError:
                valid_types = [e.value for e in AuditEventType]
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid event type: {event_type}. Must be one of: {', '.join(valid_types)}"
                )
        else:
            event_type_enum = None
        
        # Build filters
        filters = AuditFilters(
            user_id=UUID(user_id) if user_id else None,
            tool_id=UUID(tool_id) if tool_id else None,
            execution_id=UUID(execution_id) if execution_id else None,
            event_type=event_type_enum,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # Large limit for export
        )
        
        # Export audit trail
        export_data = await audit_manager.export_audit_trail(filters, format)
        
        # Determine content type and filename
        if format == "json":
            content_type = "application/json"
            filename = f"audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        else:
            content_type = "text/csv"
            filename = f"audit_trail_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        logger.info(
            "audit_trail_exported",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            format=format,
            size_bytes=len(export_data)
        )
        
        return Response(
            content=export_data,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(
            "audit_trail_export_failed",
            admin_user_id=str(current_user.id),
            admin_username=current_user.username,
            format=format,
            error=str(e),
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export audit trail"
        )
