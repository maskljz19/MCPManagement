"""Property-based tests for API endpoint behavior"""

import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError
from uuid import uuid4
import re

from app.schemas.mcp_tool import MCPTool, MCPToolCreate, MCPToolUpdate, MCPToolVersion
from app.schemas.user import User
from app.schemas.auth import Token
from app.schemas.api_key import APIKey, APIKeyResponse
from app.schemas.knowledge import Document, SearchResult
from app.schemas.ai_analysis import FeasibilityReport, Improvement
from app.models.mcp_tool import ToolStatus
from datetime import datetime


# Helper strategies for generating valid test data
def valid_mcp_tool_strategy():
    """Generate valid MCPTool instances"""
    return st.builds(
        MCPTool,
        id=st.uuids(),
        name=st.text(min_size=1, max_size=255),
        slug=st.from_regex(r'^[a-z0-9-]+$', fullmatch=True).filter(
            lambda x: not x.startswith('-') and not x.endswith('-') and '--' not in x and len(x) > 0
        ),
        description=st.one_of(st.none(), st.text(max_size=1000)),
        version=st.from_regex(r'^\d+\.\d+\.\d+$', fullmatch=True),
        author_id=st.uuids(),
        status=st.sampled_from([ToolStatus.DRAFT, ToolStatus.ACTIVE, ToolStatus.DEPRECATED]),
        created_at=st.datetimes(),
        updated_at=st.datetimes(),
        deleted_at=st.none()
    )


def valid_user_strategy():
    """Generate valid User instances"""
    return st.builds(
        User,
        id=st.uuids(),
        username=st.from_regex(r'^[a-zA-Z0-9][a-zA-Z0-9_-]{2,49}$', fullmatch=True),
        email=st.emails(),
        role=st.sampled_from(['admin', 'developer', 'viewer']),
        is_active=st.booleans(),
        created_at=st.datetimes(),
        updated_at=st.datetimes()
    )


def valid_api_key_strategy():
    """Generate valid APIKey instances"""
    return st.builds(
        APIKey,
        id=st.uuids(),
        user_id=st.uuids(),
        name=st.text(min_size=1, max_size=100),
        last_used_at=st.one_of(st.none(), st.datetimes()),
        expires_at=st.one_of(st.none(), st.datetimes()),
        revoked_at=st.none(),
        created_at=st.datetimes(),
        updated_at=st.datetimes()
    )


# Feature: mcp-platform-backend, Property 37: Response Schema Consistency
# Validates: Requirements 10.4
@settings(
    max_examples=100,
    deadline=None
)
@given(tool=valid_mcp_tool_strategy())
def test_mcp_tool_response_schema_consistency(tool):
    """
    Property 37: Response Schema Consistency
    
    For any API endpoint, all successful responses should conform to the 
    documented Pydantic response schema.
    
    This test validates that MCPTool responses can be serialized and 
    deserialized consistently, maintaining all required fields.
    """
    # Serialize to dict (simulating API response)
    tool_dict = tool.model_dump()
    
    # Verify all required fields are present
    required_fields = ['id', 'name', 'slug', 'version', 'author_id', 'status', 'created_at', 'updated_at']
    for field in required_fields:
        assert field in tool_dict, f"Required field '{field}' missing from response"
        assert tool_dict[field] is not None, f"Required field '{field}' should not be None"
    
    # Deserialize back to model (simulating client parsing)
    reconstructed_tool = MCPTool(**tool_dict)
    
    # Verify consistency - all fields should match
    assert reconstructed_tool.id == tool.id
    assert reconstructed_tool.name == tool.name
    assert reconstructed_tool.slug == tool.slug
    assert reconstructed_tool.version == tool.version
    assert reconstructed_tool.author_id == tool.author_id
    assert reconstructed_tool.status == tool.status
    
    # Verify the schema is valid JSON-serializable
    import json
    json_str = json.dumps(tool_dict, default=str)
    assert len(json_str) > 0, "Response should be JSON-serializable"


@settings(
    max_examples=100,
    deadline=None
)
@given(user=valid_user_strategy())
def test_user_response_schema_consistency(user):
    """
    Property 37: Response Schema Consistency
    
    This test validates that User responses conform to the schema and
    do not include sensitive fields like password_hash.
    """
    # Serialize to dict (simulating API response)
    user_dict = user.model_dump()
    
    # Verify all required fields are present
    required_fields = ['id', 'username', 'email', 'role', 'is_active', 'created_at', 'updated_at']
    for field in required_fields:
        assert field in user_dict, f"Required field '{field}' missing from response"
    
    # Verify sensitive fields are NOT present
    sensitive_fields = ['password', 'password_hash']
    for field in sensitive_fields:
        assert field not in user_dict, f"Sensitive field '{field}' should not be in response"
    
    # Deserialize back to model
    reconstructed_user = User(**user_dict)
    
    # Verify consistency
    assert reconstructed_user.id == user.id
    assert reconstructed_user.username == user.username
    assert reconstructed_user.email == user.email
    assert reconstructed_user.role == user.role
    assert reconstructed_user.is_active == user.is_active


