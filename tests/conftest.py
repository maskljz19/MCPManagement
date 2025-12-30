"""Shared test fixtures for all tests"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from uuid import uuid4
import os

from app.models.base import Base
from app.services.mcp_manager import MCPManager
from app.services.knowledge_service import KnowledgeBaseService
from app.services.task_tracker import TaskTracker


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
    # Try to connect to MongoDB, but if not available, skip tests
    try:
        # Use a test database
        client = AsyncIOMotorClient(
            "mongodb://localhost:27017",
            serverSelectionTimeoutMS=2000  # 2 second timeout
        )
        test_db_name = f"test_mcp_platform_{uuid4().hex[:8]}"
        
        # Test connection
        await client.admin.command('ping')
        
        yield client[test_db_name]
        
        # Cleanup: drop test database
        await client.drop_database(test_db_name)
        client.close()
    except Exception as e:
        # MongoDB not available, skip tests that require it
        pytest.skip(f"MongoDB not available: {e}")


@pytest_asyncio.fixture
async def redis_client():
    """Create test Redis client"""
    try:
        # Use a test database (15 is commonly used for testing)
        redis = Redis(
            host="localhost",
            port=6379,
            db=15,
            decode_responses=True,
            socket_connect_timeout=2  # 2 second timeout
        )
        
        # Test connection
        await redis.ping()
        
        # Clear the test database
        await redis.flushdb()
        
        yield redis
        
        # Cleanup
        await redis.flushdb()
        await redis.close()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")


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


@pytest_asyncio.fixture
async def knowledge_service_fixture(mongo_client, redis_client):
    """Create KnowledgeBaseService instance with test dependencies"""
    # Get OpenAI API key from environment or use a test key
    openai_api_key = os.getenv("OPENAI_API_KEY", "test-key-for-mocking")
    
    service = KnowledgeBaseService(
        mongo_db=mongo_client,
        redis=redis_client,
        openai_api_key=openai_api_key
    )
    
    yield service
    
    # Cleanup is handled by individual fixtures


@pytest_asyncio.fixture
async def task_tracker_fixture(redis_client):
    """Create TaskTracker instance with test dependencies"""
    tracker = TaskTracker(redis=redis_client)
    
    yield tracker
    
    # Cleanup is handled by redis_client fixture


@pytest_asyncio.fixture
async def mcp_server_manager_fixture(db_session):
    """Create MCPServerManager instance with test dependencies"""
    from app.services.mcp_server_manager import MCPServerManager
    
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9200
    )
    
    yield manager
    
    # Cleanup: stop all running processes
    for deployment_id in list(manager._processes.keys()):
        try:
            from uuid import UUID
            await manager.stop_server(UUID(deployment_id))
        except:
            pass  # Best effort cleanup


@pytest_asyncio.fixture
async def client(db_engine, redis_client):
    """Create test HTTP client for API integration tests"""
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    from app.core.database import get_db, get_redis
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession
    
    # Override database dependency to use test database
    async_session_factory = sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    
    async def override_get_db():
        async with async_session_factory() as session:
            yield session
    
    async def override_get_redis():
        return redis_client
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis
    
    # Use ASGITransport to connect to the FastAPI app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clear overrides
    app.dependency_overrides.clear()


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
