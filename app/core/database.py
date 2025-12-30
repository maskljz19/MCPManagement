"""Database configuration and connection management"""

from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, AsyncAdaptedQueuePool
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from redis.asyncio import Redis, ConnectionPool
from app.core.config import settings

# Import Base from models (defined in models/base.py)
# This ensures all models are registered with the same Base
from app.models.base import Base

# MySQL async engine
mysql_engine: Optional[AsyncEngine] = None
async_session_factory: Optional[sessionmaker] = None

# MongoDB client
mongo_client: Optional[AsyncIOMotorClient] = None
mongo_db: Optional[AsyncIOMotorDatabase] = None

# Redis client
redis_client: Optional[Redis] = None
redis_pool: Optional[ConnectionPool] = None


def get_mysql_url() -> str:
    """Construct MySQL connection URL"""
    return (
        f"mysql+aiomysql://{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}"
        f"@{settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}"
    )


async def init_mysql() -> None:
    """Initialize MySQL async engine and session factory"""
    global mysql_engine, async_session_factory
    
    mysql_url = get_mysql_url()
    
    # Create async engine with connection pooling
    mysql_engine = create_async_engine(
        mysql_url,
        echo=settings.DEBUG,
        pool_size=10,  # Maximum number of connections in the pool
        max_overflow=20,  # Maximum overflow connections beyond pool_size
        pool_timeout=30,  # Timeout for getting connection from pool
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Verify connections before using
        poolclass=AsyncAdaptedQueuePool,
    )
    
    # Create async session factory
    async_session_factory = sessionmaker(
        mysql_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def close_mysql() -> None:
    """Close MySQL engine and cleanup connections"""
    global mysql_engine
    if mysql_engine:
        await mysql_engine.dispose()
        mysql_engine = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency injection for database sessions.
    
    Usage in FastAPI:
        @app.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_mysql() first.")
    
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session for use in Celery tasks.
    
    Usage:
        async for session in get_async_session():
            # Use session
            pass
    """
    if async_session_factory is None:
        # Initialize if not already done
        await init_mysql()
    
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_mysql_connection() -> bool:
    """
    Check if MySQL connection is healthy.
    Used for health checks.
    """
    if mysql_engine is None:
        return False
    
    try:
        async with mysql_engine.connect() as conn:
            await conn.execute("SELECT 1")
        return True
    except Exception:
        return False


# ============================================================================
# MongoDB Configuration
# ============================================================================

async def init_mongodb() -> None:
    """Initialize MongoDB async client and database"""
    global mongo_client, mongo_db
    
    mongo_client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=50,  # Maximum connections in pool
        minPoolSize=10,  # Minimum connections in pool
        maxIdleTimeMS=45000,  # Close idle connections after 45 seconds
        serverSelectionTimeoutMS=5000,  # Timeout for server selection
    )
    
    mongo_db = mongo_client[settings.MONGODB_DATABASE]


async def close_mongodb() -> None:
    """Close MongoDB client and cleanup connections"""
    global mongo_client
    if mongo_client:
        mongo_client.close()
        mongo_client = None


def get_mongodb() -> AsyncIOMotorDatabase:
    """
    Get MongoDB database instance.
    
    Usage:
        db = get_mongodb()
        collection = db["my_collection"]
        await collection.insert_one({"key": "value"})
    """
    if mongo_db is None:
        raise RuntimeError("MongoDB not initialized. Call init_mongodb() first.")
    return mongo_db


def get_mongo_collection(collection_name: str):
    """
    Get a specific MongoDB collection.
    
    Usage:
        collection = get_mongo_collection("mcp_config_history")
        await collection.insert_one(document)
    """
    db = get_mongodb()
    return db[collection_name]


async def check_mongodb_connection() -> bool:
    """
    Check if MongoDB connection is healthy.
    Used for health checks.
    """
    if mongo_client is None:
        return False
    
    try:
        # Ping the database
        await mongo_client.admin.command('ping')
        return True
    except Exception:
        return False


# ============================================================================
# Redis Configuration
# ============================================================================

def get_redis_url() -> str:
    """Construct Redis connection URL"""
    if settings.REDIS_PASSWORD:
        return (
            f"redis://:{settings.REDIS_PASSWORD}@{settings.REDIS_HOST}:"
            f"{settings.REDIS_PORT}/{settings.REDIS_DB}"
        )
    return f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"


async def init_redis() -> None:
    """Initialize Redis async client with connection pooling and retry logic"""
    global redis_client, redis_pool
    
    redis_url = get_redis_url()
    
    # Create connection pool
    redis_pool = ConnectionPool.from_url(
        redis_url,
        max_connections=50,  # Maximum connections in pool
        decode_responses=True,  # Automatically decode responses to strings
        socket_connect_timeout=5,  # Connection timeout
        socket_keepalive=True,  # Enable TCP keepalive
        retry_on_timeout=True,  # Retry on timeout
        health_check_interval=30,  # Health check every 30 seconds
    )
    
    # Create Redis client
    redis_client = Redis(connection_pool=redis_pool)
    
    # Test connection with retry logic
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            await redis_client.ping()
            break
        except Exception as e:
            if attempt == max_retries - 1:
                # Last attempt failed, raise exception
                raise RuntimeError(f"Failed to connect to Redis after {max_retries} attempts: {e}")
            # Wait before retrying
            import asyncio
            await asyncio.sleep(retry_delay * (attempt + 1))


async def close_redis() -> None:
    """Close Redis client and cleanup connections"""
    global redis_client, redis_pool
    if redis_client:
        await redis_client.close()
        redis_client = None
    if redis_pool:
        await redis_pool.disconnect()
        redis_pool = None


def get_redis() -> Redis:
    """
    Get Redis client instance.
    
    Usage:
        redis = get_redis()
        await redis.set("key", "value")
        value = await redis.get("key")
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client


async def check_redis_connection() -> bool:
    """
    Check if Redis connection is healthy.
    Used for health checks.
    """
    if redis_client is None:
        return False
    
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False


# ============================================================================
# Helper Functions for Celery Tasks
# ============================================================================

def get_mongodb_client() -> AsyncIOMotorClient:
    """
    Get MongoDB client for Celery tasks.
    Creates a new client if not initialized.
    """
    global mongo_client
    if mongo_client is None:
        mongo_client = AsyncIOMotorClient(
            settings.MONGODB_URL,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=45000,
            serverSelectionTimeoutMS=5000,
        )
    return mongo_client


def get_redis_client() -> Redis:
    """
    Get Redis client for Celery tasks.
    Creates a new client if not initialized.
    """
    global redis_client, redis_pool
    if redis_client is None:
        redis_url = get_redis_url()
        redis_pool = ConnectionPool.from_url(
            redis_url,
            max_connections=50,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )
        redis_client = Redis(connection_pool=redis_pool)
    return redis_client
