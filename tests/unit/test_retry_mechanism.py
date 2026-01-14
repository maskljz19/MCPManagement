"""Unit tests for retry mechanism in MCPExecutor"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.services.mcp_executor import MCPExecutor
from app.schemas.mcp_execution import RetryPolicy
from app.core.exceptions import MCPExecutionError


@pytest.fixture
def mock_mcp_manager():
    """Mock MCP Manager"""
    manager = AsyncMock()
    
    # Mock tool configuration
    mock_tool = MagicMock()
    mock_tool.id = uuid4()
    mock_tool.name = "test-tool"
    mock_tool.config = {
        "command": "python",
        "args": ["-c", "print('test')"],
        "env": {}
    }
    
    manager.get_tool = AsyncMock(return_value=mock_tool)
    return manager


@pytest.fixture
def mock_mongo_db():
    """Mock MongoDB"""
    db = MagicMock()
    collection = AsyncMock()
    collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
    collection.update_one = AsyncMock()
    collection.find_one = AsyncMock()
    db.__getitem__ = MagicMock(return_value=collection)
    return db


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    redis = AsyncMock()
    redis.set = AsyncMock()
    redis.hset = AsyncMock()
    redis.hgetall = AsyncMock(return_value={})
    redis.expire = AsyncMock()
    return redis


@pytest.fixture
def executor(mock_mcp_manager, mock_mongo_db, mock_redis):
    """Create MCPExecutor instance with mocks"""
    return MCPExecutor(
        mcp_manager=mock_mcp_manager,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )


@pytest.mark.asyncio
async def test_classify_error_timeout(executor):
    """Test error classification for timeout errors"""
    # Test asyncio.TimeoutError
    import asyncio
    error_type = executor._classify_error(asyncio.TimeoutError())
    assert error_type == "timeout"
    
    # Test error message with "timeout"
    error_type = executor._classify_error(Exception("Connection timed out"))
    assert error_type == "timeout"


@pytest.mark.asyncio
async def test_classify_error_connection(executor):
    """Test error classification for connection errors"""
    error_type = executor._classify_error(Exception("Connection refused"))
    assert error_type == "connection_error"
    
    error_type = executor._classify_error(Exception("Host unreachable"))
    assert error_type == "connection_error"


@pytest.mark.asyncio
async def test_classify_error_validation(executor):
    """Test error classification for validation errors"""
    error_type = executor._classify_error(Exception("Invalid parameter"))
    assert error_type == "validation_error"
    
    error_type = executor._classify_error(Exception("Schema validation failed"))
    assert error_type == "validation_error"


@pytest.mark.asyncio
async def test_classify_error_permission(executor):
    """Test error classification for permission errors"""
    error_type = executor._classify_error(Exception("Permission denied"))
    assert error_type == "permission_error"
    
    error_type = executor._classify_error(Exception("403 Forbidden"))
    assert error_type == "permission_error"


@pytest.mark.asyncio
async def test_is_retryable_error(executor):
    """Test retryable error determination"""
    retry_policy = RetryPolicy()
    
    # Retryable errors
    assert executor._is_retryable_error("timeout", retry_policy) is True
    assert executor._is_retryable_error("connection_error", retry_policy) is True
    assert executor._is_retryable_error("temporary_failure", retry_policy) is True
    
    # Non-retryable errors
    assert executor._is_retryable_error("validation_error", retry_policy) is False
    assert executor._is_retryable_error("permission_error", retry_policy) is False
    assert executor._is_retryable_error("not_found_error", retry_policy) is False


@pytest.mark.asyncio
async def test_calculate_retry_delay_exponential_backoff(executor):
    """Test exponential backoff calculation"""
    retry_policy = RetryPolicy(
        initial_delay_seconds=1.0,
        backoff_multiplier=2.0,
        max_delay_seconds=60.0
    )
    
    # First retry: 1.0 * (2.0 ^ 0) = 1.0
    delay = executor._calculate_retry_delay(0, retry_policy)
    assert delay == 1.0
    
    # Second retry: 1.0 * (2.0 ^ 1) = 2.0
    delay = executor._calculate_retry_delay(1, retry_policy)
    assert delay == 2.0
    
    # Third retry: 1.0 * (2.0 ^ 2) = 4.0
    delay = executor._calculate_retry_delay(2, retry_policy)
    assert delay == 4.0
    
    # Fourth retry: 1.0 * (2.0 ^ 3) = 8.0
    delay = executor._calculate_retry_delay(3, retry_policy)
    assert delay == 8.0


@pytest.mark.asyncio
async def test_calculate_retry_delay_max_cap(executor):
    """Test that retry delay is capped at max_delay_seconds"""
    retry_policy = RetryPolicy(
        initial_delay_seconds=10.0,
        backoff_multiplier=3.0,
        max_delay_seconds=30.0
    )
    
    # Large attempt number should be capped
    # 10.0 * (3.0 ^ 5) = 2430.0, but should be capped at 30.0
    delay = executor._calculate_retry_delay(5, retry_policy)
    assert delay == 30.0


@pytest.mark.asyncio
async def test_retry_policy_default_values():
    """Test RetryPolicy default values"""
    policy = RetryPolicy()
    
    assert policy.max_attempts == 3
    assert policy.initial_delay_seconds == 1.0
    assert policy.max_delay_seconds == 60.0
    assert policy.backoff_multiplier == 2.0
    assert "timeout" in policy.retryable_errors
    assert "connection_error" in policy.retryable_errors
    assert "temporary_failure" in policy.retryable_errors


@pytest.mark.asyncio
async def test_retry_policy_custom_values():
    """Test RetryPolicy with custom values"""
    policy = RetryPolicy(
        max_attempts=5,
        initial_delay_seconds=2.0,
        max_delay_seconds=120.0,
        backoff_multiplier=3.0,
        retryable_errors=["timeout", "custom_error"]
    )
    
    assert policy.max_attempts == 5
    assert policy.initial_delay_seconds == 2.0
    assert policy.max_delay_seconds == 120.0
    assert policy.backoff_multiplier == 3.0
    assert policy.retryable_errors == ["timeout", "custom_error"]


@pytest.mark.asyncio
async def test_record_retry_metadata(executor, mock_redis, mock_mongo_db):
    """Test recording retry metadata"""
    execution_id = uuid4()
    retry_count = 3
    
    await executor._record_retry_metadata(execution_id, retry_count)
    
    # Verify Redis was updated
    mock_redis.hset.assert_called_once_with(
        f"execution:{execution_id}:metadata",
        "retry_count",
        "3"
    )
    
    # Verify MongoDB was updated
    collection = mock_mongo_db["mcp_execution_logs"]
    collection.update_one.assert_called_once()
    call_args = collection.update_one.call_args
    assert call_args[0][0] == {"execution_id": str(execution_id)}
    assert call_args[0][1]["$set"]["retry_count"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
