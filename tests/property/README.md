# Property-Based Tests for MCP Platform Backend

This directory contains property-based tests using Hypothesis to validate correctness properties defined in the design document.

## Overview

Property-based tests verify universal properties that should hold for all valid inputs, rather than testing specific examples. Each test runs 100 iterations with randomly generated inputs to ensure comprehensive coverage.

## Test Files

- `test_mcp_properties.py` - Tests for MCP Manager (tool CRUD, versioning, caching)
- `test_auth_properties.py` - Tests for Authentication Service (JWT, API keys, permissions)
- `test_cache_properties.py` - Tests for Cache Service (Redis operations, TTL, invalidation)
- `test_database_properties.py` - Tests for Database operations (connections, transactions)
- `test_migration_properties.py` - Tests for Alembic migrations (execution, rollback)
- `test_validation_properties.py` - Tests for Input validation (Pydantic schemas)
- `test_knowledge_properties.py` - Tests for Knowledge Base Service (documents, embeddings, search)

## Prerequisites

### Required Services

The property tests require the following services to be running:

1. **MongoDB** (localhost:27017)
   - Used for document storage and version history
   - Tests will be skipped if MongoDB is not available

2. **Redis** (localhost:6379)
   - Used for caching and session management
   - Tests will be skipped if Redis is not available

3. **Qdrant** (optional, uses in-memory mode for tests)
   - Used for vector storage and semantic search
   - Tests use in-memory Qdrant client

### Starting Services with Docker

```bash
# Start MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:latest

# Start Redis
docker run -d --name redis -p 6379:6379 redis:latest

# Optional: Start Qdrant (if not using in-memory mode)
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
```

### Environment Variables

For Knowledge Base tests that use real OpenAI embeddings:

```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

If `OPENAI_API_KEY` is not set, tests will use deterministic mock embeddings.

## Running Tests

### Run All Property Tests

```bash
pytest tests/property/ -v
```

### Run Specific Test File

```bash
pytest tests/property/test_knowledge_properties.py -v
```

### Run Specific Test

```bash
pytest tests/property/test_knowledge_properties.py::test_dual_store_document_consistency -v
```

### Run with Coverage

```bash
pytest tests/property/ --cov=app --cov-report=html
```

### Run with Hypothesis Statistics

```bash
pytest tests/property/ -v --hypothesis-show-statistics
```

## Test Configuration

Property tests are configured in `pytest.ini`:

```ini
[pytest]
markers =
    property: Property-based tests using Hypothesis
    asyncio: Async tests

# Hypothesis settings
hypothesis_profile = default
```

Each test uses these Hypothesis settings:
- `max_examples=100` - Run 100 iterations per test
- `deadline=None` - No time limit per example
- `suppress_health_check=[HealthCheck.function_scoped_fixture]` - Allow function-scoped fixtures

## Property Test Structure

Each property test follows this structure:

```python
# Feature: mcp-platform-backend, Property N: Property Name
@given(input_data=strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_name(input_data, fixture):
    """
    Property N: Property Name
    
    For any <input>, <property should hold>.
    
    Validates: Requirements X.Y
    """
    # Arrange
    # Act
    # Assert
```

## Knowledge Base Service Tests

### Property 5: Dual-Store Document Consistency
Validates that documents are stored in both MongoDB and Qdrant with matching IDs.

### Property 6: Search Result Ordering
Validates that search results are ordered by descending similarity score.

### Property 7: Document Deletion Consistency
Validates that documents are removed from both MongoDB and Qdrant when deleted.

### Property 8: Embedding Dimension Consistency
Validates that all embeddings have the same dimension (1536 for text-embedding-3-small).

## Troubleshooting

### Tests are Skipped

If tests are skipped with messages like "MongoDB not available" or "Redis not available":

1. Ensure the required services are running
2. Check connection settings in `tests/conftest.py`
3. Verify network connectivity to localhost

### Hypothesis Finds Failures

When Hypothesis finds a failing example:

1. The test output will show the minimal failing case
2. Hypothesis will save the example in `.hypothesis/examples/`
3. The same example will be tested first in future runs
4. Fix the implementation or adjust the property
5. Re-run tests to verify the fix

### Slow Tests

Property tests can be slow because they run 100 iterations. To speed up during development:

```python
@settings(max_examples=10)  # Reduce iterations temporarily
```

### Memory Issues

If tests consume too much memory:

1. Reduce `max_examples` in test settings
2. Ensure proper cleanup in fixtures
3. Check for resource leaks in the implementation

## Continuous Integration

In CI environments:

1. Start required services (MongoDB, Redis) before running tests
2. Use Docker Compose for service orchestration
3. Set appropriate timeouts for service startup
4. Run extended property tests (1000 iterations) nightly

Example CI configuration:

```yaml
# .github/workflows/test.yml
- name: Start services
  run: docker-compose up -d mongodb redis

- name: Wait for services
  run: |
    timeout 30 bash -c 'until docker exec mongodb mongosh --eval "db.adminCommand(\"ping\")"; do sleep 1; done'
    timeout 30 bash -c 'until docker exec redis redis-cli ping; do sleep 1; done'

- name: Run property tests
  run: pytest tests/property/ -v --hypothesis-profile=ci
```

## References

- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Property-Based Testing Guide](https://hypothesis.works/articles/what-is-property-based-testing/)
- [Design Document](../../.kiro/specs/mcp-platform-backend/design.md) - See Correctness Properties section