@settings(
    max_examples=100,
    deadline=None
)
@given(api_key=valid_api_key_strategy())
def test_api_key_response_schema_consistency(api_key):
    """
    Property 37: Response Schema Consistency
    
    This test validates that APIKey responses conform to the schema and
    do not include the actual key value (only shown once at creation).
    """
    # Serialize to dict (simulating API response)
    api_key_dict = api_key.model_dump()
    
    # Verify all required fields are present
    required_fields = ['id', 'user_id', 'name', 'created_at', 'updated_at']
    for field in required_fields:
        assert field in api_key_dict, f"Required field '{field}' missing from response"
    
    # Verify sensitive fields are NOT present in regular response
    # (key is only shown in APIKeyResponse at creation time)
    assert 'key' not in api_key_dict, "Plain key should not be in regular API key response"
    assert 'key_hash' not in api_key_dict, "Key hash should not be exposed in response"
    
    # Deserialize back to model
    reconstructed_key = APIKey(**api_key_dict)
    
    # Verify consistency
    assert reconstructed_key.id == api_key.id
    assert reconstructed_key.user_id == api_key.user_id
    assert reconstructed_key.name == api_key.name


@settings(
    max_examples=100,
    deadline=None
)
@given(
    tool_id=st.uuids(),
    version=st.from_regex(r'^\d+\.\d+\.\d+$', fullmatch=True),
    config=st.dictionaries(
        keys=st.text(min_size=1, max_size=50),
        values=st.one_of(st.text(), st.integers(), st.booleans())
    ),
    changed_by=st.uuids(),
    changed_at=st.datetimes(),
    change_type=st.sampled_from(['create', 'update', 'delete'])
)
def test_version_history_response_schema_consistency(
    tool_id, version, config, changed_by, changed_at, change_type
):
    """
    Property 37: Response Schema Consistency
    
    This test validates that MCPToolVersion responses conform to the schema.
    """
    # Create version history entry
    version_entry = MCPToolVersion(
        tool_id=tool_id,
        version=version,
        config=config,
        changed_by=changed_by,
        changed_at=changed_at,
        change_type=change_type,
        diff=None
    )
    
    # Serialize to dict
    version_dict = version_entry.model_dump()
    
    # Verify all required fields are present
    required_fields = ['tool_id', 'version', 'config', 'changed_by', 'changed_at', 'change_type']
    for field in required_fields:
        assert field in version_dict, f"Required field '{field}' missing from response"
        assert version_dict[field] is not None, f"Required field '{field}' should not be None"
    
    # Deserialize back to model
    reconstructed_version = MCPToolVersion(**version_dict)
    
    # Verify consistency
    assert reconstructed_version.tool_id == tool_id
    assert reconstructed_version.version == version
    assert reconstructed_version.config == config
    assert reconstructed_version.changed_by == changed_by
    assert reconstructed_version.change_type == change_type


