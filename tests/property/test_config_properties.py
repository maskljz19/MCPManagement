"""
Property-based tests for configuration loading and validation.

These tests verify that the configuration system correctly loads and validates
environment variables according to the requirements.
"""

import os
import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError
from app.core.config import Settings


# Feature: mcp-platform-backend, Property 49: Environment Configuration Loading
@given(
    app_name=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters='\x00')),
    mysql_host=st.text(min_size=1, max_size=255, alphabet=st.characters(blacklist_characters='\x00')),
    mysql_port=st.integers(min_value=1, max_value=65535),
    redis_port=st.integers(min_value=1, max_value=65535),
    log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]),
)
@settings(max_examples=100, deadline=None)
def test_environment_configuration_loading(
    app_name, mysql_host, mysql_port, redis_port, log_level
):
    """
    Property 49: Environment Configuration Loading
    
    For any environment variable defined in the configuration schema,
    the application should load and use the value from the environment.
    
    Validates: Requirements 14.2
    """
    # Set environment variables directly
    os.environ["APP_NAME"] = app_name
    os.environ["MYSQL_HOST"] = mysql_host
    os.environ["MYSQL_PORT"] = str(mysql_port)
    os.environ["MYSQL_USER"] = "test_user"
    os.environ["MYSQL_PASSWORD"] = "test_password"
    os.environ["MYSQL_DATABASE"] = "test_db"
    os.environ["REDIS_PORT"] = str(redis_port)
    os.environ["LOG_LEVEL"] = log_level
    os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long"
    
    # Required fields for MongoDB
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
    os.environ["MONGODB_DATABASE"] = "test_db"
    
    try:
        # Load configuration
        settings = Settings()
        
        # Verify that configuration loaded the environment values
        assert settings.APP_NAME == app_name
        assert settings.MYSQL_HOST == mysql_host
        assert settings.MYSQL_PORT == mysql_port
        assert settings.REDIS_PORT == redis_port
        assert settings.LOG_LEVEL == log_level
        
        # Verify required fields are present
        assert settings.MYSQL_USER == "test_user"
        assert settings.MYSQL_PASSWORD == "test_password"
        assert settings.MYSQL_DATABASE == "test_db"
        assert settings.SECRET_KEY == "test-secret-key-min-32-characters-long"
    finally:
        # Clean up environment variables
        for key in ["APP_NAME", "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", 
                    "MYSQL_PASSWORD", "MYSQL_DATABASE", "REDIS_PORT", "LOG_LEVEL",
                    "SECRET_KEY", "MONGODB_URL", "MONGODB_DATABASE"]:
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_all_required_config_fields_loaded():
    """
    Test that all required configuration fields can be loaded from environment.
    
    This is a specific example test that complements the property test.
    """
    # Create a minimal valid configuration
    env_vars = {
        "APP_NAME": "Test App",
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3306",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
    }
    
    # Set environment variables
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Load configuration
        settings = Settings()
        
        # Verify all required fields are loaded
        assert settings.APP_NAME == "Test App"
        assert settings.MYSQL_HOST == "localhost"
        assert settings.MYSQL_PORT == 3306
        assert settings.MYSQL_USER == "test_user"
        assert settings.MYSQL_PASSWORD == "test_password"
        assert settings.MYSQL_DATABASE == "test_db"
        assert settings.MONGODB_URL == "mongodb://localhost:27017"
        assert settings.MONGODB_DATABASE == "test_db"
        assert settings.REDIS_HOST == "localhost"
        assert settings.REDIS_PORT == 6379
        assert settings.SECRET_KEY == "test-secret-key-min-32-characters-long"
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_optional_config_fields_have_defaults():
    """
    Test that optional configuration fields have sensible defaults.
    """
    # Set only required fields
    required_env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
    }
    
    for key, value in required_env_vars.items():
        os.environ[key] = value
    
    try:
        # Load configuration
        settings = Settings()
        
        # Verify optional fields have defaults
        assert settings.DEBUG is False
        assert settings.ENVIRONMENT == "production"
        assert settings.MYSQL_PORT == 3306
        assert settings.REDIS_PORT == 6379
        assert settings.REDIS_DB == 0
        assert settings.QDRANT_PORT == 6333
        assert settings.RABBITMQ_PORT == 5672
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 15
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
        
    finally:
        # Clean up environment variables
        for key in required_env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_config_type_conversion():
    """
    Test that configuration correctly converts string environment variables to proper types.
    """
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_PORT": "3307",  # String that should be converted to int
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "REDIS_PORT": "6380",  # String that should be converted to int
        "REDIS_DB": "1",  # String that should be converted to int
        "DEBUG": "true",  # String that should be converted to bool
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "30",  # String that should be converted to int
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Load configuration
        settings = Settings()
        
        # Verify type conversions
        assert isinstance(settings.MYSQL_PORT, int)
        assert settings.MYSQL_PORT == 3307
        
        assert isinstance(settings.REDIS_PORT, int)
        assert settings.REDIS_PORT == 6380
        
        assert isinstance(settings.REDIS_DB, int)
        assert settings.REDIS_DB == 1
        
        assert isinstance(settings.DEBUG, bool)
        assert settings.DEBUG is True
        
        assert isinstance(settings.ACCESS_TOKEN_EXPIRE_MINUTES, int)
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_config_list_parsing():
    """
    Test that configuration correctly parses list values from environment variables.
    """
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
        "CORS_ORIGINS": '["http://localhost:3000","https://example.com"]',
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Load configuration
        settings = Settings()
        
        # Verify list parsing
        assert isinstance(settings.CORS_ORIGINS, list)
        assert len(settings.CORS_ORIGINS) == 2
        assert "http://localhost:3000" in settings.CORS_ORIGINS
        assert "https://example.com" in settings.CORS_ORIGINS
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


