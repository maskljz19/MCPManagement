"""Integration tests for MCP tool management endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import UserModel, UserRole
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.core.security import hash_password
from uuid import uuid4


@pytest.mark.asyncio
async def test_create_mcp_tool_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful MCP tool creation"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="toolcreator",
        email="creator@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get access token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "toolcreator",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Create MCP tool
    tool_data = {
        "name": "Test Tool",
        "slug": "test-tool",
        "description": "A test MCP tool",
        "version": "1.0.0",
        "config": {"servers": [], "tools": []},
        "author_id": str(user.id),
        "status": "draft"
    }
    
    response = await client.post(
        "/api/v1/mcps",
        json=tool_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Tool"
    assert data["slug"] == "test-tool"
    assert data["version"] == "1.0.0"
    assert data["status"] == "DRAFT"
    assert "id" in data
    
    # Verify tool was created in database
    stmt = select(MCPToolModel).where(MCPToolModel.slug == "test-tool")
    result = await db_session.execute(stmt)
    tool = result.scalar_one_or_none()
    assert tool is not None
    assert tool.name == "Test Tool"


@pytest.mark.asyncio
async def test_create_mcp_tool_unauthorized(client: AsyncClient):
    """Test MCP tool creation without authentication fails"""
    tool_data = {
        "name": "Test Tool",
        "slug": "test-tool",
        "version": "1.0.0",
        "config": {},
        "author_id": str(uuid4())
    }
    
    response = await client.post("/api/v1/mcps", json=tool_data)
    
    assert response.status_code == 403  # No authorization header


@pytest.mark.asyncio
async def test_create_mcp_tool_viewer_forbidden(client: AsyncClient, db_session: AsyncSession):
    """Test MCP tool creation by viewer role is forbidden"""
    # Create viewer user
    user = UserModel(
        id=str(uuid4()),
        username="viewer",
        email="viewer@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.VIEWER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "viewer",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Try to create tool
    tool_data = {
        "name": "Test Tool",
        "slug": "test-tool",
        "version": "1.0.0",
        "config": {},
        "author_id": str(user.id)
    }
    
    response = await client.post(
        "/api/v1/mcps",
        json=tool_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 403
    assert "permission" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_mcp_tool_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful MCP tool retrieval"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="toolreader",
        email="reader@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Existing Tool",
        slug="existing-tool",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.ACTIVE
    )
    db_session.add(tool)
    await db_session.commit()
    tool_id = tool.id
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "toolreader",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Get tool
    response = await client.get(
        f"/api/v1/mcps/{tool_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Existing Tool"
    assert data["slug"] == "existing-tool"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_get_mcp_tool_not_found(client: AsyncClient, db_session: AsyncSession):
    """Test getting non-existent MCP tool returns 404"""
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
    
    # Try to get non-existent tool
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/mcps/{fake_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_mcp_tools_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful MCP tool listing with pagination"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="lister",
        email="lister@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create multiple test tools
    for i in range(5):
        tool = MCPToolModel(
            id=str(uuid4()),
            name=f"Tool {i}",
            slug=f"tool-{i}",
            version="1.0.0",
            author_id=str(user.id),
            status=ToolStatus.ACTIVE
        )
        db_session.add(tool)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "lister",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # List tools
    response = await client.get(
        "/api/v1/mcps?page=1&page_size=10",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert len(data["items"]) == 5
    assert data["total"] == 5


@pytest.mark.asyncio
async def test_update_mcp_tool_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful MCP tool update"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="updater",
        email="updater@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Original Name",
        slug="update-tool",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.DRAFT
    )
    db_session.add(tool)
    await db_session.commit()
    tool_id = tool.id
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "updater",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Update tool
    update_data = {
        "name": "Updated Name",
        "version": "1.1.0",
        "status": "ACTIVE"
    }
    
    response = await client.put(
        f"/api/v1/mcps/{tool_id}",
        json=update_data,
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["version"] == "1.1.0"
    assert data["status"] == "ACTIVE"


@pytest.mark.asyncio
async def test_delete_mcp_tool_success(client: AsyncClient, db_session: AsyncSession):
    """Test successful MCP tool deletion (soft delete)"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="deleter",
        email="deleter@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Create test tool
    tool = MCPToolModel(
        id=str(uuid4()),
        name="To Delete",
        slug="delete-tool",
        version="1.0.0",
        author_id=str(user.id),
        status=ToolStatus.DRAFT
    )
    db_session.add(tool)
    await db_session.commit()
    tool_id = tool.id
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "deleter",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Delete tool
    response = await client.delete(
        f"/api/v1/mcps/{tool_id}",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 204
    
    # Verify tool was soft deleted
    await db_session.refresh(tool)
    assert tool.deleted_at is not None


@pytest.mark.asyncio
async def test_complete_mcp_tool_workflow(client: AsyncClient, db_session: AsyncSession):
    """Test complete MCP tool lifecycle: create, read, update, delete"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),
        username="workflow",
        email="workflow@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "workflow",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    
    # 1. Create tool
    create_response = await client.post(
        "/api/v1/mcps",
        json={
            "name": "Workflow Tool",
            "slug": "workflow-tool",
            "version": "1.0.0",
            "config": {"test": "data"},
            "author_id": str(user.id)
        },
        headers=headers
    )
    assert create_response.status_code == 201
    tool_id = create_response.json()["id"]
    
    # 2. Read tool
    get_response = await client.get(f"/api/v1/mcps/{tool_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["name"] == "Workflow Tool"
    
    # 3. Update tool
    update_response = await client.put(
        f"/api/v1/mcps/{tool_id}",
        json={"name": "Updated Workflow Tool", "version": "2.0.0"},
        headers=headers
    )
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Updated Workflow Tool"
    assert update_response.json()["version"] == "2.0.0"
    
    # 4. List tools (should include our tool)
    list_response = await client.get("/api/v1/mcps", headers=headers)
    assert list_response.status_code == 200
    assert any(t["id"] == tool_id for t in list_response.json()["items"])
    
    # 5. Delete tool
    delete_response = await client.delete(f"/api/v1/mcps/{tool_id}", headers=headers)
    assert delete_response.status_code == 204
    
    # 6. Verify tool is no longer accessible
    get_deleted_response = await client.get(f"/api/v1/mcps/{tool_id}", headers=headers)
    assert get_deleted_response.status_code == 404

