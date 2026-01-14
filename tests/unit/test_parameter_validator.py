"""Unit tests for Parameter Validator"""

import pytest
from app.services.parameter_validator import ParameterValidator, ValidationResult


@pytest.fixture
def validator():
    """Create a parameter validator instance"""
    return ParameterValidator()


class TestSchemaValidation:
    """Test schema-based validation"""
    
    @pytest.mark.asyncio
    async def test_required_field_missing(self, validator):
        """Test that missing required fields are detected"""
        schema = {
            "properties": {
                "name": {"type": "string"}
            },
            "required": ["name"]
        }
        
        result = await validator.validate_parameters(
            parameters={},
            schema=schema
        )
        
        assert not result.valid
        assert len(result.errors) == 1
        assert result.errors[0].field == "name"
        assert result.errors[0].error_type == "required"
    
    @pytest.mark.asyncio
    async def test_type_validation(self, validator):
        """Test that type mismatches are detected"""
        schema = {
            "properties": {
                "age": {"type": "integer"}
            }
        }
        
        result = await validator.validate_parameters(
            parameters={"age": "not a number"},
            schema=schema
        )
        
        assert not result.valid
        # Should have both coercion error and type error
        assert len(result.errors) >= 1
        assert any(e.field == "age" for e in result.errors)
    
    @pytest.mark.asyncio
    async def test_string_length_validation(self, validator):
        """Test string length constraints"""
        schema = {
            "properties": {
                "username": {
                    "type": "string",
                    "minLength": 3,
                    "maxLength": 20
                }
            }
        }
        
        # Too short
        result = await validator.validate_parameters(
            parameters={"username": "ab"},
            schema=schema
        )
        assert not result.valid
        assert any(e.error_type == "minLength" for e in result.errors)
        
        # Too long
        result = await validator.validate_parameters(
            parameters={"username": "a" * 25},
            schema=schema
        )
        assert not result.valid
        assert any(e.error_type == "maxLength" for e in result.errors)
        
        # Valid
        result = await validator.validate_parameters(
            parameters={"username": "validuser"},
            schema=schema
        )
        assert result.valid
    
    @pytest.mark.asyncio
    async def test_number_range_validation(self, validator):
        """Test number range constraints"""
        schema = {
            "properties": {
                "score": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 100
                }
            }
        }
        
        # Below minimum
        result = await validator.validate_parameters(
            parameters={"score": -5},
            schema=schema
        )
        assert not result.valid
        assert any(e.error_type == "minimum" for e in result.errors)
        
        # Above maximum
        result = await validator.validate_parameters(
            parameters={"score": 150},
            schema=schema
        )
        assert not result.valid
        assert any(e.error_type == "maximum" for e in result.errors)
        
        # Valid
        result = await validator.validate_parameters(
            parameters={"score": 75},
            schema=schema
        )
        assert result.valid
    
    @pytest.mark.asyncio
    async def test_enum_validation(self, validator):
        """Test enum value validation"""
        schema = {
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["active", "inactive", "pending"]
                }
            }
        }
        
        # Invalid value
        result = await validator.validate_parameters(
            parameters={"status": "unknown"},
            schema=schema
        )
        assert not result.valid
        assert any(e.error_type == "enum" for e in result.errors)
        
        # Valid value
        result = await validator.validate_parameters(
            parameters={"status": "active"},
            schema=schema
        )
        assert result.valid


class TestTypeCoercion:
    """Test type coercion"""
    
    @pytest.mark.asyncio
    async def test_string_to_number_coercion(self, validator):
        """Test coercing string to number"""
        schema = {
            "properties": {
                "count": {"type": "integer"}
            }
        }
        
        result = await validator.validate_parameters(
            parameters={"count": "42"},
            schema=schema
        )
        
        assert result.valid
        assert result.sanitized_params["count"] == 42
    
    @pytest.mark.asyncio
    async def test_string_to_boolean_coercion(self, validator):
        """Test coercing string to boolean"""
        schema = {
            "properties": {
                "enabled": {"type": "boolean"}
            }
        }
        
        # Test "true"
        result = await validator.validate_parameters(
            parameters={"enabled": "true"},
            schema=schema
        )
        assert result.valid
        assert result.sanitized_params["enabled"] is True
        
        # Test "false"
        result = await validator.validate_parameters(
            parameters={"enabled": "false"},
            schema=schema
        )
        assert result.valid
        assert result.sanitized_params["enabled"] is False
    
    @pytest.mark.asyncio
    async def test_failed_coercion(self, validator):
        """Test that invalid coercion fails gracefully"""
        schema = {
            "properties": {
                "count": {"type": "integer"}
            }
        }
        
        result = await validator.validate_parameters(
            parameters={"count": "not_a_number"},
            schema=schema
        )
        
        assert not result.valid
        assert any(e.error_type == "coercion" for e in result.errors)


