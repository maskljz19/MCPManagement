"""API Middleware for request processing"""

import time
import re
from typing import Callable
from uuid import uuid4
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.database import get_async_session
from app.models.usage_stat import MCPUsageStatModel
from app.core.config import settings
from app.core.logging_config import get_logger


# Configure structured logging
logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add unique request ID to each request.
    
    Generates a UUID for each request and adds it to:
    - Request state (accessible in route handlers)
    - Response headers (X-Request-ID)
    - Log context
    
    **Requirements: 12.4**
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add request ID"""
        
        # Generate unique request ID
        request_id = str(uuid4())
        
        # Store in request state for access in route handlers
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log all requests and responses with correlation IDs.
    
    Logs structured information including:
    - Request ID (correlation ID)
    - HTTP method and path
    - Request/response timing
    - Status code
    - User ID (if authenticated)
    - Sensitive data redaction
    
    **Requirements: 12.2, 12.4, 11.4**
    """
    
    # Patterns for sensitive data redaction
    SENSITIVE_PATTERNS = [
        (re.compile(r'"password"\s*:\s*"[^"]*"'), '"password": "[REDACTED]"'),
        (re.compile(r'"token"\s*:\s*"[^"]*"'), '"token": "[REDACTED]"'),
        (re.compile(r'"api_key"\s*:\s*"[^"]*"'), '"api_key": "[REDACTED]"'),
        (re.compile(r'"secret"\s*:\s*"[^"]*"'), '"secret": "[REDACTED]"'),
        (re.compile(r'"authorization"\s*:\s*"[^"]*"', re.IGNORECASE), '"authorization": "[REDACTED]"'),
        (re.compile(r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), 'Bearer [REDACTED]'),
    ]
    
    # Paths to exclude from detailed logging (health checks, metrics, etc.)
    EXCLUDED_PATHS = {
        "/health",
        "/metrics",
        "/favicon.ico",
        "/robots.txt"
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details"""
        
        # Get request ID from state (set by RequestIDMiddleware)
        request_id = getattr(request.state, "request_id", "unknown")
        
        # Get user ID if authenticated
        user_id = getattr(request.state, "user_id", None)
        
        # Check if this is a path we should skip detailed logging for
        skip_detailed_logging = (
            request.url.path in self.EXCLUDED_PATHS and 
            not settings.LOG_HEALTH_CHECKS
        )
        
        # Record start time
        start_time = time.time()
        
        # Log request (skip for health checks unless in debug mode)
        if not skip_detailed_logging or settings.DEBUG:
            logger.info(
                "request_started",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                query_params=str(request.query_params),
                user_id=user_id,
                client_host=request.client.host if request.client else None,
            )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            response_time = time.time() - start_time
            
            # Log response (skip for health checks unless in debug mode or error)
            if not skip_detailed_logging or settings.DEBUG or response.status_code >= 400:
                logger.info(
                    "request_completed",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    status_code=response.status_code,
                    response_time_ms=int(response_time * 1000),
                    user_id=user_id,
                )
            
            return response
            
        except Exception as e:
            # Calculate response time
            response_time = time.time() - start_time
            
            # Always log errors, even for health checks
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                error_type=type(e).__name__,
                error_message=self._redact_sensitive_data(str(e)),
                response_time_ms=int(response_time * 1000),
                user_id=user_id,
                exc_info=True
            )
            
            # Re-raise to be handled by error handler
            raise
    
    @classmethod
    def _redact_sensitive_data(cls, text: str) -> str:
        """
        Redact sensitive data from text.
        
        Replaces passwords, tokens, API keys, and other sensitive
        information with [REDACTED] placeholder.
        """
        for pattern, replacement in cls.SENSITIVE_PATTERNS:
            text = pattern.sub(replacement, text)
        return text


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.
    
    Catches all unhandled exceptions and formats them into
    consistent JSON error responses.
    
    **Requirements: 10.3**
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and handle errors"""
        
        try:
            response = await call_next(request)
            return response
            
        except Exception as e:
            # Get request ID for correlation
            request_id = getattr(request.state, "request_id", "unknown")
            
            # Log the error
            logger.error(
                "unhandled_exception",
                request_id=request_id,
                error_type=type(e).__name__,
                error_message=str(e),
                exc_info=True
            )
            
            # Format error response
            error_response = {
                "error": {
                    "type": type(e).__name__,
                    "message": str(e),
                    "request_id": request_id,
                }
            }
            
            # Return JSON error response
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=500,
                content=error_response
            )


class UsageStatisticsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to record API usage statistics for MCP tool endpoints.
    
    Records request details including:
    - Tool ID and deployment ID
    - Endpoint and HTTP method
    - Response status code
    - Response time in milliseconds
    - User ID (if authenticated)
    
    **Requirements: 7.4**
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and record usage statistics"""
        
        # Record start time
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Check if this is an MCP routing request
        if request.url.path.startswith("/mcp/"):
            # Extract slug from path: /mcp/{slug}/v1/...
            path_parts = request.url.path.split("/")
            if len(path_parts) >= 3:
                slug = path_parts[2]
                
                # Record usage statistics asynchronously
                # We don't await this to avoid blocking the response
                request.app.state.background_tasks.add(
                    self._record_usage_stat(
                        slug=slug,
                        endpoint=request.url.path,
                        method=request.method,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms,
                        user_id=getattr(request.state, "user_id", None)
                    )
                )
        
        return response
    
    async def _record_usage_stat(
        self,
        slug: str,
        endpoint: str,
        method: str,
        status_code: int,
        response_time_ms: int,
        user_id: str = None
    ):
        """
        Record usage statistics to database.
        
        This runs in the background to avoid blocking the response.
        """
        try:
            # Get database session
            async for db in get_async_session():
                # Find tool by slug to get tool_id
                from sqlalchemy import select
                from app.models.mcp_tool import MCPToolModel
                
                stmt = select(MCPToolModel).where(
                    MCPToolModel.slug == slug,
                    MCPToolModel.deleted_at.is_(None)
                )
                result = await db.execute(stmt)
                tool = result.scalar_one_or_none()
                
                if tool:
                    # Find active deployment for this tool
                    from app.models.deployment import MCPDeploymentModel, DeploymentStatus
                    
                    stmt = select(MCPDeploymentModel).where(
                        MCPDeploymentModel.tool_id == tool.id,
                        MCPDeploymentModel.status == DeploymentStatus.RUNNING
                    ).limit(1)
                    result = await db.execute(stmt)
                    deployment = result.scalar_one_or_none()
                    
                    # Create usage stat record
                    usage_stat = MCPUsageStatModel(
                        tool_id=tool.id,
                        deployment_id=deployment.id if deployment else None,
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        user_id=user_id
                    )
                    
                    db.add(usage_stat)
                    await db.commit()
                
                break  # Exit the async generator
                
        except Exception as e:
            # Log error but don't fail the request
            logger.error("failed_to_record_usage_statistics", error=str(e))


class BackgroundTaskManager:
    """
    Simple background task manager for non-blocking operations.
    
    Stores tasks in a set and processes them asynchronously.
    """
    
    def __init__(self):
        self.tasks = set()
    
    def add(self, coro):
        """Add a coroutine to be executed in the background"""
        import asyncio
        task = asyncio.create_task(coro)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)


# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)


def validate_cors_origin(origin: str, allowed_origins: list[str]) -> bool:
    """
    Validate CORS origin against whitelist.
    
    Supports exact matches and wildcard patterns.
    
    **Requirements: 11.5**
    """
    if not origin:
        return False
    
    # Check for exact match
    if origin in allowed_origins:
        return True
    
    # Check for wildcard patterns
    for allowed in allowed_origins:
        if "*" in allowed:
            # Convert wildcard pattern to regex
            pattern = allowed.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{pattern}$", origin):
                return True
    
    return False

