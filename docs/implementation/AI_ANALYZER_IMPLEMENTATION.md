# AI Analyzer Implementation

## Overview

The AI Analyzer component has been successfully implemented with LangChain and OpenAI integration. This document provides details about the implementation and how to test it.

## Implementation Details

### Files Created

1. **`app/services/ai_analyzer.py`** - Main AI Analyzer service
   - LangChain ChatOpenAI integration
   - Feasibility analysis with structured output parsing
   - Improvement suggestions generation
   - Auto-configuration generation
   - Result persistence in MongoDB with TTL

2. **`tests/property/test_ai_analysis_properties.py`** - Property-based tests
   - Property 9: AI Analysis Response Completeness
   - Property 10: Improvement Suggestions Non-Empty
   - Property 11: Generated Configuration Validity
   - Property 12: Analysis Result Persistence

### Key Features

#### 1. LangChain Integration
- Uses `ChatOpenAI` with GPT-4 model
- Temperature set to 0.2 for consistent, focused responses
- Structured output parsing with Pydantic models
- Prompt templates for different analysis tasks

#### 2. Feasibility Analysis
- Analyzes MCP configurations for feasibility
- Returns structured report with:
  - Feasibility score (0.0 to 1.0)
  - Boolean feasibility flag
  - Detailed reasoning
  - Identified risks
  - Recommendations

#### 3. Improvement Suggestions
- Generates actionable improvement suggestions
- Each suggestion includes:
  - Category (performance, security, usability, etc.)
  - Title and description
  - Priority level (low, medium, high, critical)
  - Effort estimate (low, medium, high)
  - Impact assessment (low, medium, high)

#### 4. Configuration Generation
- Generates valid MCP configurations from requirements
- Validates against MCP specification structure
- Includes servers, tools, and optional prompts

#### 5. Result Persistence
- Stores analysis results in MongoDB
- Automatic TTL (time-to-live) for cleanup
- Supports retrieval by task_id
- TTL index for automatic expiration

## Testing

### Prerequisites

The property tests require MongoDB to be running. You have two options:

#### Option 1: Docker (Recommended)

Start MongoDB using Docker:

```bash
# Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:latest

# Verify it's running
docker ps | grep mongodb
```

#### Option 2: Local Installation

Install MongoDB locally and ensure it's running on `localhost:27017`.

### Running Tests

Once MongoDB is running:

```bash
# Run all AI Analyzer property tests
pytest tests/property/test_ai_analysis_properties.py -v

# Run specific test
pytest tests/property/test_ai_analysis_properties.py::test_analysis_response_completeness -v

# Run with Hypothesis statistics
pytest tests/property/test_ai_analysis_properties.py -v --hypothesis-show-statistics
```

### Test Configuration

Each property test:
- Runs 100 iterations with randomly generated inputs
- Uses mocked LLM responses to avoid API costs
- Tests universal properties across all valid inputs
- Validates against requirements from design document

### Property Tests

#### Property 9: AI Analysis Response Completeness
**Validates: Requirements 3.1**

For any MCP configuration submitted for feasibility analysis, the response should contain:
- A score between 0.0 and 1.0
- Non-empty reasoning text
- Boolean feasibility flag
- Lists of risks and recommendations

#### Property 10: Improvement Suggestions Non-Empty
**Validates: Requirements 3.2**

For any tool submitted for improvement analysis, the response should contain:
- At least one improvement suggestion
- Each suggestion has all required fields
- Valid priority, effort, and impact values

#### Property 11: Generated Configuration Validity
**Validates: Requirements 3.3**

For any configuration requirements, the auto-generated MCP configuration should:
- Be a valid dictionary
- Contain servers or tools
- Have proper structure for each component

#### Property 12: Analysis Result Persistence
**Validates: Requirements 3.5**

For any completed AI analysis task:
- MongoDB should contain a result document
- Document should have matching task_id
- TTL should be set correctly
- All required fields should be present

