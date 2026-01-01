"""FastAPI Application Entry Point"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from pathlib import Path

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
from app.api.exception_handlers import register_exception_handlers
from app.core.config import settings
from app.core.database import (
    init_mysql, close_mysql,
    init_mongodb, close_mongodb,
    init_redis, close_redis
)
from app.core.logging_config import get_logger


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup: Initialize database connections
    logger.info("application_startup_initiated")
    await init_mysql()
    await init_mongodb()
    await init_redis()
    logger.info("application_startup_completed")
    yield
    # Shutdown: Close database connections
    logger.info("application_shutdown_initiated")
    await close_mysql()
    await close_mongodb()
    await close_redis()
    logger.info("application_shutdown_completed")


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

# Register comprehensive exception handlers for authentication enum fix
# This includes RoleValidationError, AuthenticationError, TokenValidationError, etc.
register_exception_handlers(app)

logger.info(
    "application_initialized",
    title=app.title,
    version=app.version,
    environment=settings.ENVIRONMENT
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
# Health router is included twice: once with prefix for API consistency,
# and once without prefix for Docker healthcheck compatibility
app.include_router(health.router, prefix="/api/v1")
app.include_router(health.router)  # No prefix for /health/simple
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(mcps.router, prefix="/api/v1")
app.include_router(knowledge.router, prefix="/api/v1")
app.include_router(analyze.router, prefix="/api/v1")
app.include_router(github.router, prefix="/api/v1")
app.include_router(deployments.router, prefix="/api/v1")
app.include_router(websocket.router, prefix="/api/v1")


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
    """Root endpoint - serve frontend index.html"""
    frontend_path = Path(__file__).parent.parent / "frontend" / "dist"
    index_file = frontend_path / "index.html"
    
    if index_file.exists():
        return FileResponse(index_file)
    else:
        return {"message": "MCP Platform API", "version": "1.0.0"}


# Mount static files for frontend (must be after API routes)
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    # Mount static assets (js, css, images, etc.)
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    # Catch-all route for SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Serve SPA for all non-API routes.
        This handles client-side routing for React Router.
        """
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path.startswith("mcp/"):
            raise HTTPException(status_code=404, detail="Not found")
        
        # Serve index.html for all other routes
        index_file = frontend_dist / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        else:
            raise HTTPException(status_code=404, detail="Frontend not found")
    
    logger.info("frontend_static_files_mounted", path=str(frontend_dist))
else:
    logger.warning("frontend_dist_not_found", expected_path=str(frontend_dist))

