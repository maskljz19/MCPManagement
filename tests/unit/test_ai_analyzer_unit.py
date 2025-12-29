"""Unit tests for AI Analyzer Service (without external dependencies)"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
import json

from app.services.ai_analyzer import AIAnalyzer
from app.schemas.ai_analysis import (
    FeasibilityReport,
    Improvement,
    ConfigRequirements
)


@pytest.fixture
def mock_mongo_client():
    """Create a mock MongoDB client"""
    mock_client = MagicMock()
    mock_db = MagicMock()
    mock_collection = MagicMock()
    
    # Setup the chain: client[db_name] -> db -> collection
    mock_client.__getitem__ = MagicMock(return_value=mock_db)
    mock_db.__getitem__ = MagicMock(return_value=mock_collection)
    
    # Make collection methods async
    mock_collection.insert_one = AsyncMock()
    mock_collection.find_one = AsyncMock()
    mock_collection.create_index = AsyncMock()
    
    return mock_client


@pytest.fixture
def ai_analyzer(mock_mongo_client):
    """Create AIAnalyzer with mocked dependencies"""
    with patch('app.services.ai_analyzer.ChatOpenAI'):
        analyzer = AIAnalyzer(
            mongo_client=mock_mongo_client,
            openai_api_key="test-key"
        )
        return analyzer


@pytest.mark.asyncio
async def test_analyze_feasibility_returns_valid_report(ai_analyzer):
    """Test that feasibility analysis returns a valid FeasibilityReport"""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "score": 0.85,
        "is_feasible": True,
        "reasoning": "The configuration is well-structured and feasible.",
        "risks": ["Potential scalability issues"],
        "recommendations": ["Add load balancing", "Implement caching"]
    })
    
    ai_analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Test
    config = {"servers": [], "tools": []}
    report = await ai_analyzer.analyze_feasibility(config)
    
    # Assertions
    assert isinstance(report, FeasibilityReport)
    assert 0.0 <= report.score <= 1.0
    assert isinstance(report.is_feasible, bool)
    assert len(report.reasoning) > 0
    assert isinstance(report.risks, list)
    assert isinstance(report.recommendations, list)


@pytest.mark.asyncio
async def test_suggest_improvements_returns_list(ai_analyzer):
    """Test that improvement suggestions returns a list of Improvement objects"""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = json.dumps([
        {
            "category": "performance",
            "title": "Optimize database queries",
            "description": "Add indexes to frequently queried fields",
            "priority": "high",
            "effort": "medium",
            "impact": "high"
        },
        {
            "category": "security",
            "title": "Add rate limiting",
            "description": "Implement rate limiting to prevent abuse",
            "priority": "critical",
            "effort": "low",
            "impact": "high"
        }
    ])
    
    ai_analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Test
    improvements = await ai_analyzer.suggest_improvements(
        tool_name="Test Tool",
        description="A test tool",
        config={"servers": []}
    )
    
    # Assertions
    assert isinstance(improvements, list)
    assert len(improvements) >= 1
    for improvement in improvements:
        assert isinstance(improvement, Improvement)
        assert improvement.category in ["performance", "security", "usability", "reliability", "maintainability"]
        assert len(improvement.title) > 0
        assert len(improvement.description) > 0
        assert improvement.priority in ["low", "medium", "high", "critical"]
        assert improvement.effort in ["low", "medium", "high"]
        assert improvement.impact in ["low", "medium", "high"]


@pytest.mark.asyncio
async def test_suggest_improvements_handles_markdown_json(ai_analyzer):
    """Test that improvement suggestions can parse JSON from markdown code blocks"""
    # Mock LLM response with markdown code block
    mock_response = MagicMock()
    mock_response.content = """Here are the improvements:

```json
[
    {
        "category": "performance",
        "title": "Optimize queries",
        "description": "Add database indexes",
        "priority": "high",
        "effort": "medium",
        "impact": "high"
    }
]
```

These improvements will help."""
    
    ai_analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Test
    improvements = await ai_analyzer.suggest_improvements(
        tool_name="Test Tool",
        description="A test tool",
        config={"servers": []}
    )
    
    # Assertions
    assert isinstance(improvements, list)
    assert len(improvements) >= 1


@pytest.mark.asyncio
async def test_generate_config_returns_dict(ai_analyzer):
    """Test that config generation returns a valid dictionary"""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.content = json.dumps({
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
    
    ai_analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Test
    requirements = ConfigRequirements(
        tool_name="New Tool",
        description="A new MCP tool",
        capabilities=["data processing"],
        constraints={}
    )
    config = await ai_analyzer.generate_config(requirements)
    
    # Assertions
    assert isinstance(config, dict)
    assert "servers" in config or "tools" in config


@pytest.mark.asyncio
async def test_generate_config_handles_markdown_json(ai_analyzer):
    """Test that config generation can parse JSON from markdown code blocks"""
    # Mock LLM response with markdown code block
    mock_response = MagicMock()
    mock_response.content = """Here's the configuration:

