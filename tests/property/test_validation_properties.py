"""Property-based tests for input validation and error handling"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError
from typing import Dict, Any
import re

from app.schemas.mcp_tool import MCPToolCreate, MCPToolUpdate
from app.schemas.knowledge import DocumentCreate, SearchQuery
from app.schemas.user import UserCreate, UserUpdate
from app.schemas.ai_analysis import ConfigRequirements, Improvement
from app.schemas.api_key import APIKeyCreate
from datetime import datetime, timedelta
from uuid import uuid4


# Helper strategies for generating test data
def invalid_slug_strategy():
    """Generate invalid slugs that should fail validation"""
    return st.one_of(
        st.text(min_size=1).filter(lambda x: not re.match(r'^[a-z0-9-]+$', x)),  # Invalid characters
        st.just(''),  # Empty string
        st.just('-start'),  # Starts with hyphen
        st.just('end-'),  # Ends with hyphen
        st.just('double--hyphen'),  # Consecutive hyphens
        st.just('UPPERCASE'),  # Uppercase letters
        st.just('has spaces'),  # Spaces
        st.just('special@chars'),  # Special characters
    )


def invalid_version_strategy():
    """Generate invalid version strings that should fail validation"""
    return st.one_of(
        st.just('1.0'),  # Missing patch version
        st.just('1'),  # Only major version
        st.just('v1.0.0'),  # Has 'v' prefix
        st.just('1.0.0-beta'),  # Has pre-release tag
        st.just('1.0.0.0'),  # Too many parts
        st.just('a.b.c'),  # Non-numeric
        st.just(''),  # Empty
        st.just('1.-1.0'),  # Negative number
    )


def invalid_email_strategy():
    """Generate invalid email addresses"""
    return st.one_of(
        st.just('notanemail'),  # No @ symbol
        st.just('@example.com'),  # Missing local part
        st.just('user@'),  # Missing domain
        st.just('user @example.com'),  # Space in email
        st.just(''),  # Empty
        st.just('user@@example.com'),  # Double @
    )


def invalid_password_strategy():
    """Generate passwords that don't meet strength requirements"""
    return st.one_of(
        st.just('short'),  # Too short (< 8 chars)
        st.just('alllowercase123'),  # No uppercase
        st.just('ALLUPPERCASE123'),  # No lowercase
        st.just('NoNumbers'),  # No digits
        st.just(''),  # Empty
        st.just('1234567'),  # Only 7 chars
    )


