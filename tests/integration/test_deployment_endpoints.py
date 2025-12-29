"""Integration tests for Deployment API endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.models.user import UserModel, UserRole
from app.models.mcp_tool import ToolStatus, MCPToolModel
from app.schemas.mcp_tool import MCPToolCreate
from app.schemas.deployment import DeploymentCreate, DeploymentConfig


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for authentication"""
    user_id = uuid4()
    user = UserModel(
        id=str(user_id),
        username="deployuser",
        email="deploy@example.com",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYzS7sFCe4W",
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def auth_headers(client: AsyncClient, test_user: UserModel):
    """Get authentication headers for test user"""
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "deployuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
async def test_tool(db_session: AsyncSession, test_user: UserModel):
    """Create a test MCP tool"""
    tool = MCPToolModel(
        id=str(uuid4()),
        name="Test Tool",
        slug="test-tool-deploy",
        description="Test tool for deployment",
        version="1.0.0",
        author_id=str(test_user.id),
        status=ToolStatus.ACTIVE
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.mark.asyncio
async def test_deploy_mcp_tool(
    client: AsyncClient,
    auth_headers: dict,
    test_tool: MCPToolModel
):
    """Test deploying an MCP tool"""
    # Deploy the tool
    deployment_data = {
        "tool_id": str(test_tool.id),
        "config": {
            "environment": {"TEST_VAR": "test_value"},
            "port": None
        }
    }
    
    response = await client.post(
        "/api/v1/deployments",
        json=deployment_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["tool_id"] == str(test_tool.id)
    assert data["status"] in ["starting", "running"]
    assert "endpoint_url" in data


@pytest.mark.asyncio
async def test_get_deployment(
    client: AsyncClient,
    auth_headers: dict,
    test_tool: MCPToolModel,
    mcp_server_manager_fixture
):
    """Test getting deployment details"""
    # Deploy a tool
    config = DeploymentConfig()
    deployment = await mcp_server_manager_fixture.deploy_server(test_tool.id, config)
    
    # Get deployment details
    response = await client.get(
        f"/api/v1/deployments/{deployment.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(deployment.id)
    assert data["tool_id"] == str(test_tool.id)


@pytest.mark.asyncio
async def test_get_deployment_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Test getting non-existent deployment returns 404"""
    fake_id = uuid4()
    response = await client.get(
        f"/api/v1/deployments/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stop_deployment(
    client: AsyncClient,
    auth_headers: dict,
    test_tool: MCPToolModel,
    mcp_server_manager_fixture
):
    """Test stopping a deployment"""
    # Deploy a tool
    config = DeploymentConfig()
    deployment = await mcp_server_manager_fixture.deploy_server(test_tool.id, config)
    
    # Stop the deployment
    response = await client.delete(
        f"/api/v1/deployments/{deployment.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_stop_deployment_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Test stopping non-existent deployment returns 404"""
    fake_id = uuid4()
    response = await client.delete(
        f"/api/v1/deployments/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_deployments(
    client: AsyncClient,
    auth_headers: dict,
    db_session: AsyncSession,
    test_user: UserModel,
    mcp_server_manager_fixture
):
    """Test listing deployments"""
    # Create and deploy multiple tools
    for i in range(3):
        tool = MCPToolModel(
            id=str(uuid4()),
            name=f"Test Tool {i}",
            slug=f"test-tool-list-{i}",
            description="Test tool",
            version="1.0.0",
            author_id=str(test_user.id),
            status=ToolStatus.ACTIVE
        )
        db_session.add(tool)
        await db_session.commit()
        await db_session.refresh(tool)
        
        config = DeploymentConfig()
        await mcp_server_manager_fixture.deploy_server(tool.id, config)
    
    # List all deployments
    response = await client.get(
        "/api/v1/deployments",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


@pytest.mark.asyncio
async def test_list_deployments_with_filter(
    client: AsyncClient,
    auth_headers: dict,
    test_tool: MCPToolModel,
    mcp_server_manager_fixture
):
    """Test listing deployments with tool_id filter"""
    # Deploy a tool
    config = DeploymentConfig()
    deployment = await mcp_server_manager_fixture.deploy_server(test_tool.id, config)
    
    # List deployments filtered by tool_id
    response = await client.get(
        f"/api/v1/deployments?tool_id={test_tool.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert all(d["tool_id"] == str(test_tool.id) for d in data)


@pytest.mark.asyncio
async def test_check_deployment_health(
    client: AsyncClient,
    auth_headers: dict,
    test_tool: MCPToolModel,
    mcp_server_manager_fixture
):
    """Test checking deployment health"""
    # Deploy a tool
    config = DeploymentConfig()
    deployment = await mcp_server_manager_fixture.deploy_server(test_tool.id, config)
    
    # Check health
    response = await client.get(
        f"/api/v1/deployments/{deployment.id}/health",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "deployment_id" in data
    assert "status" in data
    assert "checked_at" in data
    assert data["deployment_id"] == str(deployment.id)