## Usage Example

```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.ai_analyzer import AIAnalyzer
from app.schemas.ai_analysis import ConfigRequirements

# Initialize
mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
analyzer = AIAnalyzer(
    mongo_client=mongo_client,
    openai_api_key="your-api-key"
)

# Ensure TTL index exists (call once at startup)
await analyzer.ensure_ttl_index()

# Analyze feasibility
config = {
    "servers": [{"name": "main", "url": "http://localhost:8000"}],
    "tools": [{"name": "example", "description": "Example tool"}]
}
report = await analyzer.analyze_feasibility(config)
print(f"Feasibility: {report.is_feasible}, Score: {report.score}")

# Get improvement suggestions
improvements = await analyzer.suggest_improvements(
    tool_name="My Tool",
    description="A tool for testing",
    config=config
)
for improvement in improvements:
    print(f"{improvement.title}: {improvement.description}")

# Generate configuration
requirements = ConfigRequirements(
    tool_name="New Tool",
    description="A new MCP tool",
    capabilities=["data processing", "API integration"],
    constraints={}
)
generated_config = await analyzer.generate_config(requirements)

# Store result
from uuid import uuid4
task_id = uuid4()
await analyzer.store_analysis_result(
    task_id=task_id,
    task_type="feasibility",
    result=report,
    ttl_hours=24
)

# Retrieve result later
stored_result = await analyzer.get_analysis_result(task_id)
```

## Configuration

The AI Analyzer requires the following environment variables:

```bash
# Required
OPENAI_API_KEY=sk-your-api-key-here

# MongoDB connection
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=mcp_platform
```

## Error Handling

The service includes robust error handling:

1. **Missing API Key**: Raises `ValueError` if OpenAI API key is not provided
2. **JSON Parsing**: Falls back to extracting JSON from markdown code blocks
3. **LLM Failures**: Propagates exceptions for proper retry handling
4. **MongoDB Errors**: Allows database errors to propagate for proper handling

## Performance Considerations

1. **LLM Calls**: Each analysis makes one LLM API call
   - Feasibility analysis: ~2-5 seconds
   - Improvement suggestions: ~3-7 seconds
   - Config generation: ~2-5 seconds

2. **MongoDB Operations**: Fast (< 100ms typically)
   - Document insertion with TTL
   - Document retrieval by task_id

3. **Async Operations**: All methods are async for non-blocking I/O

## Future Enhancements

Potential improvements for future iterations:

1. **Caching**: Cache analysis results for identical configurations
2. **Batch Processing**: Support batch analysis of multiple tools
3. **Streaming**: Stream LLM responses for real-time feedback
4. **Model Selection**: Allow configurable LLM models (GPT-3.5, GPT-4, etc.)
5. **Prompt Optimization**: Fine-tune prompts based on feedback
6. **Validation**: Add more sophisticated config validation
7. **Metrics**: Track analysis quality and performance metrics

## Troubleshooting

### Tests are Skipped

If tests show "MongoDB not available":
1. Ensure MongoDB is running on `localhost:27017`
2. Check connection with: `mongosh --eval "db.adminCommand('ping')"`
3. Verify no firewall blocking port 27017

### LLM API Errors

If you get OpenAI API errors:
1. Verify `OPENAI_API_KEY` is set correctly
2. Check API key has sufficient credits
3. Verify network connectivity to OpenAI API
4. Check rate limits haven't been exceeded

### JSON Parsing Errors

If LLM responses fail to parse:
1. The service includes fallback parsing for markdown code blocks
2. Check LLM temperature (lower = more consistent)
3. Review prompt templates for clarity
4. Consider adding more examples to prompts

## References

- [LangChain Documentation](https://python.langchain.com/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Hypothesis Testing Guide](https://hypothesis.readthedocs.io/)
- Design Document: `.kiro/specs/mcp-platform-backend/design.md`
- Requirements Document: `.kiro/specs/mcp-platform-backend/requirements.md`
