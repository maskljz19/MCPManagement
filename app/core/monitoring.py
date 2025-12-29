"""Prometheus Metrics Configuration"""

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from typing import Dict, Any
import time

# Create a custom registry for our metrics
registry = CollectorRegistry()

# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status'],
    registry=registry
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    registry=registry,
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently being processed',
    ['method', 'endpoint'],
    registry=registry
)

# ============================================================================
# Business Metrics
# ============================================================================

mcp_tools_total = Gauge(
    'mcp_tools_total',
    'Total number of MCP tools',
    ['status'],
    registry=registry
)

active_deployments = Gauge(
    'active_deployments',
    'Number of active MCP deployments',
    registry=registry
)

cache_hit_rate = Gauge(
    'cache_hit_rate',
    'Cache hit rate (0.0 to 1.0)',
    registry=registry
)

cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'result'],
    registry=registry
)

# ============================================================================
# Task Queue Metrics
# ============================================================================

celery_tasks_total = Counter(
    'celery_tasks_total',
    'Total Celery tasks',
    ['task_name', 'status'],
    registry=registry
)

celery_task_duration_seconds = Histogram(
    'celery_task_duration_seconds',
    'Celery task duration in seconds',
    ['task_name'],
    registry=registry,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0)
)

celery_tasks_in_progress = Gauge(
    'celery_tasks_in_progress',
    'Number of Celery tasks currently being processed',
    ['task_name'],
    registry=registry
)

# ============================================================================
# Database Metrics
# ============================================================================

database_connections_active = Gauge(
    'database_connections_active',
    'Number of active database connections',
    ['database'],
    registry=registry
)

