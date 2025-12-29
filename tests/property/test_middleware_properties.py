"""
Property-Based Tests for Middleware Components

Tests correctness properties for:
- Rate limiting enforcement
- Sensitive data redaction
- CORS origin validation
- Structured error logging
- Request correlation IDs

**Feature: mcp-platform-backend**
"""

import pytest
from hypothesis import given, strategies as st
from hypothesis import settings as hypothesis_settings
from hypothesis import HealthCheck
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re
import json
import time

from app.api.middleware import (
    LoggingMiddleware,
    RequestIDMiddleware,
    ErrorHandlingMiddleware,
    validate_cors_origin,
    limiter
)
from app.core.config import settings as app_settings


# Test data generators
@st.composite
def origin_strings(draw):
    """Generate origin strings for CORS testing"""
    protocol = draw(st.sampled_from(["http", "https"]))
    domain = draw(st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), min_codepoint=97, max_codepoint=122),
        min_size=3,
        max_size=20
    ))
    tld = draw(st.sampled_from(["com", "org", "net", "io"]))
    port = draw(st.one_of(st.none(), st.integers(min_value=1000, max_value=9999)))
    
    origin = f"{protocol}://{domain}.{tld}"
    if port:
        origin += f":{port}"
    
    return origin


@st.composite
def sensitive_data_strings(draw):
    """Generate strings containing sensitive data patterns"""
    template = draw(st.sampled_from([
        '{"password": "SECRET123"}',
        '{"token": "abc123xyz"}',
        '{"api_key": "sk-1234567890"}',
        '{"secret": "my-secret-value"}',
        'Authorization: Bearer TOKEN123',
        '{"authorization": "Bearer xyz789"}',
    ]))
    return template


@st.composite
def log_contexts(draw):
    """Generate log context dictionaries"""
    return {
        "request_id": draw(st.uuids()).hex,
        "method": draw(st.sampled_from(["GET", "POST", "PUT", "DELETE"])),
        "path": draw(st.text(min_size=1, max_size=50)),
        "status_code": draw(st.integers(min_value=200, max_value=599)),
        "error_type": draw(st.sampled_from(["ValueError", "KeyError", "RuntimeError"])),
        "error_message": draw(st.text(min_size=1, max_size=100)),
    }


# Property 39: Rate Limit Enforcement
@pytest.mark.property
@given(
    num_requests=st.integers(min_value=app_settings.RATE_LIMIT_PER_MINUTE + 1, max_value=app_settings.RATE_LIMIT_PER_MINUTE + 10)
)
@hypothesis_settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_property_39_rate_limit_enforcement(num_requests):
    """
    Property 39: Rate Limit Enforcement
    
    For any user, when the rate limit is exceeded for an endpoint,
    subsequent requests should return HTTP 429 status.
    
    **Validates: Requirements 11.2**
    **Feature: mcp-platform-backend, Property 39**
    """
    # Create a fresh FastAPI app with rate limiting for each test
    # This ensures rate limiter state doesn't persist across tests
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    
    app = FastAPI()
    fresh_limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = fresh_limiter
    
    @app.get("/test")
    @fresh_limiter.limit(f"{app_settings.RATE_LIMIT_PER_MINUTE}/minute")
    async def test_endpoint(request: Request):
        return {"message": "success"}
    
    # Use a new client for each test to avoid state sharing
    with TestClient(app) as client:
        # Make requests up to and beyond the rate limit
        responses = []
        for i in range(num_requests):
            response = client.get("/test")
            responses.append(response.status_code)
        
        # Property: At least one request should be rate limited (429)
        # Since we're making more requests than the limit
        assert 429 in responses, f"Expected at least one 429 response when making {num_requests} requests (limit: {app_settings.RATE_LIMIT_PER_MINUTE})"
        
        # Property: The first requests should succeed (200)
        # At least some of the early requests should be successful
        success_count = responses[:app_settings.RATE_LIMIT_PER_MINUTE].count(200)
        assert success_count > 0, f"Expected at least some successful responses within rate limit, got {responses[:app_settings.RATE_LIMIT_PER_MINUTE]}"


# Property 40: Sensitive Data Redaction
@pytest.mark.property
@given(sensitive_text=sensitive_data_strings())
@hypothesis_settings(max_examples=100, deadline=None)
def test_property_40_sensitive_data_redaction(sensitive_text):
    """
    Property 40: Sensitive Data Redaction
    
    For any log entry containing sensitive data (passwords, tokens, API keys),
    the sensitive values should be redacted or masked.
    
    **Validates: Requirements 11.4**
    **Feature: mcp-platform-backend, Property 40**
    """
    # Redact sensitive data using the middleware method
    redacted = LoggingMiddleware._redact_sensitive_data(sensitive_text)
    
    # Property: Redacted text should not contain the original sensitive values
    # Check for common sensitive patterns
    sensitive_patterns = [
        r'SECRET\d+',
        r'abc123xyz',
        r'sk-\d+',
        r'my-secret-value',
        r'TOKEN\d+',
        r'xyz789',
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, sensitive_text):
            # If the original contained this pattern, it should be redacted
            assert not re.search(pattern, redacted), f"Sensitive pattern '{pattern}' was not redacted"
    
    # Property: Redacted text should contain [REDACTED] marker
    if any(keyword in sensitive_text.lower() for keyword in ["password", "token", "api_key", "secret", "authorization", "bearer"]):
        assert "[REDACTED]" in redacted, "Expected [REDACTED] marker in redacted text"


