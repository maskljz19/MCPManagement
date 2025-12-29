"""FastAPI Application Entry Point"""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.api.v1 import health
from app.core.config import settings
from app.core.database import (
    init_mysql, close_mysql,
    init_mongodb, close_mongodb,
    init_redis, close_redis,
    init_qdrant, close_qdrant
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup: Initialize database connections
    await init_mysql()
    await init_mongodb()
    await init_redis()
    await init_qdrant()
    yield
    # Shutdown: Close database connections
    await close_mysql()
    await close_mongodb()
    await close_redis()
    await close_qdrant()


app = FastAPI(
    title="MCP Platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# Include routers
app.include_router(health.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "MCP Platform API", "version": "1.0.0"}