database_query_duration_seconds = Histogram(
    'database_query_duration_seconds',
    'Database query duration in seconds',
    ['database', 'operation'],
    registry=registry,
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

database_errors_total = Counter(
    'database_errors_total',
    'Total database errors',
    ['database', 'error_type'],
    registry=registry
)

# ============================================================================
# Knowledge Base Metrics
# ============================================================================

documents_total = Gauge(
    'documents_total',
    'Total number of documents in knowledge base',
    registry=registry
)

search_queries_total = Counter(
    'search_queries_total',
    'Total semantic search queries',
    registry=registry
)

search_duration_seconds = Histogram(
    'search_duration_seconds',
    'Semantic search duration in seconds',
    registry=registry,
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

embedding_generation_duration_seconds = Histogram(
    'embedding_generation_duration_seconds',
    'Embedding generation duration in seconds',
    registry=registry,
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
)

# ============================================================================
# AI Analysis Metrics
# ============================================================================

ai_analysis_requests_total = Counter(
    'ai_analysis_requests_total',
    'Total AI analysis requests',
    ['analysis_type'],
    registry=registry
)

ai_analysis_duration_seconds = Histogram(
    'ai_analysis_duration_seconds',
    'AI analysis duration in seconds',
    ['analysis_type'],
    registry=registry,
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0)
)

ai_analysis_errors_total = Counter(
    'ai_analysis_errors_total',
    'Total AI analysis errors',
    ['analysis_type', 'error_type'],
    registry=registry
)

# ============================================================================
# WebSocket Metrics
# ============================================================================

websocket_connections_active = Gauge(
    'websocket_connections_active',
    'Number of active WebSocket connections',
    registry=registry
)

websocket_messages_total = Counter(
    'websocket_messages_total',
    'Total WebSocket messages',
    ['direction'],  # 'sent' or 'received'
    registry=registry
)

# ============================================================================
# GitHub Integration Metrics
# ============================================================================

github_sync_operations_total = Counter(
    'github_sync_operations_total',
    'Total GitHub sync operations',
    ['status'],
    registry=registry
)

github_api_requests_total = Counter(
    'github_api_requests_total',
    'Total GitHub API requests',
    ['endpoint', 'status'],
    registry=registry
)

# ============================================================================
# Helper Functions
# ============================================================================

def get_metrics() -> bytes:
    """
    Generate Prometheus metrics in text format.
    
    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(registry)


def get_metrics_content_type() -> str:
    """
    Get the content type for Prometheus metrics.
    
    Returns:
        Content type string
    """
    return CONTENT_TYPE_LATEST


class MetricsCollector:
    """Helper class for collecting and updating metrics"""
    
    @staticmethod
    def record_http_request(method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request metrics"""
        http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
        http_request_duration_seconds.labels(method=method, endpoint=endpoint).observe(duration)
    
    @staticmethod
    def record_cache_operation(operation: str, result: str):
        """Record cache operation metrics"""
        cache_operations_total.labels(operation=operation, result=result).inc()
    
    @staticmethod
    def update_cache_hit_rate(hit_rate: float):
        """Update cache hit rate metric"""
        cache_hit_rate.set(hit_rate)
    
    @staticmethod
    def record_celery_task(task_name: str, status: str, duration: float = None):
        """Record Celery task metrics"""
        celery_tasks_total.labels(task_name=task_name, status=status).inc()
        if duration is not None:
            celery_task_duration_seconds.labels(task_name=task_name).observe(duration)
    
    @staticmethod
    def record_database_query(database: str, operation: str, duration: float):
        """Record database query metrics"""
        database_query_duration_seconds.labels(database=database, operation=operation).observe(duration)
    
    @staticmethod
    def record_database_error(database: str, error_type: str):
        """Record database error metrics"""
        database_errors_total.labels(database=database, error_type=error_type).inc()
    
    @staticmethod
    def record_search_query(duration: float):
        """Record semantic search metrics"""
        search_queries_total.inc()
        search_duration_seconds.observe(duration)
    
    @staticmethod
    def record_embedding_generation(duration: float):
        """Record embedding generation metrics"""
        embedding_generation_duration_seconds.observe(duration)
    
    @staticmethod
    def record_ai_analysis(analysis_type: str, duration: float = None, error_type: str = None):
        """Record AI analysis metrics"""
        ai_analysis_requests_total.labels(analysis_type=analysis_type).inc()
        if duration is not None:
            ai_analysis_duration_seconds.labels(analysis_type=analysis_type).observe(duration)
        if error_type is not None:
            ai_analysis_errors_total.labels(analysis_type=analysis_type, error_type=error_type).inc()
    
    @staticmethod
    def update_websocket_connections(count: int):
        """Update active WebSocket connections count"""
        websocket_connections_active.set(count)
    
    @staticmethod
    def record_websocket_message(direction: str):
        """Record WebSocket message"""
        websocket_messages_total.labels(direction=direction).inc()
    
    @staticmethod
    def record_github_sync(status: str):
        """Record GitHub sync operation"""
        github_sync_operations_total.labels(status=status).inc()
    
    @staticmethod
    def record_github_api_request(endpoint: str, status: int):
        """Record GitHub API request"""
        github_api_requests_total.labels(endpoint=endpoint, status=status).inc()


# ============================================================================
# Context Managers for Metrics
# ============================================================================

class MetricsTimer:
    """Context manager for timing operations and recording metrics"""
    
    def __init__(self, metric_func, *args, **kwargs):
        """
        Initialize timer.
        
        Args:
            metric_func: Function to call with duration
            *args: Arguments to pass to metric_func
            **kwargs: Keyword arguments to pass to metric_func
        """
        self.metric_func = metric_func
        self.args = args
        self.kwargs = kwargs
        self.start_time = None
    
    def __enter__(self):
        """Start timer"""
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and record metric"""
        duration = time.time() - self.start_time
        self.metric_func(*self.args, duration=duration, **self.kwargs)
        return False


# Export commonly used items
__all__ = [
    'registry',
    'get_metrics',
    'get_metrics_content_type',
    'MetricsCollector',
    'MetricsTimer',
    # Individual metrics for direct access if needed
    'http_requests_total',
    'http_request_duration_seconds',
    'mcp_tools_total',
    'active_deployments',
    'cache_hit_rate',
    'celery_tasks_total',
    'documents_total',
    'websocket_connections_active',
]