# Feature: mcp-platform-backend, Property 35: Input Validation Rejection
# Validates: Requirements 10.2, 11.1
@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_slug=invalid_slug_strategy(),
    valid_name=st.text(min_size=1, max_size=255),
    valid_version=st.from_regex(r'^\d+\.\d+\.\d+$', fullmatch=True),
)
def test_mcp_tool_invalid_slug_rejection(invalid_slug, valid_name, valid_version):
    """
    Property 35: Input Validation Rejection
    
    For any API request with invalid payload data, the response should be 
    HTTP 422 with detailed validation errors.
    
    This test validates that MCPToolCreate rejects invalid slugs.
    """
    # Attempt to create MCPToolCreate with invalid slug
    with pytest.raises(ValidationError) as exc_info:
        MCPToolCreate(
            name=valid_name,
            slug=invalid_slug,
            version=valid_version,
            config={},
            author_id=uuid4()
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the slug field
    slug_errors = [e for e in errors if 'slug' in str(e.get('loc', []))]
    assert len(slug_errors) > 0, "Should have at least one slug validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_version=invalid_version_strategy(),
    valid_name=st.text(min_size=1, max_size=255),
    valid_slug=st.from_regex(r'^[a-z0-9-]+$', fullmatch=True).filter(
        lambda x: not x.startswith('-') and not x.endswith('-') and '--' not in x and len(x) > 0
    ),
)
def test_mcp_tool_invalid_version_rejection(invalid_version, valid_name, valid_slug):
    """
    Property 35: Input Validation Rejection
    
    This test validates that MCPToolCreate rejects invalid version strings.
    """
    # Attempt to create MCPToolCreate with invalid version
    with pytest.raises(ValidationError) as exc_info:
        MCPToolCreate(
            name=valid_name,
            slug=valid_slug,
            version=invalid_version,
            config={},
            author_id=uuid4()
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the version field
    version_errors = [e for e in errors if 'version' in str(e.get('loc', []))]
    assert len(version_errors) > 0, "Should have at least one version validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_email=invalid_email_strategy(),
    valid_username=st.from_regex(r'^[a-zA-Z0-9_-]+$', fullmatch=True).filter(
        lambda x: len(x) >= 3 and not x.startswith('_') and not x.startswith('-')
    ),
    valid_password=st.text(min_size=8, max_size=100).filter(
        lambda x: re.search(r'[A-Z]', x) and re.search(r'[a-z]', x) and re.search(r'[0-9]', x)
    ),
)
def test_user_invalid_email_rejection(invalid_email, valid_username, valid_password):
    """
    Property 35: Input Validation Rejection
    
    This test validates that UserCreate rejects invalid email addresses.
    """
    # Attempt to create UserCreate with invalid email
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            username=valid_username,
            email=invalid_email,
            password=valid_password
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the email field
    email_errors = [e for e in errors if 'email' in str(e.get('loc', []))]
    assert len(email_errors) > 0, "Should have at least one email validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_password=invalid_password_strategy(),
    valid_username=st.from_regex(r'^[a-zA-Z0-9_-]+$', fullmatch=True).filter(
        lambda x: len(x) >= 3 and not x.startswith('_') and not x.startswith('-')
    ),
    valid_email=st.emails(),
)
def test_user_weak_password_rejection(invalid_password, valid_username, valid_email):
    """
    Property 35: Input Validation Rejection
    
    This test validates that UserCreate rejects weak passwords.
    """
    # Attempt to create UserCreate with weak password
    with pytest.raises(ValidationError) as exc_info:
        UserCreate(
            username=valid_username,
            email=valid_email,
            password=invalid_password
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the password field
    password_errors = [e for e in errors if 'password' in str(e.get('loc', []))]
    assert len(password_errors) > 0, "Should have at least one password validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    empty_title=st.just(''),
    valid_content=st.text(min_size=1),
)
def test_document_empty_title_rejection(empty_title, valid_content):
    """
    Property 35: Input Validation Rejection
    
    This test validates that DocumentCreate rejects empty titles.
    """
    # Attempt to create DocumentCreate with empty title
    with pytest.raises(ValidationError) as exc_info:
        DocumentCreate(
            title=empty_title,
            content=valid_content
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0


@settings(
    max_examples=100,
    deadline=None
)
@given(
    limit=st.integers(max_value=0).filter(lambda x: x < 1) | st.integers(min_value=101),
    valid_query=st.text(min_size=1),
)
def test_search_query_invalid_limit_rejection(limit, valid_query):
    """
    Property 35: Input Validation Rejection
    
    This test validates that SearchQuery rejects invalid limit values (< 1 or > 100).
    """
    # Attempt to create SearchQuery with invalid limit
    with pytest.raises(ValidationError) as exc_info:
        SearchQuery(
            query=valid_query,
            limit=limit
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the limit field
    limit_errors = [e for e in errors if 'limit' in str(e.get('loc', []))]
    assert len(limit_errors) > 0, "Should have at least one limit validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    past_date=st.datetimes(
        min_value=datetime(2000, 1, 1),
        max_value=datetime.utcnow() - timedelta(days=1)
    ),
    valid_name=st.text(min_size=1, max_size=100),
)
def test_api_key_past_expiry_rejection(past_date, valid_name):
    """
    Property 35: Input Validation Rejection
    
    This test validates that APIKeyCreate rejects expiry dates in the past.
    """
    # Attempt to create APIKeyCreate with past expiry date
    with pytest.raises(ValidationError) as exc_info:
        APIKeyCreate(
            name=valid_name,
            expires_at=past_date
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the expires_at field
    expiry_errors = [e for e in errors if 'expires_at' in str(e.get('loc', []))]
    assert len(expiry_errors) > 0, "Should have at least one expiry validation error"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_priority=st.text().filter(lambda x: x not in ['low', 'medium', 'high', 'critical']),
    valid_category=st.text(min_size=1),
    valid_title=st.text(min_size=1, max_size=200),
    valid_description=st.text(min_size=1),
)
def test_improvement_invalid_priority_rejection(
    invalid_priority, valid_category, valid_title, valid_description
):
    """
    Property 35: Input Validation Rejection
    
    This test validates that Improvement rejects invalid priority values.
    """
    assume(invalid_priority not in ['low', 'medium', 'high', 'critical'])
    
    # Attempt to create Improvement with invalid priority
    with pytest.raises(ValidationError) as exc_info:
        Improvement(
            category=valid_category,
            title=valid_title,
            description=valid_description,
            priority=invalid_priority,
            effort='medium',
            impact='high'
        )
    
    # Verify that validation error was raised
    assert exc_info.value is not None
    errors = exc_info.value.errors()
    assert len(errors) > 0
    
    # Verify that the error is related to the priority field
    priority_errors = [e for e in errors if 'priority' in str(e.get('loc', []))]
    assert len(priority_errors) > 0, "Should have at least one priority validation error"



