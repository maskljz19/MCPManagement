"""Unit tests for async execution functionality in MCPExecutor"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import datetime

from app.services.mcp_executor import MCPExecutor
from app.schemas.mcp_execution import ExecutionOptions


@pytest.mark.asyncio
async def test_execute_async_returns_execution_id():
    """Test that execute_async returns an execution ID immediately"""
    # Setup mocks
    mock_mcp_manager = AsyncMock()
    mock_mongo_db = MagicMock()
    mock_redis = AsyncMock()
    
    # Mock collection
    mock_collection = AsyncMock()
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="test_id"))
    mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    # Create executor
    executor = MCPExecutor(
        mcp_manager=mock_mcp_manager,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )
    
    # Execute async
    tool_id = uuid4()
    user_id = uuid4()
    
    result = await executor.execute_async(
        tool_id=tool_id,
        tool_name="test_tool",
        arguments={"arg1": "value1"},
        user_id=user_id,
        options=ExecutionOptions(mode="async")
    )
    
    # Verify result structure
    assert "execution_id" in result
    assert "tool_id" in result
    assert "status" in result
    assert result["status"] == "queued"
    assert result["tool_name"] == "test_tool"
    
    # Verify Redis was called to store status
    assert mock_redis.set.called
    assert mock_redis.hset.called


@pytest.mark.asyncio
async def test_get_execution_status_from_redis():
    """Test that get_execution_status retrieves status from Redis"""
    # Setup mocks
    mock_mcp_manager = AsyncMock()
    mock_mongo_db = MagicMock()
    mock_redis = AsyncMock()
    
    # Mock Redis response
    execution_id = uuid4()
    mock_redis.hgetall = AsyncMock(return_value={
        "execution_id": str(execution_id),
        "tool_id": str(uuid4()),
        "tool_name": "test_tool",
        "user_id": str(uuid4()),
        "status": "running",
        "queued_at": datetime.utcnow().isoformat(),
        "started_at": datetime.utcnow().isoformat()
    })
    
    # Mock collection
    mock_collection = AsyncMock()
    mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    # Create executor
    executor = MCPExecutor(
        mcp_manager=mock_mcp_manager,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )
    
    # Get status
    status = await executor.get_execution_status(execution_id)
    
    # Verify status
    assert status.execution_id == str(execution_id)
    assert status.status == "running"
    assert status.tool_name == "test_tool"
    
    # Verify Redis was queried
    assert mock_redis.hgetall.called


@pytest.mark.asyncio
async def test_cancel_execution_queued():
    """Test cancelling a queued execution"""
    # Setup mocks
    mock_mcp_manager = AsyncMock()
    mock_mongo_db = MagicMock()
    mock_redis = AsyncMock()
    
    execution_id = uuid4()
    user_id = uuid4()
    
    # Mock Redis response for status check
    mock_redis.hgetall = AsyncMock(return_value={
        "execution_id": str(execution_id),
        "tool_id": str(uuid4()),
        "tool_name": "test_tool",
        "user_id": str(user_id),
        "status": "queued",
        "queued_at": datetime.utcnow().isoformat()
    })
    
    # Mock collection
    mock_collection = AsyncMock()
    mock_collection.update_one = AsyncMock()
    mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    # Create executor
    executor = MCPExecutor(
        mcp_manager=mock_mcp_manager,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )
    
    # Cancel execution
    result = await executor.cancel_execution(
        execution_id=execution_id,
        user_id=user_id
    )
    
    # Verify cancellation succeeded
    assert result is True
    
    # Verify status was updated to cancelled
    assert mock_redis.set.called
    assert mock_collection.update_one.called


@pytest.mark.asyncio
async def test_cancel_execution_wrong_user():
    """Test that cancellation fails if user doesn't own execution"""
    # Setup mocks
    mock_mcp_manager = AsyncMock()
    mock_mongo_db = MagicMock()
    mock_redis = AsyncMock()
    
    execution_id = uuid4()
    user_id = uuid4()
    different_user_id = uuid4()
    
    # Mock Redis response for status check
    mock_redis.hgetall = AsyncMock(return_value={
        "execution_id": str(execution_id),
        "tool_id": str(uuid4()),
        "tool_name": "test_tool",
        "user_id": str(user_id),  # Different user
        "status": "running",
        "queued_at": datetime.utcnow().isoformat()
    })
    
    # Mock collection
    mock_collection = AsyncMock()
    mock_mongo_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    # Create executor
    executor = MCPExecutor(
        mcp_manager=mock_mcp_manager,
        mongo_db=mock_mongo_db,
        redis_client=mock_redis
    )
    
    # Attempt to cancel execution with wrong user
    from app.core.exceptions import MCPExecutionError
    with pytest.raises(MCPExecutionError) as exc_info:
        await executor.cancel_execution(
            execution_id=execution_id,
            user_id=different_user_id
        )
    
    assert "permission" in str(exc_info.value).lower()
