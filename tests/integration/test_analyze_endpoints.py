"""Integration tests for AI analysis endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserModel, UserRole
from app.core.security import hash_password
from uuid import uuid4
from unittest.mock import patch, AsyncMock, MagicMock
from app.schemas.ai_analysis import FeasibilityReport, Improvement


@pytest.fixture
async def authenticated_client(client: AsyncClient, db_session: AsyncSession):
    """Create authenticated client with test user"""
    # Create test user
    user = UserModel(
        id=str(uuid4()),  # Convert UUID to string for SQLite compatibility
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("TestPass123"),
        role=UserRole.DEVELOPER
    )
    db_session.add(user)
    await db_session.commit()
    
    # Login to get access token
    login_response = await client.post("/api/v1/auth/login", json={
        "username": "testuser",
        "password": "TestPass123"
    })
    access_token = login_response.json()["access_token"]
    
    # Add authorization header to client
    client.headers["Authorization"] = f"Bearer {access_token}"
    
    return client


@pytest.mark.asyncio
async def test_analyze_feasibility_sync_success(authenticated_client: AsyncClient):
    """Test feasibility analysis in synchronous mode"""
    # Mock the AI analyzer to avoid actual API calls
    mock_report = FeasibilityReport(
        score=0.85,
        is_feasible=True,
        reasoning="The configuration is well-structured and follows MCP best practices.",
        risks=["Potential performance issues with large datasets"],
        recommendations=["Consider adding caching", "Implement rate limiting"]
    )
    
    with patch('app.api.v1.analyze.AIAnalyzer') as MockAnalyzer:
        mock_instance = AsyncMock()
        mock_instance.analyze_feasibility = AsyncMock(return_value=mock_report)
        MockAnalyzer.return_value = mock_instance
        
        config = {
            "servers": [{"name": "test-server", "command": "python", "args": ["server.py"]}],
            "tools": [{"name": "test-tool", "description": "A test tool"}]
        }
        
        response = await authenticated_client.post(
            "/api/v1/analyze/feasibility",
            params={"async_mode": False},
            json=config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["score"] == 0.85
        assert data["is_feasible"] is True
        assert "reasoning" in data
        assert len(data["risks"]) > 0
        assert len(data["recommendations"]) > 0


@pytest.mark.asyncio
async def test_analyze_feasibility_async_mode(authenticated_client: AsyncClient):
    """Test feasibility analysis in asynchronous mode"""
    config = {
        "servers": [{"name": "test-server", "command": "python", "args": ["server.py"]}],
        "tools": [{"name": "test-tool", "description": "A test tool"}]
    }
    
    with patch('app.api.v1.analyze.analyze_feasibility_task') as mock_task:
        mock_task.apply_async = MagicMock()
        
        response = await authenticated_client.post(
            "/api/v1/analyze/feasibility",
            params={"async_mode": True},
            json=config
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        assert "message" in data
        
        # Verify task was queued
        mock_task.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_feasibility_empty_config(authenticated_client: AsyncClient):
    """Test feasibility analysis with empty configuration fails"""
    response = await authenticated_client.post(
        "/api/v1/analyze/feasibility",
        params={"async_mode": False},
        json={}
    )
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_analyze_feasibility_unauthorized(client: AsyncClient):
    """Test feasibility analysis without authentication fails"""
    config = {
        "servers": [{"name": "test-server"}]
    }
    
    response = await client.post(
        "/api/v1/analyze/feasibility",
        params={"async_mode": False},
        json=config
    )
    
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_improvements_sync_success(authenticated_client: AsyncClient):
    """Test improvement suggestions in synchronous mode"""
    # Mock the AI analyzer
    mock_improvements = [
        Improvement(
            category="security",
            title="Add input validation",
            description="Implement comprehensive input validation to prevent injection attacks",
            priority="high",
            effort="medium",
            impact="high"
        ),
        Improvement(
            category="performance",
            title="Implement caching",
            description="Add Redis caching for frequently accessed data",
            priority="medium",
            effort="low",
            impact="medium"
        ),
        Improvement(
            category="usability",
            title="Improve error messages",
            description="Provide more descriptive error messages for better debugging",
            priority="low",
            effort="low",
            impact="medium"
        )
    ]
    
    with patch('app.api.v1.analyze.AIAnalyzer') as MockAnalyzer:
        mock_instance = AsyncMock()
        mock_instance.suggest_improvements = AsyncMock(return_value=mock_improvements)
        MockAnalyzer.return_value = mock_instance
        
        request_data = {
            "tool_name": "Test Tool",
            "description": "A test MCP tool",
            "config": {
                "servers": [{"name": "test-server"}],
                "tools": [{"name": "test-tool"}]
            }
        }
        
        response = await authenticated_client.post(
            "/api/v1/analyze/improvements",
            params={"async_mode": False},
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "improvements" in data
        assert len(data["improvements"]) == 3
        assert data["improvements"][0]["category"] == "security"
        assert data["improvements"][0]["priority"] == "high"


@pytest.mark.asyncio
async def test_get_improvements_async_mode(authenticated_client: AsyncClient):
    """Test improvement suggestions in asynchronous mode"""
    request_data = {
        "tool_name": "Test Tool",
        "description": "A test MCP tool",
        "config": {"servers": [{"name": "test-server"}]}
    }
    
    with patch('app.api.v1.analyze.suggest_improvements_task') as mock_task:
        mock_task.apply_async = MagicMock()
        
        response = await authenticated_client.post(
            "/api/v1/analyze/improvements",
            params={"async_mode": True},
            json=request_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        
        # Verify task was queued
        mock_task.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_get_improvements_empty_tool_name(authenticated_client: AsyncClient):
    """Test improvement suggestions with empty tool name fails"""
    request_data = {
        "tool_name": "",
        "description": "A test tool",
        "config": {"servers": []}
    }
    
    response = await authenticated_client.post(
        "/api/v1/analyze/improvements",
        params={"async_mode": False},
        json=request_data
    )
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_improvements_empty_config(authenticated_client: AsyncClient):
    """Test improvement suggestions with empty config fails"""
    request_data = {
        "tool_name": "Test Tool",
        "description": "A test tool",
        "config": {}
    }
    
    response = await authenticated_client.post(
        "/api/v1/analyze/improvements",
        params={"async_mode": False},
        json=request_data
    )
    
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_config_sync_success(authenticated_client: AsyncClient):
    """Test configuration generation in synchronous mode"""
    # Mock the AI analyzer
    mock_config = {
        "servers": [
            {
                "name": "generated-server",
                "command": "python",
                "args": ["server.py"],
                "env": {"API_KEY": "${API_KEY}"}
            }
        ],
        "tools": [
            {
                "name": "generated-tool",
                "description": "Auto-generated tool",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"}
                    }
                }
            }
        ]
    }
    
    with patch('app.api.v1.analyze.AIAnalyzer') as MockAnalyzer:
        mock_instance = AsyncMock()
        mock_instance.generate_config = AsyncMock(return_value=mock_config)
        MockAnalyzer.return_value = mock_instance
        
        requirements = {
            "tool_name": "New Tool",
            "description": "A new MCP tool for testing",
            "capabilities": ["search", "retrieve", "analyze"],
            "constraints": {"max_results": 10, "timeout": 30}
        }
        
        response = await authenticated_client.post(
            "/api/v1/analyze/generate-config",
            params={"async_mode": False},
            json=requirements
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "servers" in data["config"]
        assert "tools" in data["config"]
        assert len(data["config"]["servers"]) > 0
        assert len(data["config"]["tools"]) > 0


@pytest.mark.asyncio
async def test_generate_config_async_mode(authenticated_client: AsyncClient):
    """Test configuration generation in asynchronous mode"""
    requirements = {
        "tool_name": "New Tool",
        "description": "A new MCP tool",
        "capabilities": ["search", "retrieve"],
        "constraints": {}
    }
    
    with patch('app.api.v1.analyze.generate_config_task') as mock_task:
        mock_task.apply_async = MagicMock()
        
        response = await authenticated_client.post(
            "/api/v1/analyze/generate-config",
            params={"async_mode": True},
            json=requirements
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
        
        # Verify task was queued
        mock_task.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_generate_config_invalid_requirements(authenticated_client: AsyncClient):
    """Test configuration generation with invalid requirements fails"""
    # Missing required fields
    requirements = {
        "tool_name": "New Tool"
        # Missing description and capabilities
    }
    
    response = await authenticated_client.post(
        "/api/v1/analyze/generate-config",
        params={"async_mode": False},
        json=requirements
    )
    
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_generate_config_empty_capabilities(authenticated_client: AsyncClient):
    """Test configuration generation with empty capabilities fails"""
    requirements = {
        "tool_name": "New Tool",
        "description": "A test tool",
        "capabilities": [],  # Empty list
        "constraints": {}
    }
    
    response = await authenticated_client.post(
        "/api/v1/analyze/generate-config",
        params={"async_mode": False},
        json=requirements
    )
    
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_async_task_status_polling(authenticated_client: AsyncClient):
    """Test async task status polling flow"""
    # Queue a task
    config = {"servers": [{"name": "test"}]}
    
    with patch('app.api.v1.analyze.analyze_feasibility_task') as mock_task:
        mock_task.apply_async = MagicMock()
        
        response = await authenticated_client.post(
            "/api/v1/analyze/feasibility",
            params={"async_mode": True},
            json=config
        )
        
        assert response.status_code == 200
        task_id = response.json()["task_id"]
        
        # Poll task status
        status_response = await authenticated_client.get(
            f"/api/v1/tasks/{task_id}"
        )
        
        # Task should exist (even if pending)
        assert status_response.status_code in [200, 404]  # 404 if not in Redis yet
        
        if status_response.status_code == 200:
            status_data = status_response.json()
            assert "status" in status_data
            assert status_data["status"] in ["pending", "running", "completed", "failed"]


@pytest.mark.asyncio
async def test_complete_analysis_workflow(authenticated_client: AsyncClient):
    """Test complete analysis workflow: feasibility -> improvements -> config generation"""
    # Mock all AI operations
    mock_feasibility = FeasibilityReport(
        score=0.9,
        is_feasible=True,
        reasoning="Excellent configuration",
        risks=[],
        recommendations=["Add monitoring"]
    )
    
    mock_improvements = [
        Improvement(
            category="monitoring",
            title="Add metrics",
            description="Implement Prometheus metrics",
            priority="medium",
            effort="low",
            impact="high"
        )
    ]
    
    mock_config = {
        "servers": [{"name": "improved-server"}],
        "tools": [{"name": "improved-tool"}]
    }
    
    with patch('app.api.v1.analyze.AIAnalyzer') as MockAnalyzer:
        mock_instance = AsyncMock()
        mock_instance.analyze_feasibility = AsyncMock(return_value=mock_feasibility)
        mock_instance.suggest_improvements = AsyncMock(return_value=mock_improvements)
        mock_instance.generate_config = AsyncMock(return_value=mock_config)
        MockAnalyzer.return_value = mock_instance
        
        # Step 1: Analyze feasibility
        config = {"servers": [{"name": "test"}]}
        feasibility_response = await authenticated_client.post(
            "/api/v1/analyze/feasibility",
            params={"async_mode": False},
            json=config
        )
        assert feasibility_response.status_code == 200
        assert feasibility_response.json()["is_feasible"] is True
        
        # Step 2: Get improvements
        improvements_response = await authenticated_client.post(
            "/api/v1/analyze/improvements",
            params={"async_mode": False},
            json={
                "tool_name": "Test Tool",
                "description": "Test",
                "config": config
            }
        )
        assert improvements_response.status_code == 200
        assert len(improvements_response.json()["improvements"]) > 0
        
        # Step 3: Generate improved config
        requirements = {
            "tool_name": "Improved Tool",
            "description": "Tool with improvements applied",
            "capabilities": ["monitoring", "metrics"],
            "constraints": {}
        }
        config_response = await authenticated_client.post(
            "/api/v1/analyze/generate-config",
            params={"async_mode": False},
            json=requirements
        )
        assert config_response.status_code == 200
        assert "config" in config_response.json()