# Feature: mcp-platform-backend, Property 36: Validation Error Detail
# Validates: Requirements 10.3
@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_slug=invalid_slug_strategy(),
    valid_name=st.text(min_size=1, max_size=255),
    valid_version=st.from_regex(r'^\d+\.\d+\.\d+$', fullmatch=True),
)
def test_validation_error_contains_field_details(invalid_slug, valid_name, valid_version):
    """
    Property 36: Validation Error Detail
    
    For any request validation failure, the error response should contain 
    field-level error information identifying which fields failed validation.
    
    This test validates that validation errors include:
    1. Field location (which field failed)
    2. Error message
    3. Error type
    """
    # Attempt to create MCPToolCreate with invalid slug
    with pytest.raises(ValidationError) as exc_info:
        MCPToolCreate(
            name=valid_name,
            slug=invalid_slug,
            version=valid_version,
            config={},
            author_id=uuid4()
        )
    
    # Verify that validation error contains detailed information
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"
    
    # Check that each error has required fields
    for error in errors:
        # Field location
        assert 'loc' in error, "Error should contain 'loc' field"
        assert len(error['loc']) > 0, "Location should not be empty"
        
        # Error message
        assert 'msg' in error, "Error should contain 'msg' field"
        assert len(error['msg']) > 0, "Message should not be empty"
        
        # Error type
        assert 'type' in error, "Error should contain 'type' field"
        assert len(error['type']) > 0, "Type should not be empty"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    invalid_version=invalid_version_strategy(),
    valid_name=st.text(min_size=1, max_size=255),
    valid_slug=st.from_regex(r'^[a-z0-9-]+$', fullmatch=True).filter(
        lambda x: not x.startswith('-') and not x.endswith('-') and '--' not in x and len(x) > 0
    ),
)
def test_validation_error_identifies_specific_field(invalid_version, valid_name, valid_slug):
    """
    Property 36: Validation Error Detail
    
    This test validates that validation errors correctly identify the specific
    field that failed validation (in this case, the version field).
    """
    # Attempt to create MCPToolCreate with invalid version
    with pytest.raises(ValidationError) as exc_info:
        MCPToolCreate(
            name=valid_name,
            slug=valid_slug,
            version=invalid_version,
            config={},
            author_id=uuid4()
        )
    
    # Verify that validation error identifies the version field
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"
    
    # At least one error should be related to the version field
    version_errors = [e for e in errors if 'version' in str(e.get('loc', []))]
    assert len(version_errors) > 0, "Should have at least one error for the version field"
    
    # Verify the error provides useful information
    for error in version_errors:
        assert error['msg'] is not None and len(error['msg']) > 0, "Error message should be informative"
        assert error['type'] is not None, "Error type should be specified"


@settings(
    max_examples=100,
    deadline=None
)
@given(
    empty_content=st.just(''),
    valid_title=st.text(min_size=1, max_size=500),
)
def test_validation_error_for_empty_required_field(empty_content, valid_title):
    """
    Property 36: Validation Error Detail
    
    This test validates that validation errors for empty required fields
    provide clear field-level information.
    """
    # Attempt to create DocumentCreate with empty content
    with pytest.raises(ValidationError) as exc_info:
        DocumentCreate(
            title=valid_title,
            content=empty_content
        )
    
    # Verify that validation error identifies the content field
    errors = exc_info.value.errors()
    assert len(errors) > 0, "Should have at least one validation error"
    
    # Find errors related to the content field
    content_errors = [e for e in errors if 'content' in str(e.get('loc', []))]
    assert len(content_errors) > 0, "Should have at least one error for the content field"
    
    # Verify error details
    for error in content_errors:
        # Should have location pointing to content field
        assert 'content' in error['loc'], "Error location should include 'content'"
        
        # Should have a descriptive message
        assert 'msg' in error and len(error['msg']) > 0, "Should have error message"
        
        # Should have error type
        assert 'type' in error, "Should have error type"