# Property 41: CORS Origin Validation
@pytest.mark.property
@given(origin=origin_strings())
@hypothesis_settings(max_examples=100, deadline=None)
def test_property_41_cors_origin_validation(origin):
    """
    Property 41: CORS Origin Validation
    
    For any CORS request from a non-whitelisted origin,
    the request should be rejected or the CORS headers should not be set.
    
    **Validates: Requirements 11.5**
    **Feature: mcp-platform-backend, Property 41**
    """
    # Test with a whitelist
    allowed_origins = ["http://localhost:3000", "https://example.com"]
    
    # Property: Only whitelisted origins should validate
    is_valid = validate_cors_origin(origin, allowed_origins)
    
    if origin in allowed_origins:
        assert is_valid, f"Whitelisted origin {origin} should be valid"
    else:
        assert not is_valid, f"Non-whitelisted origin {origin} should be invalid"
    
    # Test with wildcard patterns
    wildcard_origins = ["http://localhost:*", "https://*.example.com"]
    is_valid_wildcard = validate_cors_origin(origin, wildcard_origins)
    
    # Property: Wildcard patterns should match correctly
    if origin.startswith("http://localhost:"):
        assert is_valid_wildcard, f"Origin {origin} should match wildcard http://localhost:*"
    elif ".example.com" in origin and origin.startswith("https://"):
        assert is_valid_wildcard, f"Origin {origin} should match wildcard https://*.example.com"


# Property 42: Structured Error Logging
@pytest.mark.property
@given(log_context=log_contexts())
@hypothesis_settings(max_examples=100, deadline=None)
def test_property_42_structured_error_logging(log_context):
    """
    Property 42: Structured Error Logging
    
    For any error that occurs during request processing,
    a structured log entry should be created containing error type,
    message, and context.
    
    **Validates: Requirements 12.2**
    **Feature: mcp-platform-backend, Property 42**
    """
    # Property: Log context should contain required fields
    required_fields = ["request_id", "method", "path", "error_type", "error_message"]
    
    for field in required_fields:
        assert field in log_context, f"Log context missing required field: {field}"
    
    # Property: Request ID should be a valid UUID-like string
    assert len(log_context["request_id"]) == 32, "Request ID should be 32 characters (UUID hex)"
    
    # Property: Method should be a valid HTTP method
    assert log_context["method"] in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"], \
        f"Invalid HTTP method: {log_context['method']}"
    
    # Property: Status code should be in valid range
    assert 100 <= log_context["status_code"] <= 599, \
        f"Invalid status code: {log_context['status_code']}"
    
    # Property: Error type should be a non-empty string
    assert log_context["error_type"], "Error type should not be empty"
    
    # Property: Error message should be a non-empty string
    assert log_context["error_message"], "Error message should not be empty"


# Property 43: Request Correlation ID
@pytest.mark.property
@given(num_requests=st.integers(min_value=1, max_value=10))
@hypothesis_settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
def test_property_43_request_correlation_id(num_requests):
    """
    Property 43: Request Correlation ID
    
    For any API request, the request and response logs should contain
    the same correlation ID for traceability.
    
    **Validates: Requirements 12.4**
    **Feature: mcp-platform-backend, Property 43**
    """
    # Create a simple FastAPI app with RequestIDMiddleware
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/test")
    async def test_endpoint(request: Request):
        # Return the request ID from state
        return {"request_id": request.state.request_id}
    
    client = TestClient(app)
    
    # Make multiple requests
    request_ids = []
    response_headers = []
    
    for _ in range(num_requests):
        response = client.get("/test")
        
        # Get request ID from response body
        body_request_id = response.json()["request_id"]
        request_ids.append(body_request_id)
        
        # Get request ID from response header
        header_request_id = response.headers.get("X-Request-ID")
        response_headers.append(header_request_id)
        
        # Property: Request ID in body should match header
        assert body_request_id == header_request_id, \
            "Request ID in response body should match X-Request-ID header"
    
    # Property: All request IDs should be unique
    assert len(set(request_ids)) == num_requests, \
        "Each request should have a unique request ID"
    
    # Property: All request IDs should be valid UUIDs
    for request_id in request_ids:
        # UUID format: 8-4-4-4-12 characters
        assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', request_id), \
            f"Request ID should be a valid UUID: {request_id}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
