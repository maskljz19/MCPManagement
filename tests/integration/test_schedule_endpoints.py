"""Integration tests for Schedule endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserModel, UserRole
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.models.scheduled_execution import ScheduledExecutionModel
from app.core.security import hash_password
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_schedule_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful schedule creation"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="scheduler_user",
        email="scheduler@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login to get access token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create schedule
    schedule_data = {
        "tool_id": tool.id,
        "tool_name": "Test Tool",
        "arguments": {"param1": "value1"},
        "schedule_expression": "0 0 * * *"  # Daily at midnight
    }
    
    response = await client.post(
        "/api/v1/schedule",
        json=schedule_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["tool_id"] == tool.id
    assert data["tool_name"] == "Test Tool"
    assert data["schedule_expression"] == "0 0 * * *"
    assert data["is_active"] is True
    assert "schedule_id" in data
    assert "next_execution_at" in data
    
    # Verify schedule was created in database
    stmt = select(ScheduledExecutionModel).where(
        ScheduledExecutionModel.id == data["schedule_id"]
    )
    result = await db_session.execute(stmt)
    schedule = result.scalar_one_or_none()
    assert schedule is not None
    assert schedule.tool_id == tool.id
    assert schedule.is_active is True


@pytest.mark.asyncio
async def test_create_schedule_invalid_cron(client: AsyncClient, db_session: AsyncSession):
    """Test schedule creation with invalid cron expression fails"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="scheduler_user2",
        email="scheduler2@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 2",
        slug="test-tool-2",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user2",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to create schedule with invalid cron
    schedule_data = {
        "tool_id": tool.id,
        "tool_name": "Test Tool 2",
        "arguments": {},
        "schedule_expression": "invalid cron"
    }
    
    response = await client.post(
        "/api/v1/schedule",
        json=schedule_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_list_schedules(client: AsyncClient, db_session: AsyncSession):
    """Test listing schedules"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="scheduler_user3",
        email="scheduler3@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 3",
        slug="test-tool-3",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user3",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create two schedules
    for i in range(2):
        schedule_data = {
            "tool_id": tool.id,
            "tool_name": "Test Tool 3",
            "arguments": {"index": i},
            "schedule_expression": "0 0 * * *"
        }
        await client.post(
            "/api/v1/schedule",
            json=schedule_data,
            headers={"Authorization": f"Bearer {access_token}"}
        )
    
    # List schedules
    response = await client.get(
        "/api/v1/schedule",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "schedules" in data
    assert "total" in data
    assert data["total"] == 2
    assert len(data["schedules"]) == 2


@pytest.mark.asyncio
async def test_get_schedule(client: AsyncClient, db_session: AsyncSession):
    """Test getting a specific schedule"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="scheduler_user4",
        email="scheduler4@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 4",
        slug="test-tool-4",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user4",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create schedule
    schedule_data = {
        "tool_id": tool.id,
        "tool_name": "Test Tool 4",
        "arguments": {"test": "data"},
        "schedule_expression": "*/5 * * * *"
    }
    create_response = await client.post(
        "/api/v1/schedule",
        json=schedule_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    schedule_id = create_response.json()["schedule_id"]
    
    # Get schedule
    response = await client.get(
        f"/api/v1/schedule/{schedule_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["schedule_id"] == schedule_id
    assert data["tool_id"] == tool.id
    assert data["schedule_expression"] == "*/5 * * * *"


@pytest.mark.asyncio
async def test_delete_schedule(client: AsyncClient, db_session: AsyncSession):
    """Test deleting a schedule"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="scheduler_user5",
        email="scheduler5@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 5",
        slug="test-tool-5",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user5",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create schedule
    schedule_data = {
        "tool_id": tool.id,
        "tool_name": "Test Tool 5",
        "arguments": {},
        "schedule_expression": "0 0 * * *"
    }
    create_response = await client.post(
        "/api/v1/schedule",
        json=schedule_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    schedule_id = create_response.json()["schedule_id"]
    
    # Delete schedule
    response = await client.delete(
        f"/api/v1/schedule/{schedule_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    
    # Verify schedule was deleted
    stmt = select(ScheduledExecutionModel).where(
        ScheduledExecutionModel.id == schedule_id
    )
    result = await db_session.execute(stmt)
    schedule = result.scalar_one_or_none()
    assert schedule is None


@pytest.mark.asyncio
async def test_delete_schedule_unauthorized(client: AsyncClient, db_session: AsyncSession):
    """Test deleting another user's schedule fails"""
    # Create two users
    user1 = UserModel(
        id=str(uuid4()),
        username="scheduler_user6",
        email="scheduler6@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    user2 = UserModel(
        id=str(uuid4()),
        username="scheduler_user7",
        email="scheduler7@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user1)
    db_session.add(user2)
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool 6",
        slug="test-tool-6",
        description="A test tool",
        version="1.0.0",
        config={"servers": [], "tools": []},
        author_id=user1.id,
        status=ToolStatus.PUBLISHED
    )
    db_session.add(tool)
    await db_session.commit()
    
    # User 1 creates schedule
    login_response1 = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user6",
        "password": "TestPass123"
    })
    access_token1 = login_response1.json()["access_token"]
    
    schedule_data = {
        "tool_id": tool.id,
        "tool_name": "Test Tool 6",
        "arguments": {},
        "schedule_expression": "0 0 * * *"
    }
    create_response = await client.post(
        "/api/v1/schedule",
        json=schedule_data,
        headers={"Authorization": f"Bearer {access_token1}"}
    )
    schedule_id = create_response.json()["schedule_id"]
    
    # User 2 tries to delete user 1's schedule
    login_response2 = await client.post("/api/v1/auth/login", json={
        "username": "scheduler_user7",
        "password": "TestPass123"
    })
    access_token2 = login_response2.json()["access_token"]
    
    response = await client.delete(
        f"/api/v1/schedule/{schedule_id}",
        headers={"Authorization": f"Bearer {access_token2}"}
    )
    
    assert response.status_code == 404  # Not found (unauthorized)


@pytest.mark.asyncio
async def test_create_schedule_unauthorized(client: AsyncClient):
    """Test schedule creation without authentication fails"""
    schedule_data = {
        "tool_id": str(uuid4()),
        "tool_name": "Test Tool",
        "arguments": {},
        "schedule_expression": "0 0 * * *"
    }
    
    response = await client.post("/api/v1/schedule", json=schedule_data)
    
    assert response.status_code == 403  # No authorization header
