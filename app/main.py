"""FastAPI Application Entry Point"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response
from fastapi.exceptions import RequestValidationError
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import health, tasks, auth, mcps, knowledge, analyze, github, deployments, websocket
from app.core.database import get_db
from app.api.middleware import (
    UsageStatisticsMiddleware,
    BackgroundTaskManager,
    RequestIDMiddleware,
    LoggingMiddleware,
    ErrorHandlingMiddleware,
    limiter,
    validate_cors_origin
)
from app.core.config import settings
from app.core.database import (
    init_mysql, close_mysql,
    init_mongodb, close_mongodb,
    init_redis, close_redis
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup: Initialize database connections
    await init_mysql()
    await init_mongodb()
    await init_redis()
    yield
    # Shutdown: Close database connections
    await close_mysql()
    await close_mongodb()
    await close_redis()


app = FastAPI(
    title="MCP Platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Initialize background task manager
app.state.background_tasks = BackgroundTaskManager()

# Add rate limiter state
app.state.limiter = limiter

# Add rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle validation errors with detailed field-level information.
    
    **Requirements: 10.3**
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "type": "ValidationError",
                "message": "Request validation failed",
                "details": errors,
                "request_id": getattr(request.state, "request_id", "unknown")
            }
        }
    )

# Add middleware in correct order (LIFO - last added is executed first)
# Order: Error Handler -> Logging -> Request ID -> Usage Stats -> CORS

# 1. CORS Middleware (outermost - handles preflight requests first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 2. Usage Statistics Middleware
app.add_middleware(UsageStatisticsMiddleware)

# 3. Request ID Middleware (must be before logging)
app.add_middleware(RequestIDMiddleware)

# 4. Logging Middleware
app.add_middleware(LoggingMiddleware)

# 5. Error Handling Middleware (innermost - catches all errors)
app.add_middleware(ErrorHandlingMiddleware)

# Include routers
app.include_router(health.router)
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(mcps.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(github.router, prefix="/api/v1")
app.include_router(deployments.router, prefix="/api/v1")
app.include_router(websocket.router)  # WebSocket and SSE endpoints


# Dynamic MCP service routing - catch-all route
@app.api_route(
    "/mcp/{slug}/v1/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
    tags=["mcp-routing"]
)
async def route_mcp_request(
    slug: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Dynamic MCP service routing.
    
    Routes requests to deployed MCP servers based on the tool slug.
    This is a catch-all route that forwards all HTTP methods to the
    appropriate deployed MCP server instance.
    
    **Requirements: 5.2**
    """
    from app.services.mcp_server_manager import MCPServerManager
    
    manager = MCPServerManager(db_session=db)
    
    # Get request body
    body = await request.body()
    
    # Get headers (exclude host and other proxy-specific headers)
    headers = dict(request.headers)
    headers.pop("host", None)
    
    try:
        # Route request to deployed server
        response = await manager.route_request(
            slug=slug,
            path=f"/{path}",
            method=request.method,
            headers=headers,
            body=body if body else None
        )
        
        # Return response from deployed server
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.headers.get("content-type")
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to route request: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MCP Platform API", "version": "1.0.0"}