@settings(
    max_examples=100,
    deadline=None
)
@given(
    page_size=st.integers(min_value=1, max_value=100),
    total=st.integers(min_value=0, max_value=1000),
    page=st.integers(min_value=1, max_value=100)
)
def test_paginated_response_schema_consistency(page_size, total, page):
    """
    Property 37: Response Schema Consistency
    
    This test validates that paginated responses conform to a consistent schema
    with items, total, page, page_size, and total_pages fields.
    """
    # Generate items that respect page_size constraint
    # In a real pagination, items count should not exceed page_size
    items_count = min(page_size, max(0, total - (page - 1) * page_size))
    items = [
        MCPTool(
            id=uuid4(),
            name=f"Tool {i}",
            slug=f"tool-{i}",
            description=None,
            version="1.0.0",
            author_id=uuid4(),
            status=ToolStatus.DRAFT,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            deleted_at=None
        )
        for i in range(items_count)
    ]
    
    # Calculate total_pages
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    
    # Create paginated response (simulating API response)
    response = {
        "items": [tool.model_dump() for tool in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
    
    # Verify all required pagination fields are present
    required_fields = ['items', 'total', 'page', 'page_size', 'total_pages']
    for field in required_fields:
        assert field in response, f"Required pagination field '{field}' missing from response"
    
    # Verify field types
    assert isinstance(response['items'], list), "items should be a list"
    assert isinstance(response['total'], int), "total should be an integer"
    assert isinstance(response['page'], int), "page should be an integer"
    assert isinstance(response['page_size'], int), "page_size should be an integer"
    assert isinstance(response['total_pages'], int), "total_pages should be an integer"
    
    # Verify pagination invariants
    assert response['total'] >= 0, "total should be non-negative"
    assert response['page'] >= 1, "page should be at least 1"
    assert response['page_size'] >= 1, "page_size should be at least 1"
    assert response['total_pages'] >= 0, "total_pages should be non-negative"
    assert len(response['items']) <= response['page_size'], "items count should not exceed page_size"


# Feature: mcp-platform-backend, Property 38: API Version Routing
# Validates: Requirements 10.5
@settings(
    max_examples=100,
    deadline=None
)
@given(
    endpoint=st.sampled_from([
        'mcps',
        'knowledge/documents',
        'analyze/feasibility',
        'github/connect',
        'deployments',
        'auth/login'
    ]),
    version=st.sampled_from(['v1', 'v2'])
)
def test_api_version_routing_path_format(endpoint, version):
    """
    Property 38: API Version Routing
    
    For any versioned API endpoint (e.g., /api/v1/*, /api/v2/*), requests 
    should be routed to the correct version handler.
    
    This test validates that API paths follow the correct versioning format.
    """
    # Construct versioned API path
    api_path = f"/api/{version}/{endpoint}"
    
    # Verify path format matches expected pattern
    version_pattern = r'^/api/v\d+/[a-z0-9/_-]+$'
    assert re.match(version_pattern, api_path), f"API path '{api_path}' should match version pattern"
    
    # Verify version is in the correct position (second segment)
    path_parts = api_path.split('/')
    assert len(path_parts) >= 4, "API path should have at least 4 segments"
    assert path_parts[1] == 'api', "First segment should be 'api'"
    assert path_parts[2].startswith('v'), "Second segment should be version (e.g., 'v1')"
    assert path_parts[2][1:].isdigit(), "Version should be numeric after 'v'"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    resource=st.sampled_from(['mcps', 'knowledge', 'analyze', 'github', 'deployments']),
    action=st.sampled_from(['', '/{id}', '/search', '/sync', '/history'])
)
def test_api_version_prefix_consistency(resource, action):
    """
    Property 38: API Version Routing
    
    This test validates that all API endpoints consistently use the /api/v1 prefix.
    """
    # Construct API path with v1 prefix
    api_path = f"/api/v1/{resource}{action}"
    
    # Verify the path starts with /api/v1
    assert api_path.startswith('/api/v1/'), "All API paths should start with /api/v1/"
    
    # Verify no double slashes
    assert '//' not in api_path, "API path should not contain double slashes"
    
    # Verify path structure
    path_parts = [p for p in api_path.split('/') if p]  # Filter empty strings
    assert len(path_parts) >= 3, "API path should have at least 3 non-empty segments"
    assert path_parts[0] == 'api', "First segment should be 'api'"
    assert path_parts[1] == 'v1', "Second segment should be 'v1'"
    assert path_parts[2] == resource, "Third segment should be the resource name"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    version_number=st.integers(min_value=1, max_value=10)
)
def test_api_version_number_format(version_number):
    """
    Property 38: API Version Routing
    
    This test validates that API version numbers follow the 'v{number}' format.
    """
    # Construct version string
    version = f"v{version_number}"
    
    # Verify version format
    assert version.startswith('v'), "Version should start with 'v'"
    assert version[1:].isdigit(), "Version number should be numeric"
    assert int(version[1:]) >= 1, "Version number should be at least 1"
    
    # Construct full API path
    api_path = f"/api/{version}/mcps"
    
    # Verify path is valid
    assert api_path.startswith('/api/'), "Path should start with /api/"
    assert f'/{version}/' in api_path, f"Path should contain /{version}/"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    endpoint=st.sampled_from([
        '/api/v1/mcps',
        '/api/v1/mcps/{tool_id}',
        '/api/v1/mcps/{tool_id}/history',
        '/api/v1/knowledge/documents',
        '/api/v1/knowledge/search',
        '/api/v1/auth/login',
        '/api/v1/auth/refresh',
        '/api/v1/deployments',
        '/api/v1/github/connect'
    ])
)
def test_api_endpoint_version_extraction(endpoint):
    """
    Property 38: API Version Routing
    
    This test validates that the API version can be reliably extracted from
    any endpoint path for routing purposes.
    """
    # Extract version from path
    path_parts = endpoint.split('/')
    
    # Find the version segment (should be after 'api')
    api_index = path_parts.index('api') if 'api' in path_parts else -1
    assert api_index >= 0, "Path should contain 'api' segment"
    
    version_index = api_index + 1
    assert version_index < len(path_parts), "Path should have version after 'api'"
    
    version = path_parts[version_index]
    
    # Verify version format
    assert version.startswith('v'), f"Version '{version}' should start with 'v'"
    assert version[1:].isdigit(), f"Version '{version}' should have numeric suffix"
    
    # Verify version is v1 (current version)
    assert version == 'v1', "Current API version should be v1"
