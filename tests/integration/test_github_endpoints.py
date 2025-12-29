"""Integration tests for GitHub integration endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from unittest.mock import patch, MagicMock
from uuid import uuid4

from app.models.user import UserModel, UserRole
from app.models.github_connection import GitHubConnectionModel
from app.models.mcp_tool import MCPToolModel, ToolStatus
from app.core.security import hash_password


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for authentication"""
    # Use a pre-hashed password to avoid bcrypt issues in tests
    # This is the hash for "TestPass123"
    # Convert UUID to string for SQLite compatibility
    user_id = uuid4()
    user = UserModel(
        id=str(user_id),  # Convert to string for SQLite
        username="githubuser",
        email="github@example.com",
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
        "username": "githubuser",
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
        slug="test-tool",
        description="Test tool for GitHub integration",
        version="1.0.0",
        author_id=str(test_user.id),
        status=ToolStatus.ACTIVE
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return tool


@pytest.mark.asyncio
async def test_connect_repository_success(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel
):
    """Test successful repository connection"""
    # Mock GitHub API
    with patch('app.services.github_integration.Github') as mock_github:
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.default_branch = "main"
        
        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        connection_data = {
            "repository_url": "https://github.com/testowner/test-repo",
            "access_token": "ghp_test_token_123",
            "tool_id": None
        }
        
        response = await client.post(
            "/api/v1/github/connect",
            json=connection_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["repository_url"] == "https://github.com/testowner/test-repo"
        assert data["user_id"] == str(test_user.id)
        assert "id" in data
        assert "created_at" in data
        
        # Verify connection was created in database
        stmt = select(GitHubConnectionModel).where(
            GitHubConnectionModel.repository_url == "https://github.com/testowner/test-repo"
        )
        result = await db_session.execute(stmt)
        connection = result.scalar_one_or_none()
        assert connection is not None
        assert connection.user_id == str(test_user.id)


@pytest.mark.asyncio
async def test_connect_repository_with_tool(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel,
    test_tool: MCPToolModel
):
    """Test repository connection with associated tool"""
    with patch('app.services.github_integration.Github') as mock_github:
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.default_branch = "main"
        
        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        connection_data = {
            "repository_url": "https://github.com/testowner/tool-repo",
            "access_token": "ghp_test_token_123",
            "tool_id": test_tool.id
        }
        
        response = await client.post(
            "/api/v1/github/connect",
            json=connection_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["tool_id"] == test_tool.id


@pytest.mark.asyncio
async def test_connect_repository_invalid_url(
    client: AsyncClient,
    auth_headers: dict
):
    """Test connection with invalid repository URL"""
    connection_data = {
        "repository_url": "not-a-valid-url",
        "access_token": "ghp_test_token_123"
    }
    
    response = await client.post(
        "/api/v1/github/connect",
        json=connection_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_repository_invalid_token(
    client: AsyncClient,
    auth_headers: dict
):
    """Test connection with invalid GitHub token"""
    with patch('app.services.github_integration.Github') as mock_github:
        from github import GithubException
        
        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.side_effect = GithubException(
            status=401,
            data={"message": "Bad credentials"}
        )
        mock_github.return_value = mock_github_instance
        
        connection_data = {
            "repository_url": "https://github.com/testowner/test-repo",
            "access_token": "invalid_token"
        }
        
        response = await client.post(
            "/api/v1/github/connect",
            json=connection_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_repository_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Test connection with non-existent repository"""
    with patch('app.services.github_integration.Github') as mock_github:
        from github import GithubException
        
        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.side_effect = GithubException(
            status=404,
            data={"message": "Not Found"}
        )
        mock_github.return_value = mock_github_instance
        
        connection_data = {
            "repository_url": "https://github.com/testowner/nonexistent",
            "access_token": "ghp_test_token_123"
        }
        
        response = await client.post(
            "/api/v1/github/connect",
            json=connection_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_connect_repository_unauthorized(client: AsyncClient):
    """Test connection without authentication fails"""
    connection_data = {
        "repository_url": "https://github.com/testowner/test-repo",
        "access_token": "ghp_test_token_123"
    }
    
    response = await client.post(
        "/api/v1/github/connect",
        json=connection_data
    )
    
    assert response.status_code == 401  # No authorization header


@pytest.mark.asyncio
async def test_trigger_sync_success(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel
):
    """Test successful sync triggering"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha=None,
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    await db_session.refresh(connection)
    
    # Mock Celery task
    with patch('app.services.github_integration.sync_repository_task') as mock_task:
        mock_task.delay.return_value = MagicMock(id="task-123")
        
        response = await client.post(
            f"/api/v1/github/sync/{connection.id}",
            headers={
                **auth_headers,
                "X-GitHub-Token": "ghp_test_token_123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "task-123"
        assert data["status"] == "queued"
        assert data["connection_id"] == connection.id
        
        # Verify task was queued
        mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_trigger_sync_connection_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Test sync with non-existent connection"""
    fake_connection_id = uuid4()
    
    response = await client.post(
        f"/api/v1/github/sync/{fake_connection_id}",
        headers={
            **auth_headers,
            "X-GitHub-Token": "ghp_test_token_123"
        }
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_trigger_sync_missing_token(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel
):
    """Test sync without GitHub token header"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha=None,
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    
    response = await client.post(
        f"/api/v1/github/sync/{connection.id}",
        headers=auth_headers  # Missing X-GitHub-Token header
    )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_disconnect_repository_success(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel,
    test_tool: MCPToolModel
):
    """Test successful repository disconnection"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        tool_id=test_tool.id,
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha="abc123",
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    connection_id = connection.id
    
    response = await client.delete(
        f"/api/v1/github/disconnect/{connection_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 204
    
    # Verify connection was deleted
    stmt = select(GitHubConnectionModel).where(
        GitHubConnectionModel.id == connection_id
    )
    result = await db_session.execute(stmt)
    deleted_connection = result.scalar_one_or_none()
    assert deleted_connection is None
    
    # Verify tool still exists (data preserved)
    stmt = select(MCPToolModel).where(MCPToolModel.id == test_tool.id)
    result = await db_session.execute(stmt)
    tool = result.scalar_one_or_none()
    assert tool is not None


@pytest.mark.asyncio
async def test_disconnect_repository_not_found(
    client: AsyncClient,
    auth_headers: dict
):
    """Test disconnection with non-existent connection"""
    fake_connection_id = uuid4()
    
    response = await client.delete(
        f"/api/v1/github/disconnect/{fake_connection_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_disconnect_repository_unauthorized(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel
):
    """Test disconnection without authentication fails"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha=None,
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    
    response = await client.delete(
        f"/api/v1/github/disconnect/{connection.id}"
    )
    
    assert response.status_code == 401  # No authorization header


@pytest.mark.asyncio
async def test_process_webhook_success(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel
):
    """Test successful webhook processing"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha=None,
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    
    webhook_data = {
        "event_type": "push",
        "payload": {
            "repository": {
                "html_url": "https://github.com/testowner/test-repo"
            },
            "ref": "refs/heads/main",
            "commits": [
                {"id": "abc123", "message": "Test commit"}
            ]
        }
    }
    
    response = await client.post(
        "/api/v1/github/webhook",
        json=webhook_data,
        headers={"X-GitHub-Event": "push"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"
    assert "webhook_id" in data
    assert data["connection_id"] == connection.id


@pytest.mark.asyncio
async def test_process_webhook_no_connection(client: AsyncClient):
    """Test webhook processing with no matching connection"""
    webhook_data = {
        "event_type": "push",
        "payload": {
            "repository": {
                "html_url": "https://github.com/unknown/repo"
            },
            "ref": "refs/heads/main"
        }
    }
    
    response = await client.post(
        "/api/v1/github/webhook",
        json=webhook_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ignored"
    assert "no connection" in data["reason"].lower()


@pytest.mark.asyncio
async def test_process_webhook_invalid_payload(client: AsyncClient):
    """Test webhook processing with invalid payload"""
    webhook_data = {
        "event_type": "push",
        "payload": {
            # Missing repository field
            "ref": "refs/heads/main"
        }
    }
    
    response = await client.post(
        "/api/v1/github/webhook",
        json=webhook_data
    )
    
    assert response.status_code == 400
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_process_webhook_with_header_event_type(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: UserModel
):
    """Test webhook processing using event type from header"""
    # Create a GitHub connection
    connection = GitHubConnectionModel(
        id=str(uuid4()),
        user_id=str(test_user.id),
        repository_url="https://github.com/testowner/test-repo",
        last_sync_sha=None,
        last_sync_at=None
    )
    db_session.add(connection)
    await db_session.commit()
    
    webhook_data = {
        "event_type": "push",  # This should be overridden by header
        "payload": {
            "repository": {
                "html_url": "https://github.com/testowner/test-repo"
            },
            "action": "opened"
        }
    }
    
    response = await client.post(
        "/api/v1/github/webhook",
        json=webhook_data,
        headers={"X-GitHub-Event": "pull_request"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_github_integration_flow(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    test_user: UserModel,
    test_tool: MCPToolModel
):
    """Test complete GitHub integration flow: connect -> sync -> disconnect"""
    # Step 1: Connect repository
    with patch('app.services.github_integration.Github') as mock_github:
        mock_repo = MagicMock()
        mock_repo.name = "test-repo"
        mock_repo.default_branch = "main"
        
        mock_github_instance = MagicMock()
        mock_github_instance.get_repo.return_value = mock_repo
        mock_github.return_value = mock_github_instance
        
        connect_response = await client.post(
            "/api/v1/github/connect",
            json={
                "repository_url": "https://github.com/testowner/flow-repo",
                "access_token": "ghp_test_token_123",
                "tool_id": test_tool.id
            },
            headers=auth_headers
        )
        
        assert connect_response.status_code == 201
        connection_id = connect_response.json()["id"]
    
    # Step 2: Trigger sync
    with patch('app.services.github_integration.sync_repository_task') as mock_task:
        mock_task.delay.return_value = MagicMock(id="sync-task-456")
        
        sync_response = await client.post(
            f"/api/v1/github/sync/{connection_id}",
            headers={
                **auth_headers,
                "X-GitHub-Token": "ghp_test_token_123"
            }
        )
        
        assert sync_response.status_code == 200
        assert sync_response.json()["task_id"] == "sync-task-456"
    
    # Step 3: Disconnect repository
    disconnect_response = await client.delete(
        f"/api/v1/github/disconnect/{connection_id}",
        headers=auth_headers
    )
    
    assert disconnect_response.status_code == 204
    
    # Verify connection is gone but tool remains
    stmt = select(GitHubConnectionModel).where(
        GitHubConnectionModel.id == connection_id
    )
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None
    
    stmt = select(MCPToolModel).where(MCPToolModel.id == test_tool.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is not None