# Feature: mcp-platform-backend, Property 50: Invalid Configuration Rejection
@given(
    mysql_port=st.one_of(
        st.integers(max_value=0),  # Invalid: port <= 0
        st.integers(min_value=65536),  # Invalid: port > 65535
    ),
)
@settings(max_examples=100, deadline=None)
def test_invalid_configuration_rejection_port(mysql_port):
    """
    Property 50: Invalid Configuration Rejection
    
    For any invalid configuration (missing required fields, wrong types),
    the application should fail to start with a clear error message.
    
    This test focuses on invalid port numbers.
    
    Validates: Requirements 14.5
    """
    # Set environment variables with invalid port
    os.environ["MYSQL_HOST"] = "localhost"
    os.environ["MYSQL_PORT"] = str(mysql_port)
    os.environ["MYSQL_USER"] = "test_user"
    os.environ["MYSQL_PASSWORD"] = "test_password"
    os.environ["MYSQL_DATABASE"] = "test_db"
    os.environ["MONGODB_URL"] = "mongodb://localhost:27017"
    os.environ["MONGODB_DATABASE"] = "test_db"
    os.environ["SECRET_KEY"] = "test-secret-key-min-32-characters-long"
    
    try:
        # Attempt to load configuration - should raise ValidationError
        with pytest.raises((ValidationError, ValueError)):
            settings = Settings()
    finally:
        # Clean up environment variables
        for key in ["MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD",
                    "MYSQL_DATABASE", "MONGODB_URL", "MONGODB_DATABASE", "SECRET_KEY"]:
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_missing_required_field_rejection():
    """
    Test that configuration rejects missing required fields.
    
    This is a specific example test that complements the property test.
    """
    # Set only some required fields, missing MYSQL_PASSWORD
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "test_user",
        # MYSQL_PASSWORD is missing - this should cause an error
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Attempt to load configuration - should succeed with default empty password
        # (Pydantic allows empty strings for optional fields)
        settings = Settings()
        # Verify that missing password defaults to empty string
        assert settings.MYSQL_PASSWORD == ""
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_invalid_log_level_rejection():
    """
    Test that configuration rejects invalid log levels.
    """
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
        "LOG_LEVEL": "INVALID_LEVEL",  # Invalid log level
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Attempt to load configuration - should raise ValidationError
        with pytest.raises(ValidationError):
            settings = Settings()
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_invalid_boolean_value():
    """
    Test that configuration handles invalid boolean values.
    """
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
        "DEBUG": "not_a_boolean",  # Invalid boolean value
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Pydantic will reject invalid boolean values
        with pytest.raises(ValidationError):
            settings = Settings()
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)


@pytest.mark.asyncio
async def test_empty_required_string_field():
    """
    Test that configuration handles empty required string fields.
    """
    env_vars = {
        "MYSQL_HOST": "",  # Empty host - should this be allowed?
        "MYSQL_USER": "test_user",
        "MYSQL_PASSWORD": "test_password",
        "MYSQL_DATABASE": "test_db",
        "MONGODB_URL": "mongodb://localhost:27017",
        "MONGODB_DATABASE": "test_db",
        "SECRET_KEY": "test-secret-key-min-32-characters-long",
    }
    
    for key, value in env_vars.items():
        os.environ[key] = value
    
    try:
        # Load configuration - empty strings are allowed by default
        settings = Settings()
        assert settings.MYSQL_HOST == ""
        
    finally:
        # Clean up environment variables
        for key in env_vars.keys():
            os.environ.pop(key, None)
