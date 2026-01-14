"""Integration tests for batch execution endpoints"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserModel, UserRole
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.core.security import hash_password
from uuid import uuid4


@pytest.mark.asyncio
async def test_execute_batch_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful batch execution"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="batchuser",
        email="batchuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tools
    tool1 = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 1",
        slug="test-tool-1",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test1"],
            "env": {}
        }
    )
    tool2 = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 2",
        slug="test-tool-2",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test2"],
            "env": {}
        }
    )
    db_session.add(tool1)
    db_session.add(tool2)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "batchuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute batch
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [
                {
                    "tool_id": str(tool1.id),
                    "tool_name": "test_tool_1",
                    "arguments": {"test": "value1"}
                },
                {
                    "tool_id": str(tool2.id),
                    "tool_name": "test_tool_2",
                    "arguments": {"test": "value2"}
                }
            ],
            "concurrency_limit": 2,
            "stop_on_error": False
        },
        headers=headers
    )
    
    assert batch_response.status_code == 202
    data = batch_response.json()
    assert "batch_id" in data
    assert data["total_tools"] == 2
    assert data["status"] == "queued"
    assert data["user_id"] == str(user.id)


@pytest.mark.asyncio
async def test_execute_batch_validation_error(client: AsyncClient, db_session: AsyncSession):
    """Test batch execution with validation errors"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="validuser",
        email="validuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "validuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test empty tools list
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [],
            "concurrency_limit": 2
        },
        headers=headers
    )
    
    assert batch_response.status_code == 422


@pytest.mark.asyncio
async def test_execute_batch_too_many_tools(client: AsyncClient, db_session: AsyncSession):
    """Test batch execution with too many tools"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="manyuser",
        email="manyuser@example.com",
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
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "manyuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Test with 51 tools (exceeds limit of 50)
    tools = [
        {
            "tool_id": str(tool.id),
            "tool_name": "test_tool",
            "arguments": {"index": i}
        }
        for i in range(51)
    ]
    
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": tools,
            "concurrency_limit": 5
        },
        headers=headers
    )
    
    assert batch_response.status_code == 422


@pytest.mark.asyncio
async def test_get_batch_status(client: AsyncClient, db_session: AsyncSession):
    """Test getting batch status"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="statususer",
        email="statususer@example.com",
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
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "statususer",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute batch
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [
                {
                    "tool_id": str(tool.id),
                    "tool_name": "test_tool",
                    "arguments": {"test": "value"}
                }
            ],
            "concurrency_limit": 1
        },
        headers=headers
    )
    
    assert batch_response.status_code == 202
    batch_id = batch_response.json()["batch_id"]
    
    # Get batch status
    status_response = await client.get(
        f"/api/v1/batch/{batch_id}",
        headers=headers
    )
    
    assert status_response.status_code == 200
    data = status_response.json()
    assert data["batch_id"] == batch_id
    assert data["total_tools"] == 1
    assert "status" in data
    assert "tool_statuses" in data
    assert len(data["tool_statuses"]) == 1


@pytest.mark.asyncio
async def test_get_batch_status_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting status for non-existent batch"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="notfounduser",
        email="notfound@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "notfounduser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to get non-existent batch
    fake_batch_id = str(uuid4())
    status_response = await client.get(
        f"/api/v1/batch/{fake_batch_id}",
        headers=headers
    )
    
    assert status_response.status_code == 404


@pytest.mark.asyncio
async def test_cancel_batch(client: AsyncClient, db_session: AsyncSession):
    """Test cancelling a batch execution"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="canceluser",
        email="canceluser@example.com",
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
            "command": "sleep",
            "args": ["10"],
            "env": {}
        }
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "canceluser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute batch
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [
                {
                    "tool_id": str(tool.id),
                    "tool_name": "test_tool",
                    "arguments": {"test": "value"}
                }
            ],
            "concurrency_limit": 1
        },
        headers=headers
    )
    
    assert batch_response.status_code == 202
    batch_id = batch_response.json()["batch_id"]
    
    # Wait a moment for batch to start
    await asyncio.sleep(0.5)
    
    # Cancel batch
    cancel_response = await client.delete(
        f"/api/v1/batch/{batch_id}",
        headers=headers
    )
    
    assert cancel_response.status_code == 200
    data = cancel_response.json()
    assert data["batch_id"] == batch_id
    assert "cancelled" in data["message"].lower()


@pytest.mark.asyncio
async def test_cancel_batch_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test cancelling non-existent batch"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="cancelnotfound",
        email="cancelnotfound@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "cancelnotfound",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to cancel non-existent batch
    fake_batch_id = str(uuid4())
    cancel_response = await client.delete(
        f"/api/v1/batch/{fake_batch_id}",
        headers=headers
    )
    
    assert cancel_response.status_code == 404


@pytest.mark.asyncio
async def test_batch_with_stop_on_error(client: AsyncClient, db_session: AsyncSession):
    """Test batch execution with stop_on_error enabled"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="stopuser",
        email="stopuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tools
    tool1 = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 1",
        slug="test-tool-1",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test1"],
            "env": {}
        }
    )
    tool2 = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 2",
        slug="test-tool-2",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE,
        config={
            "command": "echo",
            "args": ["test2"],
            "env": {}
        }
    )
    db_session.add(tool1)
    db_session.add(tool2)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "stopuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute batch with stop_on_error
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [
                {
                    "tool_id": str(tool1.id),
                    "tool_name": "test_tool_1",
                    "arguments": {"test": "value1"}
                },
                {
                    "tool_id": str(tool2.id),
                    "tool_name": "test_tool_2",
                    "arguments": {"test": "value2"}
                }
            ],
            "concurrency_limit": 1,
            "stop_on_error": True
        },
        headers=headers
    )
    
    assert batch_response.status_code == 202
    data = batch_response.json()
    assert data["stop_on_error"] is True


@pytest.mark.asyncio
async def test_batch_with_custom_execution_options(client: AsyncClient, db_session: AsyncSession):
    """Test batch execution with custom execution options"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="optionsuser",
        email="optionsuser@example.com",
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
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "optionsuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute batch with custom options
    batch_response = await client.post(
        "/api/v1/batch/execute",
        json={
            "tools": [
                {
                    "tool_id": str(tool.id),
                    "tool_name": "test_tool",
                    "arguments": {"test": "value"}
                }
            ],
            "concurrency_limit": 1,
            "execution_options": {
                "timeout": 60,
                "priority": 8,
                "cache_enabled": False,
                "retry_policy": {
                    "max_attempts": 2,
                    "initial_delay_seconds": 1.0
                }
            }
        },
        headers=headers
    )
    
    assert batch_response.status_code == 202
