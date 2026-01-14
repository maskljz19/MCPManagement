"""Parameter Validation Service for MCP Tool Execution

This service provides comprehensive parameter validation including:
- Schema-based validation against tool parameter schemas
- Dangerous value detection and sanitization
- Default value application
- Type coercion
- Detailed validation error reporting
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import MCPExecutionError


class ValidationError(BaseModel):
    """Represents a single validation error"""
    field: str = Field(..., description="Field name that failed validation")
    error_type: str = Field(..., description="Type of validation error")
    message: str = Field(..., description="Human-readable error message")
    value: Optional[Any] = Field(None, description="The invalid value")


class ValidationResult(BaseModel):
    """Result of parameter validation"""
    valid: bool = Field(..., description="Whether validation passed")
    errors: List[ValidationError] = Field(
        default_factory=list,
        description="List of validation errors"
    )
    sanitized_params: Dict[str, Any] = Field(
        default_factory=dict,
        description="Sanitized and validated parameters"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Non-fatal warnings"
    )


class ParameterValidator:
    """
    Validates and sanitizes parameters for MCP tool execution.
    
    Implements comprehensive validation including:
    - Schema validation
    - Type coercion
    - Dangerous value detection
    - Default value application
    - SQL injection prevention
    - XSS prevention
    - Command injection prevention
    """
    
    # Dangerous patterns to detect
    SQL_INJECTION_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"('.*--)",
        r"(UNION.*SELECT)",
    ]
    
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$()]",
        r"\$\{.*\}",
        r"\$\(.*\)",
        r"``",
    ]
    
    # Maximum string length to prevent DoS
    MAX_STRING_LENGTH = 10000
    
    # Maximum array/object depth
    MAX_DEPTH = 10
    
    # Maximum number of array elements
    MAX_ARRAY_LENGTH = 1000
    
    def __init__(self):
        """Initialize the parameter validator"""
        pass
    
    async def validate_parameters(
        self,
        parameters: Dict[str, Any],
        schema: Optional[Dict[str, Any]] = None,
        tool_config: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate parameters against schema and security rules.
        
        Args:
            parameters: Parameters to validate
            schema: JSON Schema for parameter validation (optional)
            tool_config: Tool configuration containing defaults (optional)
            
        Returns:
            ValidationResult with validation status and sanitized parameters
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        sanitized_params = {}
        
        # Step 1: Apply defaults from tool config
        if tool_config and "defaults" in tool_config:
            sanitized_params = dict(tool_config["defaults"])
        
        # Step 2: Merge provided parameters
        sanitized_params.update(parameters)
        
        # Step 3: Validate size limits (before sanitization truncates)
        size_errors = await self._validate_size_limits(sanitized_params)
        errors.extend(size_errors)
        
        # Step 4: Type coercion (before validation)
        coerced_params, coercion_errors = await self._coerce_types(
            sanitized_params,
            schema
        )
        sanitized_params = coerced_params
        errors.extend(coercion_errors)
        
        # Step 5: Validate against schema if provided
        if schema:
            schema_errors = await self._validate_against_schema(
                sanitized_params,
                schema
            )
            errors.extend(schema_errors)
        
        # Step 6: Security validation
        security_errors, security_warnings = await self._validate_security(
            sanitized_params
        )
        errors.extend(security_errors)
        warnings.extend(security_warnings)
        
        # Step 7: Sanitize dangerous values
        sanitized_params = await self._sanitize_parameters(sanitized_params)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            sanitized_params=sanitized_params if len(errors) == 0 else {},
            warnings=warnings
        )
    
    async def _validate_against_schema(
        self,
        parameters: Dict[str, Any],
        schema: Dict[str, Any]
    ) -> List[ValidationError]:
        """
        Validate parameters against JSON Schema.
        
        Args:
            parameters: Parameters to validate
            schema: JSON Schema definition
            
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        
        # Get schema properties
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        
        # Check required fields
        for field_name in required:
            if field_name not in parameters:
                errors.append(ValidationError(
                    field=field_name,
                    error_type="required",
                    message=f"Required field '{field_name}' is missing",
                    value=None
                ))
        
        # Validate each parameter
        for field_name, value in parameters.items():
            if field_name in properties:
                field_schema = properties[field_name]
                field_errors = await self._validate_field(
                    field_name,
                    value,
                    field_schema
                )
                errors.extend(field_errors)
            else:
                # Unknown field - add warning but don't fail
                # Some tools may accept additional properties
                pass
        
        return errors
    
    async def _validate_field(
        self,
        field_name: str,
        value: Any,
        field_schema: Dict[str, Any]
    ) -> List[ValidationError]:
        """
        Validate a single field against its schema.
        
        Args:
            field_name: Name of the field
            value: Value to validate
            field_schema: Schema for this field
            
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        expected_type = field_schema.get("type")
        
        # Type validation
        if expected_type:
            if not self._check_type(value, expected_type):
                errors.append(ValidationError(
                    field=field_name,
                    error_type="type",
                    message=f"Field '{field_name}' must be of type '{expected_type}', got '{type(value).__name__}'",
                    value=value
                ))
                return errors  # Don't continue if type is wrong
        
        # String validations
        if expected_type == "string" and isinstance(value, str):
            # Min length
            if "minLength" in field_schema:
                min_length = field_schema["minLength"]
                if len(value) < min_length:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="minLength",
                        message=f"Field '{field_name}' must be at least {min_length} characters",
                        value=value
                    ))
            
            # Max length
            if "maxLength" in field_schema:
                max_length = field_schema["maxLength"]
                if len(value) > max_length:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="maxLength",
                        message=f"Field '{field_name}' must be at most {max_length} characters",
                        value=value
                    ))
            
            # Pattern
            if "pattern" in field_schema:
                pattern = field_schema["pattern"]
                if not re.match(pattern, value):
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="pattern",
                        message=f"Field '{field_name}' does not match required pattern",
                        value=value
                    ))
            
            # Enum
            if "enum" in field_schema:
                allowed_values = field_schema["enum"]
                if value not in allowed_values:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="enum",
                        message=f"Field '{field_name}' must be one of: {', '.join(map(str, allowed_values))}",
                        value=value
                    ))
        
        # Number validations
        if expected_type in ["number", "integer"] and isinstance(value, (int, float)):
            # Minimum
            if "minimum" in field_schema:
                minimum = field_schema["minimum"]
                if value < minimum:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="minimum",
                        message=f"Field '{field_name}' must be at least {minimum}",
                        value=value
                    ))
            
            # Maximum
            if "maximum" in field_schema:
                maximum = field_schema["maximum"]
                if value > maximum:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="maximum",
                        message=f"Field '{field_name}' must be at most {maximum}",
                        value=value
                    ))
        
        # Array validations
        if expected_type == "array" and isinstance(value, list):
            # Min items
            if "minItems" in field_schema:
                min_items = field_schema["minItems"]
                if len(value) < min_items:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="minItems",
                        message=f"Field '{field_name}' must have at least {min_items} items",
                        value=value
                    ))
            
            # Max items
            if "maxItems" in field_schema:
                max_items = field_schema["maxItems"]
                if len(value) > max_items:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="maxItems",
                        message=f"Field '{field_name}' must have at most {max_items} items",
                        value=value
                    ))
            
            # Validate items
            if "items" in field_schema:
                item_schema = field_schema["items"]
                for i, item in enumerate(value):
                    item_errors = await self._validate_field(
                        f"{field_name}[{i}]",
                        item,
                        item_schema
                    )
                    errors.extend(item_errors)
        
        # Object validations
        if expected_type == "object" and isinstance(value, dict):
            if "properties" in field_schema:
                for prop_name, prop_value in value.items():
                    if prop_name in field_schema["properties"]:
                        prop_schema = field_schema["properties"][prop_name]
                        prop_errors = await self._validate_field(
                            f"{field_name}.{prop_name}",
                            prop_value,
                            prop_schema
                        )
                        errors.extend(prop_errors)
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """
        Check if value matches expected JSON Schema type.
        
        Args:
            value: Value to check
            expected_type: Expected JSON Schema type
            
        Returns:
            True if type matches, False otherwise
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
            "null": type(None)
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, allow it
        
        expected_python_type = type_map[expected_type]
        return isinstance(value, expected_python_type)
    
    async def _coerce_types(
        self,
        parameters: Dict[str, Any],
        schema: Optional[Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], List[ValidationError]]:
        """
        Attempt to coerce parameter types to match schema.
        
        Args:
            parameters: Parameters to coerce
            schema: JSON Schema (optional)
            
        Returns:
            Tuple of (coerced parameters, errors)
        """
        if not schema or "properties" not in schema:
            return parameters, []
        
        coerced = {}
        errors: List[ValidationError] = []
        
        for field_name, value in parameters.items():
            if field_name not in schema["properties"]:
                coerced[field_name] = value
                continue
            
            field_schema = schema["properties"][field_name]
            expected_type = field_schema.get("type")
            
            if not expected_type:
                coerced[field_name] = value
                continue
            
            # Try to coerce
            try:
                coerced_value = self._coerce_value(value, expected_type)
                coerced[field_name] = coerced_value
            except (ValueError, TypeError) as e:
                errors.append(ValidationError(
                    field=field_name,
                    error_type="coercion",
                    message=f"Cannot coerce '{field_name}' to type '{expected_type}': {str(e)}",
                    value=value
                ))
                coerced[field_name] = value  # Keep original value
        
        return coerced, errors
    
    def _coerce_value(self, value: Any, expected_type: str) -> Any:
        """
        Coerce a value to the expected type.
        
        Args:
            value: Value to coerce
            expected_type: Target type
            
        Returns:
            Coerced value
            
        Raises:
            ValueError: If coercion fails
        """
        # Already correct type
        if self._check_type(value, expected_type):
            return value
        
        # String coercions
        if expected_type == "string":
            return str(value)
        
        # Number coercions
        if expected_type == "number":
            if isinstance(value, str):
                return float(value)
            return float(value)
        
        # Integer coercions
        if expected_type == "integer":
            if isinstance(value, str):
                return int(value)
            if isinstance(value, float):
                if value.is_integer():
                    return int(value)
                raise ValueError(f"Cannot coerce {value} to integer without loss")
            return int(value)
        
        # Boolean coercions
        if expected_type == "boolean":
            if isinstance(value, str):
                lower = value.lower()
                if lower in ("true", "1", "yes", "on"):
                    return True
                if lower in ("false", "0", "no", "off"):
                    return False
                raise ValueError(f"Cannot coerce string '{value}' to boolean")
            return bool(value)
        
        # Array coercions
        if expected_type == "array":
            if not isinstance(value, list):
                return [value]  # Wrap single value in array
            return value
        
        # No coercion possible
        raise ValueError(f"Cannot coerce {type(value).__name__} to {expected_type}")
    
    async def _validate_security(
        self,
        parameters: Dict[str, Any]
    ) -> Tuple[List[ValidationError], List[str]]:
        """
        Validate parameters for security issues.
        
        Args:
            parameters: Parameters to validate
            
        Returns:
            Tuple of (errors, warnings)
        """
        errors: List[ValidationError] = []
        warnings: List[str] = []
        
        for field_name, value in parameters.items():
            if isinstance(value, str):
                # Check for SQL injection
                for pattern in self.SQL_INJECTION_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(ValidationError(
                            field=field_name,
                            error_type="sql_injection",
                            message=f"Field '{field_name}' contains potentially dangerous SQL patterns",
                            value=value
                        ))
                        break
                
                # Check for XSS
                for pattern in self.XSS_PATTERNS:
                    if re.search(pattern, value, re.IGNORECASE):
                        errors.append(ValidationError(
                            field=field_name,
                            error_type="xss",
                            message=f"Field '{field_name}' contains potentially dangerous XSS patterns",
                            value=value
                        ))
                        break
                
                # Check for command injection
                for pattern in self.COMMAND_INJECTION_PATTERNS:
                    if re.search(pattern, value):
                        warnings.append(
                            f"Field '{field_name}' contains shell metacharacters that may be dangerous"
                        )
                        break
            
            elif isinstance(value, dict):
                # Recursively check nested objects
                nested_errors, nested_warnings = await self._validate_security(value)
                errors.extend(nested_errors)
                warnings.extend(nested_warnings)
            
            elif isinstance(value, list):
                # Check array elements
                for i, item in enumerate(value):
                    if isinstance(item, (dict, str)):
                        item_errors, item_warnings = await self._validate_security(
                            {f"{field_name}[{i}]": item}
                        )
                        errors.extend(item_errors)
                        warnings.extend(item_warnings)
        
        return errors, warnings
    
    async def _sanitize_parameters(
        self,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Sanitize parameters by removing/escaping dangerous content.
        
        Args:
            parameters: Parameters to sanitize
            
        Returns:
            Sanitized parameters
        """
        sanitized = {}
        
        for field_name, value in parameters.items():
            if isinstance(value, str):
                # Trim whitespace
                sanitized_value = value.strip()
                
                # Remove null bytes
                sanitized_value = sanitized_value.replace('\x00', '')
                
                # Limit length
                if len(sanitized_value) > self.MAX_STRING_LENGTH:
                    sanitized_value = sanitized_value[:self.MAX_STRING_LENGTH]
                
                sanitized[field_name] = sanitized_value
            
            elif isinstance(value, dict):
                # Recursively sanitize nested objects
                sanitized[field_name] = await self._sanitize_parameters(value)
            
            elif isinstance(value, list):
                # Sanitize array elements
                sanitized_list = []
                for item in value[:self.MAX_ARRAY_LENGTH]:  # Limit array size
                    if isinstance(item, str):
                        sanitized_item = item.strip().replace('\x00', '')
                        if len(sanitized_item) > self.MAX_STRING_LENGTH:
                            sanitized_item = sanitized_item[:self.MAX_STRING_LENGTH]
                        sanitized_list.append(sanitized_item)
                    elif isinstance(item, dict):
                        sanitized_list.append(await self._sanitize_parameters(item))
                    else:
                        sanitized_list.append(item)
                sanitized[field_name] = sanitized_list
            
            else:
                # Keep other types as-is
                sanitized[field_name] = value
        
        return sanitized
    
    async def _validate_size_limits(
        self,
        parameters: Dict[str, Any],
        depth: int = 0
    ) -> List[ValidationError]:
        """
        Validate size limits to prevent DoS attacks.
        
        Args:
            parameters: Parameters to validate
            depth: Current nesting depth
            
        Returns:
            List of validation errors
        """
        errors: List[ValidationError] = []
        
        # Check depth
        if depth > self.MAX_DEPTH:
            errors.append(ValidationError(
                field="<root>",
                error_type="max_depth",
                message=f"Parameter nesting depth exceeds maximum of {self.MAX_DEPTH}",
                value=None
            ))
            return errors
        
        for field_name, value in parameters.items():
            # Check string length (before sanitization truncates it)
            if isinstance(value, str):
                original_length = len(value)
                if original_length > self.MAX_STRING_LENGTH:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="max_length",
                        message=f"Field '{field_name}' exceeds maximum length of {self.MAX_STRING_LENGTH} (got {original_length})",
                        value=f"{value[:100]}..."
                    ))
            
            # Check array length (before sanitization truncates it)
            elif isinstance(value, list):
                original_length = len(value)
                if original_length > self.MAX_ARRAY_LENGTH:
                    errors.append(ValidationError(
                        field=field_name,
                        error_type="max_items",
                        message=f"Field '{field_name}' exceeds maximum array length of {self.MAX_ARRAY_LENGTH} (got {original_length})",
                        value=None
                    ))
            
            # Recursively check nested objects
            elif isinstance(value, dict):
                nested_errors = await self._validate_size_limits(value, depth + 1)
                errors.extend(nested_errors)
        
        return errors