```json
{
    "servers": [],
    "tools": [{"name": "test"}],
    "version": "1.0.0"
}
```

This configuration should work."""
    
    ai_analyzer.llm.ainvoke = AsyncMock(return_value=mock_response)
    
    # Test
    requirements = ConfigRequirements(
        tool_name="New Tool",
        description="A new MCP tool",
        capabilities=["testing"],
        constraints={}
    )
    config = await ai_analyzer.generate_config(requirements)
    
    # Assertions
    assert isinstance(config, dict)


@pytest.mark.asyncio
async def test_store_analysis_result_with_pydantic_model(ai_analyzer):
    """Test storing analysis result with Pydantic model"""
    task_id = uuid4()
    result = FeasibilityReport(
        score=0.9,
        is_feasible=True,
        reasoning="Test reasoning",
        risks=["Test risk"],
        recommendations=["Test recommendation"]
    )
    
    # Test
    await ai_analyzer.store_analysis_result(
        task_id=task_id,
        task_type="feasibility",
        result=result,
        ttl_hours=24
    )
    
    # Verify insert_one was called
    ai_analyzer.results_collection.insert_one.assert_called_once()
    
    # Verify the document structure
    call_args = ai_analyzer.results_collection.insert_one.call_args[0][0]
    assert call_args["task_id"] == str(task_id)
    assert call_args["task_type"] == "feasibility"
    assert call_args["status"] == "completed"
    assert "result" in call_args
    assert "ttl_expires_at" in call_args


@pytest.mark.asyncio
async def test_store_analysis_result_with_list(ai_analyzer):
    """Test storing analysis result with list of Pydantic models"""
    task_id = uuid4()
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
    
    # Test
    await ai_analyzer.store_analysis_result(
        task_id=task_id,
        task_type="improvements",
        result=result,
        ttl_hours=48
    )
    
    # Verify insert_one was called
    ai_analyzer.results_collection.insert_one.assert_called_once()
    
    # Verify the document structure
    call_args = ai_analyzer.results_collection.insert_one.call_args[0][0]
    assert call_args["task_id"] == str(task_id)
    assert call_args["task_type"] == "improvements"
    assert isinstance(call_args["result"], list)


@pytest.mark.asyncio
async def test_get_analysis_result(ai_analyzer):
    """Test retrieving analysis result"""
    task_id = uuid4()
    
    # Mock MongoDB response
    mock_result = {
        "_id": "some-mongo-id",
        "task_id": str(task_id),
        "task_type": "feasibility",
        "status": "completed",
        "result": {"score": 0.8}
    }
    ai_analyzer.results_collection.find_one = AsyncMock(return_value=mock_result)
    
    # Test
    result = await ai_analyzer.get_analysis_result(task_id)
    
    # Assertions
    assert result is not None
    assert result["task_id"] == str(task_id)
    assert "_id" not in result  # Should be removed


@pytest.mark.asyncio
async def test_get_analysis_result_not_found(ai_analyzer):
    """Test retrieving non-existent analysis result"""
    task_id = uuid4()
    
    # Mock MongoDB response (not found)
    ai_analyzer.results_collection.find_one = AsyncMock(return_value=None)
    
    # Test
    result = await ai_analyzer.get_analysis_result(task_id)
    
    # Assertions
    assert result is None


@pytest.mark.asyncio
async def test_ensure_ttl_index(ai_analyzer):
    """Test TTL index creation"""
    # Test
    await ai_analyzer.ensure_ttl_index()
    
    # Verify create_index was called
    ai_analyzer.results_collection.create_index.assert_called_once_with(
        "ttl_expires_at",
        expireAfterSeconds=0
    )


def test_ai_analyzer_requires_api_key(mock_mongo_client):
    """Test that AIAnalyzer raises error without API key"""
    with patch('app.services.ai_analyzer.ChatOpenAI'):
        with patch('app.services.ai_analyzer.settings') as mock_settings:
            mock_settings.OPENAI_API_KEY = None
            
            with pytest.raises(ValueError, match="OpenAI API key is required"):
                AIAnalyzer(
                    mongo_client=mock_mongo_client,
                    openai_api_key=None
                )
