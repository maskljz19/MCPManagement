"""Property-based tests for AI Analyzer Service"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4
from datetime import datetime, timedelta
from typing import Dict, Any
import json

from app.services.ai_analyzer import AIAnalyzer
from app.schemas.ai_analysis import (
    FeasibilityReport,
    Improvement,
    ConfigRequirements
)


# Hypothesis strategies for generating test data
@st.composite
def mcp_config_strategy(draw):
    """Generate random MCP configurations"""
    num_servers = draw(st.integers(min_value=1, max_value=3))
    num_tools = draw(st.integers(min_value=1, max_value=5))
    
    servers = []
    for _ in range(num_servers):
        server = {
            "name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
            "url": f"http://localhost:{draw(st.integers(min_value=3000, max_value=9999))}",
            "type": draw(st.sampled_from(["http", "websocket", "stdio"]))
        }
        servers.append(server)
    
    tools = []
    for _ in range(num_tools):
        tool = {
            "name": draw(st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))),
            "description": draw(st.text(min_size=10, max_size=200)),
            "parameters": {}
        }
        tools.append(tool)
    
    return {
        "servers": servers,
        "tools": tools,
        "version": "1.0.0"
    }


@st.composite
def config_requirements_strategy(draw):
    """Generate random configuration requirements"""
    num_capabilities = draw(st.integers(min_value=1, max_value=5))
    capabilities = [
        draw(st.text(min_size=5, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))))
        for _ in range(num_capabilities)
    ]
    
    return ConfigRequirements(
        tool_name=draw(st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs')))),
        description=draw(st.text(min_size=10, max_size=500)),
        capabilities=capabilities,
        constraints={}
    )


# Fixtures
@pytest.fixture
async def ai_analyzer(mongo_client):
    """Provide AIAnalyzer instance with test dependencies"""
    # Use a mock API key for testing
    analyzer = AIAnalyzer(
        mongo_client=mongo_client,
        openai_api_key="sk-test-key-for-testing"
    )
    
    # Ensure TTL index exists
    await analyzer.ensure_ttl_index()
    
    yield analyzer
    
    # Cleanup
    await analyzer.results_collection.delete_many({})


# Feature: mcp-platform-backend, Property 9: AI Analysis Response Completeness
@given(config=mcp_config_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
@pytest.mark.property
async def test_analysis_response_completeness(config, ai_analyzer, monkeypatch):
    """
    Property 9: AI Analysis Response Completeness
    
    For any MCP configuration submitted for feasibility analysis,
    the response should contain a score (0.0-1.0) and non-empty reasoning text.
    
    Validates: Requirements 3.1
    """
    # Mock the LLM response to avoid actual API calls
    async def mock_ainvoke(prompt):
        class MockResponse:
            content = json.dumps({
                "score": 0.75,
                "is_feasible": True,
                "reasoning": "This configuration appears feasible based on the provided structure.",
                "risks": ["Potential performance issues with multiple servers"],
                "recommendations": ["Consider load balancing", "Add monitoring"]
            })
        return MockResponse()
    
    monkeypatch.setattr(ai_analyzer.llm, "ainvoke", mock_ainvoke)
    
    # Act: Analyze feasibility
    report = await ai_analyzer.analyze_feasibility(config)
    
    # Assert: Response completeness
    assert isinstance(report, FeasibilityReport)
    assert 0.0 <= report.score <= 1.0, f"Score {report.score} not in range [0.0, 1.0]"
    assert report.reasoning is not None
    assert len(report.reasoning.strip()) > 0, "Reasoning cannot be empty"
    assert isinstance(report.is_feasible, bool)
    assert isinstance(report.risks, list)
    assert isinstance(report.recommendations, list)


# Feature: mcp-platform-backend, Property 10: Improvement Suggestions Non-Empty
@given(
    tool_name=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))),
    description=st.text(min_size=10, max_size=500),
    config=mcp_config_strategy()
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
@pytest.mark.property
async def test_improvement_suggestions_non_empty(tool_name, description, config, ai_analyzer, monkeypatch):
    """
    Property 10: Improvement Suggestions Non-Empty
    
    For any tool submitted for improvement analysis,
    the response should contain at least one recommendation.
    
    Validates: Requirements 3.2
    """
    # Mock the LLM response to avoid actual API calls
    async def mock_ainvoke(prompt):
        class MockResponse:
            content = json.dumps([
                {
                    "category": "performance",
                    "title": "Optimize server connections",
                    "description": "Consider implementing connection pooling for better performance",
                    "priority": "medium",
                    "effort": "medium",
                    "impact": "high"
                },
                {
                    "category": "security",
                    "title": "Add authentication",
                    "description": "Implement proper authentication mechanisms",
                    "priority": "high",
                    "effort": "high",
                    "impact": "high"
                }
            ])
        return MockResponse()
    
    monkeypatch.setattr(ai_analyzer.llm, "ainvoke", mock_ainvoke)
    
    # Act: Get improvement suggestions
    improvements = await ai_analyzer.suggest_improvements(
        tool_name=tool_name,
        description=description,
        config=config
    )
    
    # Assert: At least one improvement
    assert isinstance(improvements, list)
    assert len(improvements) >= 1, "Should return at least one improvement suggestion"
    
    # Verify each improvement has required fields
    for improvement in improvements:
        assert isinstance(improvement, Improvement)
        assert improvement.category is not None
        assert len(improvement.title) > 0
        assert len(improvement.description) > 0
        assert improvement.priority in ["low", "medium", "high", "critical"]
        assert improvement.effort in ["low", "medium", "high"]
        assert improvement.impact in ["low", "medium", "high"]


# Feature: mcp-platform-backend, Property 11: Generated Configuration Validity
@given(requirements=config_requirements_strategy())
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
@pytest.mark.property
async def test_generated_config_validity(requirements, ai_analyzer, monkeypatch):
    """
    Property 11: Generated Configuration Validity
    
    For any configuration requirements, the auto-generated MCP configuration
    should pass Pydantic schema validation (be a valid dict with expected structure).
    
    Validates: Requirements 3.3
    """
    # Mock the LLM response to avoid actual API calls
    async def mock_ainvoke(prompt):
        class MockResponse:
            content = json.dumps({
                "servers": [
                    {
                        "name": "main-server",
                        "url": "http://localhost:8000",
                        "type": "http"
                    }
                ],
                "tools": [
                    {
                        "name": "example-tool",
                        "description": "An example tool",
                        "parameters": {}
                    }
                ],
                "version": "1.0.0"
            })
        return MockResponse()
    
    monkeypatch.setattr(ai_analyzer.llm, "ainvoke", mock_ainvoke)
    
    # Act: Generate configuration
    config = await ai_analyzer.generate_config(requirements)
    
    # Assert: Valid configuration structure
    assert isinstance(config, dict), "Generated config should be a dictionary"
    assert "servers" in config or "tools" in config, "Config should have servers or tools"
    
    # Validate basic structure
    if "servers" in config:
        assert isinstance(config["servers"], list)
        for server in config["servers"]:
            assert isinstance(server, dict)
            assert "name" in server or "url" in server or "type" in server
    
    if "tools" in config:
        assert isinstance(config["tools"], list)
        for tool in config["tools"]:
            assert isinstance(tool, dict)


# Feature: mcp-platform-backend, Property 12: Analysis Result Persistence
@given(
    task_type=st.sampled_from(["feasibility", "improvements", "generate_config"]),
    ttl_hours=st.integers(min_value=1, max_value=72)
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
@pytest.mark.asyncio
@pytest.mark.property
async def test_analysis_result_persistence(task_type, ttl_hours, ai_analyzer):
    """
    Property 12: Analysis Result Persistence
    
    For any completed AI analysis task, MongoDB should contain
    a result document with matching task_id.
    
    Validates: Requirements 3.5
    """
    # Arrange: Create a task ID and result
    task_id = uuid4()
    
    # Create appropriate result based on task type
    if task_type == "feasibility":
        result = FeasibilityReport(
            score=0.8,
            is_feasible=True,
            reasoning="Test reasoning",
            risks=["Test risk"],
            recommendations=["Test recommendation"]
        )
    elif task_type == "improvements":
        result = [
            Improvement(
                category="performance",
                title="Test improvement",
                description="Test description",
                priority="medium",
                effort="low",
                impact="high"
            )
        ]
    else:  # generate_config
        result = {"servers": [], "tools": [], "version": "1.0.0"}
    
    # Act: Store result
    await ai_analyzer.store_analysis_result(
        task_id=task_id,
        task_type=task_type,
        result=result,
        ttl_hours=ttl_hours
    )
    
    # Assert: Result is retrievable
    stored_result = await ai_analyzer.get_analysis_result(task_id)
    
    assert stored_result is not None, "Result should be stored in MongoDB"
    assert stored_result["task_id"] == str(task_id)
    assert stored_result["task_type"] == task_type
    assert stored_result["status"] == "completed"
    assert "result" in stored_result
    assert "created_at" in stored_result
    assert "completed_at" in stored_result
    assert "ttl_expires_at" in stored_result
    
    # Verify TTL is set correctly (within reasonable margin)
    ttl_expires_at = stored_result["ttl_expires_at"]
    expected_expiry = datetime.utcnow() + timedelta(hours=ttl_hours)
    time_diff = abs((ttl_expires_at - expected_expiry).total_seconds())
    assert time_diff < 60, f"TTL expiry time should be within 60 seconds of expected ({time_diff}s difference)"
