"""Shared test fixtures for all tests"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from uuid import uuid4

from app.models.base import Base
from app.services.mcp_manager import MCPManager


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine (in-memory SQLite)"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Cleanup
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session"""
    async_session_factory = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async with async_session_factory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def mongo_client():
    """Create test MongoDB client"""
    # Use a test database
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    test_db_name = f"test_mcp_platform_{uuid4().hex[:8]}"
    
    yield client[test_db_name]
    
    # Cleanup: drop test database
    await client.drop_database(test_db_name)
    client.close()


@pytest_asyncio.fixture
async def redis_client():
    """Create test Redis client"""
    # Use a test database (15 is commonly used for testing)
    redis = Redis(
        host="localhost",
        port=6379,
        db=15,
        decode_responses=True
    )
    
    # Clear the test database
    await redis.flushdb()
    
    yield redis
    
    # Cleanup
    await redis.flushdb()
    await redis.close()


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest_asyncio.fixture
async def mcp_manager_fixture(db_session, mongo_client, redis_client):
    """Create MCPManager instance with test dependencies"""
    manager = MCPManager(
        db_session=db_session,
        mongo_db=mongo_client,
        cache=redis_client
    )
    
    yield manager
    
    # Cleanup is handled by individual fixtures


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers",
        "property: mark test as property-based test"
    )
