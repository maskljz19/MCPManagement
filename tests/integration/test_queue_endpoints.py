"""Integration tests for queue management endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserModel, UserRole
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.models.execution_queue import ExecutionQueueModel, QueueStatus
from app.core.security import hash_password
from uuid import uuid4
from datetime import datetime


@pytest.mark.asyncio
async def test_get_queue_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue list"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="queueuser",
        email="queueuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test"],
            "env": {}
        }
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Create queued executions
    execution1 = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user.id),
        tool_name="test_tool",
        arguments={"test": "value1"},
        options={"mode": "async", "timeout": 30},
        priority=5,
        status=QueueStatus.QUEUED,
        queue_position=1,
        estimated_wait_seconds=30,
        queued_at=datetime.utcnow()
    )
    execution2 = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user.id),
        tool_name="test_tool",
        arguments={"test": "value2"},
        options={"mode": "async", "timeout": 30},
        priority=3,
        status=QueueStatus.QUEUED,
        queue_position=2,
        estimated_wait_seconds=60,
        queued_at=datetime.utcnow()
    )
    db_session.add(execution1)
    db_session.add(execution2)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "queueuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get queue
    response = await client.get(
        "/api/v1/executions/queue",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "queued" in data
    assert "processing" in data
    assert "executions" in data
    assert data["total"] >= 2
    assert data["queued"] >= 2
    
    # Verify execution data
    executions = data["executions"]
    assert len(executions) >= 2
    
    # Check first execution
    exec_ids = [e["execution_id"] for e in executions]
    assert execution1.id in exec_ids or execution2.id in exec_ids


@pytest.mark.asyncio
async def test_get_queue_with_status_filter(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue with status filter"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="filteruser",
        email="filteruser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool-filter",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test"],
            "env": {}
        }
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Create executions with different statuses
    queued_exec = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user.id),
        tool_name="test_tool",
        arguments={"test": "queued"},
        options={"mode": "async", "timeout": 30},
        priority=5,
        status=QueueStatus.QUEUED,
        queued_at=datetime.utcnow()
    )
    processing_exec = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user.id),
        tool_name="test_tool",
        arguments={"test": "processing"},
        options={"mode": "async", "timeout": 30},
        priority=5,
        status=QueueStatus.PROCESSING,
        queued_at=datetime.utcnow(),
        started_at=datetime.utcnow()
    )
    db_session.add(queued_exec)
    db_session.add(processing_exec)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "filteruser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get queue with queued filter
    response = await client.get(
        "/api/v1/executions/queue?status_filter=queued",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["queued"] >= 1
    
    # All returned executions should be queued
    for execution in data["executions"]:
        if execution["execution_id"] in [queued_exec.id, processing_exec.id]:
            assert execution["status"] == "queued"


@pytest.mark.asyncio
async def test_get_queue_position_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue position for a specific execution"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="positionuser",
        email="positionuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool-position",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test"],
            "env": {}
        }
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Create queued execution
    execution = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user.id),
        tool_name="test_tool",
        arguments={"test": "position"},
        options={"mode": "async", "timeout": 30},
        priority=5,
        status=QueueStatus.QUEUED,
        queue_position=1,
        estimated_wait_seconds=30,
        queued_at=datetime.utcnow()
    )
    db_session.add(execution)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "positionuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Get queue position
    response = await client.get(
        f"/api/v1/executions/queue/position?execution_id={execution.id}",
        headers=headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["execution_id"] == execution.id
    assert "position" in data
    assert "estimated_wait_seconds" in data
    assert "total_queued" in data
    assert data["position"] >= 1


@pytest.mark.asyncio
async def test_get_queue_position_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue position for non-existent execution"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="notfoundqueueuser",
        email="notfoundqueue@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "notfoundqueueuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to get position for non-existent execution
    fake_id = str(uuid4())
    response = await client.get(
        f"/api/v1/executions/queue/position?execution_id={fake_id}",
        headers=headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_queue_position_wrong_user(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue position for another user's execution"""
    # Create two users
    user1 = UserModel(
        id=str(uuid4()),
        username="queueowner",
        email="queueowner@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    user2 = UserModel(
        id=str(uuid4()),
        username="queueother",
        email="queueother@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool-ownership",
        version="1.0.0",
        author_id=str(user1.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test"],
            "env": {}
        }
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Create execution owned by user1
    execution = ExecutionQueueModel(
        id=str(uuid4()),
        tool_id=str(tool.id),
        user_id=str(user1.id),
        tool_name="test_tool",
        arguments={"test": "ownership"},
        options={"mode": "async", "timeout": 30},
        priority=5,
        status=QueueStatus.QUEUED,
        queued_at=datetime.utcnow()
    )
    db_session.add(execution)
    await db_session.commit()
    
    # Login as user2
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "queueother",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to get position for user1's execution
    response = await client.get(
        f"/api/v1/executions/queue/position?execution_id={execution.id}",
        headers=headers
    )
    
    # Should be forbidden
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_queue_invalid_status_filter(client: AsyncClient, db_session: AsyncSession):
    """Test getting queue with invalid status filter"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="invalidfilteruser",
        email="invalidfilter@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "invalidfilteruser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to get queue with invalid status
    response = await client.get(
        "/api/v1/executions/queue?status_filter=invalid_status",
        headers=headers
    )
    
    assert response.status_code == 422