class TestSecurityValidation:
    """Test security validation"""
    
    @pytest.mark.asyncio
    async def test_sql_injection_detection(self, validator):
        """Test SQL injection pattern detection"""
        result = await validator.validate_parameters(
            parameters={"query": "SELECT * FROM users WHERE id = 1"},
            schema=None
        )
        
        assert not result.valid
        assert any(e.error_type == "sql_injection" for e in result.errors)
    
    @pytest.mark.asyncio
    async def test_xss_detection(self, validator):
        """Test XSS pattern detection"""
        result = await validator.validate_parameters(
            parameters={"content": "<script>alert('xss')</script>"},
            schema=None
        )
        
        assert not result.valid
        assert any(e.error_type == "xss" for e in result.errors)
    
    @pytest.mark.asyncio
    async def test_command_injection_warning(self, validator):
        """Test command injection warning"""
        result = await validator.validate_parameters(
            parameters={"command": "ls; rm -rf /"},
            schema=None
        )
        
        # Should have warnings but might still be valid
        assert len(result.warnings) > 0


class TestDefaultValues:
    """Test default value application"""
    
    @pytest.mark.asyncio
    async def test_apply_defaults(self, validator):
        """Test that defaults are applied"""
        tool_config = {
            "defaults": {
                "timeout": 30,
                "retries": 3
            }
        }
        
        result = await validator.validate_parameters(
            parameters={"custom": "value"},
            schema=None,
            tool_config=tool_config
        )
        
        assert result.valid
        assert result.sanitized_params["timeout"] == 30
        assert result.sanitized_params["retries"] == 3
        assert result.sanitized_params["custom"] == "value"
    
    @pytest.mark.asyncio
    async def test_override_defaults(self, validator):
        """Test that provided values override defaults"""
        tool_config = {
            "defaults": {
                "timeout": 30
            }
        }
        
        result = await validator.validate_parameters(
            parameters={"timeout": 60},
            schema=None,
            tool_config=tool_config
        )
        
        assert result.valid
        assert result.sanitized_params["timeout"] == 60


class TestSanitization:
    """Test parameter sanitization"""
    
    @pytest.mark.asyncio
    async def test_trim_whitespace(self, validator):
        """Test that whitespace is trimmed"""
        result = await validator.validate_parameters(
            parameters={"name": "  John Doe  "},
            schema=None
        )
        
        assert result.valid
        assert result.sanitized_params["name"] == "John Doe"
    
    @pytest.mark.asyncio
    async def test_remove_null_bytes(self, validator):
        """Test that null bytes are removed"""
        result = await validator.validate_parameters(
            parameters={"data": "test\x00data"},
            schema=None
        )
        
        assert result.valid
        assert "\x00" not in result.sanitized_params["data"]
    
    @pytest.mark.asyncio
    async def test_limit_string_length(self, validator):
        """Test that overly long strings are truncated"""
        long_string = "a" * 20000
        
        result = await validator.validate_parameters(
            parameters={"data": long_string},
            schema=None
        )
        
        # Should have size limit error
        assert not result.valid
        assert any(e.error_type == "max_length" for e in result.errors)


class TestSizeLimits:
    """Test size limit validation"""
    
    @pytest.mark.asyncio
    async def test_array_length_limit(self, validator):
        """Test array length limits"""
        large_array = list(range(2000))
        
        result = await validator.validate_parameters(
            parameters={"items": large_array},
            schema=None
        )
        
        assert not result.valid
        assert any(e.error_type == "max_items" for e in result.errors)
    
    @pytest.mark.asyncio
    async def test_nesting_depth_limit(self, validator):
        """Test nesting depth limits"""
        # Create deeply nested structure
        nested = {"level": 1}
        current = nested
        for i in range(15):
            current["nested"] = {"level": i + 2}
            current = current["nested"]
        
        result = await validator.validate_parameters(
            parameters=nested,
            schema=None
        )
        
        assert not result.valid
        assert any(e.error_type == "max_depth" for e in result.errors)


class TestComplexValidation:
    """Test complex validation scenarios"""
    
    @pytest.mark.asyncio
    async def test_nested_object_validation(self, validator):
        """Test validation of nested objects"""
        schema = {
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"}
                    }
                }
            }
        }
        
        result = await validator.validate_parameters(
            parameters={
                "user": {
                    "name": "John",
                    "age": 30
                }
            },
            schema=schema
        )
        
        assert result.valid
    
    @pytest.mark.asyncio
    async def test_array_item_validation(self, validator):
        """Test validation of array items"""
        schema = {
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100
                    }
                }
            }
        }
        
        # Valid array
        result = await validator.validate_parameters(
            parameters={"scores": [85, 90, 75]},
            schema=schema
        )
        assert result.valid
        
        # Invalid item
        result = await validator.validate_parameters(
            parameters={"scores": [85, 150, 75]},
            schema=schema
        )
        assert not result.valid
