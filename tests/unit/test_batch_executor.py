"""Unit tests for BatchExecutor"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.batch_executor import (
    BatchExecutor,
    BatchExecutionRequest,
    ToolExecutionConfig,
    BatchExecution,
    BatchStatusInfo
)
from app.models.batch_execution import BatchStatus
from app.schemas.mcp_execution import ExecutionOptions
from app.core.exceptions import MCPExecutionError


@pytest.fixture
def mock_executor():
    """Mock MCP executor"""
    executor = AsyncMock()
    executor.execute_tool = AsyncMock()
    return executor


@pytest.fixture
def mock_db_session():
    """Mock database session"""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB database"""
    db = MagicMock()
    collection = AsyncMock()
    collection.insert_one = AsyncMock()
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.expire = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.hincrby = AsyncMock()
    return redis


@pytest.fixture
def batch_executor(mock_executor, mock_db_session, mock_mongo_db, mock_redis):
    """Create BatchExecutor instance with mocks"""
    return BatchExecutor(
        mcp_executor=mock_executor,
        db_session=mock_db_session,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )
