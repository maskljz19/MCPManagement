"""Integration tests for async execution endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserModel, UserRole
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.core.security import hash_password
from uuid import uuid4


@pytest.mark.asyncio
async def test_get_execution_details_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting full execution details"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="execuser",
        email="execuser@example.com",
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
        "username": "execuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute tool asynchronously
    exec_response = await client.post(
        f"/api/v1/mcps/{tool.id}/execute/async",
        json={
            "tool_name": "test_tool",
            "arguments": {"test": "value"},
            "timeout": 30
        },
        headers=headers
    )
    
    assert exec_response.status_code == 200
    execution_id = exec_response.json()["execution_id"]
    
    # Get execution details
    details_response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}",
        headers=headers
    )
    
    assert details_response.status_code == 200
    data = details_response.json()
    assert data["execution_id"] == execution_id
    assert data["tool_id"] == str(tool.id)
    assert data["user_id"] == str(user.id)
    assert "status" in data
    assert "queued_at" in data


@pytest.mark.asyncio
async def test_get_execution_details_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting execution details for non-existent execution"""
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
    
    # Try to get non-existent execution
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/mcps/executions/{fake_id}",
        headers=headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_execution_details_forbidden(client: AsyncClient, db_session: AsyncSession):
    """Test getting execution details for another user's execution"""
    # Create two users
    user1 = UserModel(
        id=str(uuid4()),
        username="user1",
        email="user1@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    user2 = UserModel(
        id=str(uuid4()),
        username="user2",
        email="user2@example.com",
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
        slug="test-tool-2",
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
    
    # Login as user1
    login1_response = await client.post("/api/v1/auth/login", json={
        "username": "user1",
        "password": "TestPass123"
    })
    token1 = login1_response.json()["access_token"]
    
    # Execute tool as user1
    exec_response = await client.post(
        f"/api/v1/mcps/{tool.id}/execute/async",
        json={
            "tool_name": "test_tool",
            "arguments": {"test": "value"},
            "timeout": 30
        },
        headers={"Authorization": f"Bearer {token1}"}
    )
    
    execution_id = exec_response.json()["execution_id"]
    
    # Login as user2
    login2_response = await client.post("/api/v1/auth/login", json={
        "username": "user2",
        "password": "TestPass123"
    })
    token2 = login2_response.json()["access_token"]
    
    # Try to get user1's execution as user2
    response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}",
        headers={"Authorization": f"Bearer {token2}"}
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_execution_logs_success(client: AsyncClient, db_session: AsyncSession):
    """Test getting execution logs"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="loguser",
        email="loguser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool-logs",
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
        "username": "loguser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Execute tool asynchronously
    exec_response = await client.post(
        f"/api/v1/mcps/{tool.id}/execute/async",
        json={
            "tool_name": "test_tool",
            "arguments": {"test": "value"},
            "timeout": 30
        },
        headers=headers
    )
    
    execution_id = exec_response.json()["execution_id"]
    
    # Get execution logs
    logs_response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}/logs",
        headers=headers
    )
    
    assert logs_response.status_code == 200
    data = logs_response.json()
    assert data["execution_id"] == execution_id
    assert data["tool_id"] == str(tool.id)
    assert data["user_id"] == str(user.id)
    assert "status" in data
    assert "start_time" in data
    assert "logs" in data


@pytest.mark.asyncio
async def test_get_execution_logs_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting logs for non-existent execution"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="nologsuser",
        email="nologs@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "nologsuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # Try to get logs for non-existent execution
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/mcps/executions/{fake_id}/logs",
        headers=headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_async_execution_workflow(client: AsyncClient, db_session: AsyncSession):
    """Test complete async execution workflow"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="asyncuser",
        email="asyncuser@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Async Test Tool",
        slug="async-test-tool",
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
        "username": "asyncuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Execute tool asynchronously
    exec_response = await client.post(
        f"/api/v1/mcps/{tool.id}/execute/async",
        json={
            "tool_name": "test_tool",
            "arguments": {"test": "value"},
            "timeout": 30
        },
        headers=headers
    )
    
    assert exec_response.status_code == 200
    exec_data = exec_response.json()
    assert "execution_id" in exec_data
    assert exec_data["status"] == "queued"
    execution_id = exec_data["execution_id"]
    
    # 2. Get execution status
    status_response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}/status",
        headers=headers
    )
    
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["execution_id"] == execution_id
    assert status_data["status"] in ["queued", "running", "success", "error"]
    
    # 3. Get full execution details
    details_response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}",
        headers=headers
    )
    
    assert details_response.status_code == 200
    details_data = details_response.json()
    assert details_data["execution_id"] == execution_id
    assert details_data["tool_id"] == str(tool.id)
    
    # 4. Get execution logs
    logs_response = await client.get(
        f"/api/v1/mcps/executions/{execution_id}/logs",
        headers=headers
    )
    
    assert logs_response.status_code == 200
    logs_data = logs_response.json()
    assert logs_data["execution_id"] == execution_id
    assert "logs" in logs_data
