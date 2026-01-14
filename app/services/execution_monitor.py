"""
Execution Monitor Service - Collects and analyzes execution metrics.

This service is responsible for:
- Recording execution metrics (duration, success rate, resource usage)
- Aggregating metrics by tool, user, and time period
- Detecting anomalies in execution patterns
- Exporting Prometheus metrics
- Triggering alerts for administrators

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from uuid import UUID
from dataclasses import dataclass
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis

from app.core.monitoring import registry as global_registry


logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================


class MetricType(str, Enum):
    """Types of metrics collected"""
    EXECUTION_COUNT = "execution_count"
    EXECUTION_DURATION = "execution_duration"
    SUCCESS_RATE = "success_rate"
    ERROR_RATE = "error_rate"
    RESOURCE_USAGE = "resource_usage"
    QUEUE_DEPTH = "queue_depth"
    CACHE_HIT_RATE = "cache_hit_rate"


class AnomalyType(str, Enum):
    """Types of anomalies detected"""
    HIGH_ERROR_RATE = "high_error_rate"
    SLOW_EXECUTION = "slow_execution"
    HIGH_RESOURCE_USAGE = "high_resource_usage"
    UNUSUAL_PATTERN = "unusual_pattern"


@dataclass
class ExecutionMetadata:
    """Metadata for execution tracking"""
    execution_id: UUID
    tool_id: UUID
    tool_name: str
    user_id: UUID
    status: str
    started_at: datetime
    mode: str = "sync"
    priority: int = 5


@dataclass
class ExecutionResult:
    """Result of an execution"""
    execution_id: UUID
    tool_id: UUID
    tool_name: str
    user_id: UUID
    status: str
    duration_ms: int
    cpu_cores_used: float
    memory_mb_used: int
    error_type: Optional[str] = None
    completed_at: Optional[datetime] = None


@dataclass
class MetricFilters:
    """Filters for querying metrics"""
    tool_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    status: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    time_period: str = "day"  # hour, day, week, month


@dataclass
class ExecutionMetrics:
    """Aggregated execution metrics"""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_duration_ms: float
    p50_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    avg_cpu_cores: float
    avg_memory_mb: float
    error_breakdown: Dict[str, int]
    executions_by_status: Dict[str, int]


@dataclass
class Anomaly:
    """Detected anomaly"""
    anomaly_type: AnomalyType
    severity: str  # low, medium, high, critical
    description: str
    metric_value: float
    threshold_value: float
    tool_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    detected_at: Optional[datetime] = None


# ============================================================================
# Execution Monitor
# ============================================================================


class ExecutionMonitor:
    """
    Monitors and analyzes MCP tool executions.
    
    Collects metrics, detects anomalies, and exports data for monitoring systems.
    """
    
    def __init__(
        self,
        mongo_db: AsyncIOMotorDatabase,
        redis_client: Optional[Redis] = None,
        registry: Optional[CollectorRegistry] = None
    ):
        """
        Initialize the execution monitor.
        
        Args:
            mongo_db: MongoDB database for execution logs
            redis_client: Redis client for real-time metrics
            registry: Prometheus registry (uses global if not provided)
        """
        self.mongo = mongo_db
        self.execution_log_collection = mongo_db["mcp_execution_logs"]
        self.redis = redis_client
        self.registry = registry or global_registry
        
        # Initialize Prometheus metrics
        self._init_prometheus_metrics()
        
        # Anomaly detection thresholds
        self.thresholds = {
            "error_rate": 0.05,  # 5% error rate
            "slow_execution_multiplier": 3.0,  # 3x average duration
            "high_cpu_usage": 0.9,  # 90% CPU usage
            "high_memory_usage": 0.9,  # 90% memory usage
        }
    
    def _init_prometheus_metrics(self):
        """Initialize Prometheus metrics for MCP executions"""
        # Execution counters
        self.mcp_executions_total = Counter(
            'mcp_executions_total',
            'Total MCP tool executions',
            ['tool_id', 'tool_name', 'user_id', 'status'],
            registry=self.registry
        )
        
        self.mcp_execution_errors_total = Counter(
            'mcp_execution_errors_total',
            'Total MCP execution errors',
            ['tool_id', 'tool_name', 'error_type'],
            registry=self.registry
        )
        
        # Execution duration histogram
        self.mcp_execution_duration_seconds = Histogram(
            'mcp_execution_duration_seconds',
            'MCP execution duration in seconds',
            ['tool_id', 'tool_name'],
            registry=self.registry,
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
        )
        
        # Active executions gauge
        self.mcp_active_executions = Gauge(
            'mcp_active_executions',
            'Number of currently active MCP executions',
            ['tool_id', 'tool_name'],
            registry=self.registry
        )
        
        # Queue metrics
        self.mcp_queue_depth = Gauge(
            'mcp_queue_depth',
            'Number of executions in queue',
            ['priority'],
            registry=self.registry
        )
        
        self.mcp_queue_wait_time_seconds = Histogram(
            'mcp_queue_wait_time_seconds',
            'Time spent waiting in queue',
            ['priority'],
            registry=self.registry,
            buckets=(0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0, 600.0)
        )
        
        # Resource usage gauges
        self.mcp_cpu_usage = Gauge(
            'mcp_cpu_usage',
            'CPU cores used by MCP executions',
            ['tool_id', 'tool_name'],
            registry=self.registry
        )
        
        self.mcp_memory_usage_mb = Gauge(
            'mcp_memory_usage_mb',
            'Memory used by MCP executions in MB',
            ['tool_id', 'tool_name'],
            registry=self.registry
        )
        
        # Cache metrics
        self.mcp_cache_hit_rate = Gauge(
            'mcp_cache_hit_rate',
            'Cache hit rate for MCP executions (0.0 to 1.0)',
            registry=self.registry
        )
        
        # Success rate gauge
        self.mcp_success_rate = Gauge(
            'mcp_success_rate',
            'Success rate for MCP executions (0.0 to 1.0)',
            ['tool_id', 'tool_name'],
            registry=self.registry
        )
    
    async def record_execution_start(
        self,
        execution_id: UUID,
        metadata: ExecutionMetadata
    ) -> None:
        """
        Record the start of an execution.
        
        Args:
            execution_id: Unique execution identifier
            metadata: Execution metadata
        """
        try:
            # Increment active executions gauge
            self.mcp_active_executions.labels(
                tool_id=str(metadata.tool_id),
                tool_name=metadata.tool_name
            ).inc()
            
            # Store start time in Redis for duration calculation
            if self.redis:
                await self.redis.setex(
                    f"execution:start:{execution_id}",
                    3600,  # 1 hour TTL
                    metadata.started_at.isoformat()
                )
            
            logger.info(
                f"Recorded execution start: {execution_id} "
                f"(tool={metadata.tool_name}, user={metadata.user_id})"
            )
        
        except Exception as e:
            logger.error(f"Failed to record execution start: {e}")
    
    async def record_execution_complete(
        self,
        execution_id: UUID,
        result: ExecutionResult
    ) -> None:
        """
        Record the completion of an execution.
        
        Args:
            execution_id: Unique execution identifier
            result: Execution result with metrics
        """
        try:
            # Decrement active executions gauge
            self.mcp_active_executions.labels(
                tool_id=str(result.tool_id),
                tool_name=result.tool_name
            ).dec()
            
            # Increment execution counter
            self.mcp_executions_total.labels(
                tool_id=str(result.tool_id),
                tool_name=result.tool_name,
                user_id=str(result.user_id),
                status=result.status
            ).inc()
            
            # Record duration
            duration_seconds = result.duration_ms / 1000.0
            self.mcp_execution_duration_seconds.labels(
                tool_id=str(result.tool_id),
                tool_name=result.tool_name
            ).observe(duration_seconds)
            
            # Record error if failed
            if result.status == "failed" and result.error_type:
                self.mcp_execution_errors_total.labels(
                    tool_id=str(result.tool_id),
                    tool_name=result.tool_name,
                    error_type=result.error_type
                ).inc()
            
            # Update resource usage gauges
            self.mcp_cpu_usage.labels(
                tool_id=str(result.tool_id),
                tool_name=result.tool_name
            ).set(result.cpu_cores_used)
            
            self.mcp_memory_usage_mb.labels(
                tool_id=str(result.tool_id),
                tool_name=result.tool_name
            ).set(result.memory_mb_used)
            
            # Update success rate
            await self._update_success_rate(result.tool_id, result.tool_name)
            
            logger.info(
                f"Recorded execution complete: {execution_id} "
                f"(status={result.status}, duration={result.duration_ms}ms)"
            )
        
        except Exception as e:
            logger.error(f"Failed to record execution complete: {e}")
    
    async def _update_success_rate(self, tool_id: UUID, tool_name: str) -> None:
        """
        Update the success rate metric for a tool.
        
        Args:
            tool_id: Tool identifier
            tool_name: Tool name
        """
        try:
            # Query recent executions from MongoDB
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            pipeline = [
                {
                    "$match": {
                        "tool_id": str(tool_id),
                        "completed_at": {"$gte": one_hour_ago}
                    }
                },
                {
                    "$group": {
                        "_id": "$status",
                        "count": {"$sum": 1}
                    }
                }
            ]
            
            results = await self.execution_log_collection.aggregate(pipeline).to_list(None)
            
            total = sum(r["count"] for r in results)
            successful = sum(r["count"] for r in results if r["_id"] == "success")
            
            if total > 0:
                success_rate = successful / total
                self.mcp_success_rate.labels(
                    tool_id=str(tool_id),
                    tool_name=tool_name
                ).set(success_rate)
        
        except Exception as e:
            logger.error(f"Failed to update success rate: {e}")
    
    async def get_execution_metrics(
        self,
        filters: MetricFilters
    ) -> ExecutionMetrics:
        """
        Get aggregated execution metrics based on filters.
        
        Args:
            filters: Filters for querying metrics
            
        Returns:
            Aggregated execution metrics
        """
        try:
            # Build MongoDB query
            query = {}
            
            if filters.tool_id:
                query["tool_id"] = str(filters.tool_id)
            
            if filters.user_id:
                query["user_id"] = str(filters.user_id)
            
            if filters.status:
                query["status"] = filters.status
            
            if filters.start_date or filters.end_date:
                date_filter = {}
                if filters.start_date:
                    date_filter["$gte"] = filters.start_date
                if filters.end_date:
                    date_filter["$lte"] = filters.end_date
                query["completed_at"] = date_filter
            
            # Aggregate metrics
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": None,
                        "total_executions": {"$sum": 1},
                        "successful_executions": {
                            "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                        },
                        "failed_executions": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        },
                        "avg_duration_ms": {"$avg": "$duration_ms"},
                        "durations": {"$push": "$duration_ms"},
                        "avg_cpu_cores": {"$avg": "$cpu_cores_used"},
                        "avg_memory_mb": {"$avg": "$memory_mb_used"},
                        "statuses": {"$push": "$status"},
                        "error_types": {"$push": "$error_type"}
                    }
                }
            ]
            
            results = await self.execution_log_collection.aggregate(pipeline).to_list(1)
            
            if not results:
                return ExecutionMetrics(
                    total_executions=0,
                    successful_executions=0,
                    failed_executions=0,
                    success_rate=0.0,
                    avg_duration_ms=0.0,
                    p50_duration_ms=0.0,
                    p95_duration_ms=0.0,
                    p99_duration_ms=0.0,
                    avg_cpu_cores=0.0,
                    avg_memory_mb=0.0,
                    error_breakdown={},
                    executions_by_status={}
                )
            
            result = results[0]
            
            # Calculate percentiles
            durations = sorted(result.get("durations", []))
            p50 = self._calculate_percentile(durations, 50)
            p95 = self._calculate_percentile(durations, 95)
            p99 = self._calculate_percentile(durations, 99)
            
            # Calculate success rate
            total = result["total_executions"]
            successful = result["successful_executions"]
            success_rate = successful / total if total > 0 else 0.0
            
            # Count error types
            error_types = [e for e in result.get("error_types", []) if e]
            error_breakdown = {}
            for error_type in error_types:
                error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
            
            # Count statuses
            statuses = result.get("statuses", [])
            executions_by_status = {}
            for status in statuses:
                executions_by_status[status] = executions_by_status.get(status, 0) + 1
            
            return ExecutionMetrics(
                total_executions=total,
                successful_executions=successful,
                failed_executions=result["failed_executions"],
                success_rate=success_rate,
                avg_duration_ms=result.get("avg_duration_ms", 0.0),
                p50_duration_ms=p50,
                p95_duration_ms=p95,
                p99_duration_ms=p99,
                avg_cpu_cores=result.get("avg_cpu_cores", 0.0),
                avg_memory_mb=result.get("avg_memory_mb", 0.0),
                error_breakdown=error_breakdown,
                executions_by_status=executions_by_status
            )
        
        except Exception as e:
            logger.error(f"Failed to get execution metrics: {e}")
            raise
    
    def _calculate_percentile(self, sorted_values: List[float], percentile: int) -> float:
        """
        Calculate percentile from sorted values.
        
        Args:
            sorted_values: List of sorted values
            percentile: Percentile to calculate (0-100)
            
        Returns:
            Percentile value
        """
        if not sorted_values:
            return 0.0
        
        index = int((percentile / 100.0) * len(sorted_values))
        index = min(index, len(sorted_values) - 1)
        return sorted_values[index]
    
    async def detect_anomalies(self) -> List[Anomaly]:
        """
        Detect anomalies in execution patterns.
        
        Returns:
            List of detected anomalies
        """
        anomalies = []
        
        try:
            # Check for high error rates
            error_rate_anomalies = await self._detect_high_error_rate()
            anomalies.extend(error_rate_anomalies)
            
            # Check for slow executions
            slow_execution_anomalies = await self._detect_slow_executions()
            anomalies.extend(slow_execution_anomalies)
            
            # Check for high resource usage
            resource_anomalies = await self._detect_high_resource_usage()
            anomalies.extend(resource_anomalies)
            
            logger.info(f"Detected {len(anomalies)} anomalies")
        
        except Exception as e:
            logger.error(f"Failed to detect anomalies: {e}")
        
        return anomalies
    
    async def _detect_high_error_rate(self) -> List[Anomaly]:
        """Detect tools with high error rates"""
        anomalies = []
        
        try:
            # Query error rates by tool in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            pipeline = [
                {
                    "$match": {
                        "completed_at": {"$gte": one_hour_ago}
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "tool_id": "$tool_id",
                            "tool_name": "$tool_name"
                        },
                        "total": {"$sum": 1},
                        "failed": {
                            "$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}
                        }
                    }
                },
                {
                    "$match": {
                        "total": {"$gte": 10}  # At least 10 executions
                    }
                }
            ]
            
            results = await self.execution_log_collection.aggregate(pipeline).to_list(None)
            
            for result in results:
                total = result["total"]
                failed = result["failed"]
                error_rate = failed / total
                
                if error_rate > self.thresholds["error_rate"]:
                    severity = "critical" if error_rate > 0.2 else "high"
                    
                    anomalies.append(Anomaly(
                        anomaly_type=AnomalyType.HIGH_ERROR_RATE,
                        severity=severity,
                        description=f"Tool {result['_id']['tool_name']} has high error rate: {error_rate:.1%}",
                        metric_value=error_rate,
                        threshold_value=self.thresholds["error_rate"],
                        tool_id=UUID(result['_id']['tool_id']),
                        detected_at=datetime.utcnow()
                    ))
        
        except Exception as e:
            logger.error(f"Failed to detect high error rate: {e}")
        
        return anomalies
    
    async def _detect_slow_executions(self) -> List[Anomaly]:
        """Detect unusually slow executions"""
        anomalies = []
        
        try:
            # Query average durations by tool
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            pipeline = [
                {
                    "$match": {
                        "completed_at": {"$gte": one_hour_ago},
                        "status": "success"
                    }
                },
                {
                    "$group": {
                        "_id": {
                            "tool_id": "$tool_id",
                            "tool_name": "$tool_name"
                        },
                        "avg_duration": {"$avg": "$duration_ms"},
                        "max_duration": {"$max": "$duration_ms"},
                        "count": {"$sum": 1}
                    }
                },
                {
                    "$match": {
                        "count": {"$gte": 5}  # At least 5 executions
                    }
                }
            ]
            
            results = await self.execution_log_collection.aggregate(pipeline).to_list(None)
            
            for result in results:
                avg_duration = result["avg_duration"]
                max_duration = result["max_duration"]
                
                # Check if max is significantly higher than average
                if max_duration > avg_duration * self.thresholds["slow_execution_multiplier"]:
                    severity = "medium"
                    
                    anomalies.append(Anomaly(
                        anomaly_type=AnomalyType.SLOW_EXECUTION,
                        severity=severity,
                        description=f"Tool {result['_id']['tool_name']} has slow execution: {max_duration}ms (avg: {avg_duration:.0f}ms)",
                        metric_value=max_duration,
                        threshold_value=avg_duration * self.thresholds["slow_execution_multiplier"],
                        tool_id=UUID(result['_id']['tool_id']),
                        detected_at=datetime.utcnow()
                    ))
        
        except Exception as e:
            logger.error(f"Failed to detect slow executions: {e}")
        
        return anomalies
    
    async def _detect_high_resource_usage(self) -> List[Anomaly]:
        """Detect high resource usage"""
        anomalies = []
        
        try:
            # Query recent executions with high resource usage
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            high_cpu_executions = await self.execution_log_collection.count_documents({
                "completed_at": {"$gte": one_hour_ago},
                "cpu_cores_used": {"$gte": self.thresholds["high_cpu_usage"]}
            })
            
            high_memory_executions = await self.execution_log_collection.count_documents({
                "completed_at": {"$gte": one_hour_ago},
                "memory_mb_used": {"$gte": 4096 * self.thresholds["high_memory_usage"]}
            })
            
            if high_cpu_executions > 10:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.HIGH_RESOURCE_USAGE,
                    severity="high",
                    description=f"High CPU usage detected in {high_cpu_executions} executions",
                    metric_value=float(high_cpu_executions),
                    threshold_value=10.0,
                    detected_at=datetime.utcnow()
                ))
            
            if high_memory_executions > 10:
                anomalies.append(Anomaly(
                    anomaly_type=AnomalyType.HIGH_RESOURCE_USAGE,
                    severity="high",
                    description=f"High memory usage detected in {high_memory_executions} executions",
                    metric_value=float(high_memory_executions),
                    threshold_value=10.0,
                    detected_at=datetime.utcnow()
                ))
        
        except Exception as e:
            logger.error(f"Failed to detect high resource usage: {e}")
        
        return anomalies
    
    async def export_prometheus_metrics(self) -> str:
        """
        Export metrics in Prometheus format.
        
        Returns:
            Metrics in Prometheus text format
        """
        from prometheus_client import generate_latest
        
        try:
            metrics_bytes = generate_latest(self.registry)
            return metrics_bytes.decode('utf-8')
        
        except Exception as e:
            logger.error(f"Failed to export Prometheus metrics: {e}")
            raise
    
    async def trigger_alert(self, anomaly: Anomaly) -> None:
        """
        Trigger an alert for an anomaly.
        
        Args:
            anomaly: Detected anomaly
        """
        try:
            # Log the alert
            logger.warning(
                f"ALERT: {anomaly.anomaly_type.value} - {anomaly.description} "
                f"(severity={anomaly.severity})"
            )
            
            # Store alert in Redis for dashboard
            if self.redis:
                alert_key = f"alert:{anomaly.anomaly_type.value}:{datetime.utcnow().isoformat()}"
                alert_data = {
                    "type": anomaly.anomaly_type.value,
                    "severity": anomaly.severity,
                    "description": anomaly.description,
                    "metric_value": anomaly.metric_value,
                    "threshold_value": anomaly.threshold_value,
                    "detected_at": anomaly.detected_at.isoformat() if anomaly.detected_at else None
                }
                
                if anomaly.tool_id:
                    alert_data["tool_id"] = str(anomaly.tool_id)
                if anomaly.user_id:
                    alert_data["user_id"] = str(anomaly.user_id)
                
                await self.redis.setex(
                    alert_key,
                    86400,  # 24 hour TTL
                    str(alert_data)
                )
            
            # TODO: Integrate with alerting system (email, Slack, PagerDuty, etc.)
            # This would be implemented based on the organization's alerting infrastructure
        
        except Exception as e:
            logger.error(f"Failed to trigger alert: {e}")
    
    async def update_queue_metrics(self, queue_depth: int, priority: int) -> None:
        """
        Update queue depth metrics.
        
        Args:
            queue_depth: Current queue depth
            priority: Priority level
        """
        try:
            self.mcp_queue_depth.labels(priority=str(priority)).set(queue_depth)
        except Exception as e:
            logger.error(f"Failed to update queue metrics: {e}")
    
    async def record_queue_wait_time(self, wait_time_seconds: float, priority: int) -> None:
        """
        Record time spent waiting in queue.
        
        Args:
            wait_time_seconds: Wait time in seconds
            priority: Priority level
        """
        try:
            self.mcp_queue_wait_time_seconds.labels(priority=str(priority)).observe(wait_time_seconds)
        except Exception as e:
            logger.error(f"Failed to record queue wait time: {e}")
    
    async def update_cache_hit_rate(self, hit_rate: float) -> None:
        """
        Update cache hit rate metric.
        
        Args:
            hit_rate: Cache hit rate (0.0 to 1.0)
        """
        try:
            self.mcp_cache_hit_rate.set(hit_rate)
        except Exception as e:
            logger.error(f"Failed to update cache hit rate: {e}")


# ============================================================================
# Helper Functions
# ============================================================================


def create_execution_monitor(
    mongo_db: AsyncIOMotorDatabase,
    redis_client: Optional[Redis] = None,
    registry: Optional[CollectorRegistry] = None
) -> ExecutionMonitor:
    """
    Factory function to create an ExecutionMonitor instance.
    
    Args:
        mongo_db: MongoDB database
        redis_client: Redis client
        registry: Prometheus registry
        
    Returns:
        ExecutionMonitor instance
    """
    return ExecutionMonitor(
        mongo_db=mongo_db,
        redis_client=redis_client,
        registry=registry
    )
