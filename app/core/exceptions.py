"""Custom exceptions for the MCP Platform Backend"""

from typing import List, Optional, Dict, Any
from datetime import datetime


class RoleValidationError(ValueError):
    """
    Raised when role validation fails.
    
    This exception is raised when:
    - Invalid role values are provided during user registration/update
    - Role normalization fails due to unrecognized role names
    - Role validation encounters unexpected data types
    
    **Requirements: 2.4, 2.5**
    """
    
    def __init__(
        self,
        invalid_role: str,
        valid_roles: List[str],
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize RoleValidationError.
        
        Args:
            invalid_role: The invalid role value that was provided
            valid_roles: List of valid role options
            context: Additional context about where the error occurred
            details: Additional error details for debugging
        """
        self.invalid_role = invalid_role
        self.valid_roles = valid_roles
        self.context = context
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
        # Create user-friendly error message
        message = f"Invalid role: '{invalid_role}'. Valid options: {valid_roles}"
        if context:
            message = f"{context}: {message}"
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": "role_validation_error",
            "message": str(self),
            "invalid_role": self.invalid_role,
            "valid_roles": self.valid_roles,
            "context": self.context,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_api_response(self) -> Dict[str, Any]:
        """
        Get API-friendly error response.
        
        Returns:
            Dictionary suitable for HTTP error responses
        """
        return {
            "detail": str(self),
            "type": "role_validation_error",
            "field": "role",
            "invalid_value": self.invalid_role,
            "valid_options": self.valid_roles
        }


class AuthenticationError(Exception):
    """
    Raised when authentication fails.
    
    This exception is raised when:
    - Invalid credentials are provided
    - JWT token validation fails
    - User account is inactive or not found
    
    **Requirements: 2.4, 2.5**
    """
    
    def __init__(
        self,
        message: str,
        error_code: str = "authentication_failed",
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize AuthenticationError.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            context: Additional context about where the error occurred
            details: Additional error details for debugging
        """
        self.message = message
        self.error_code = error_code
        self.context = context
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": "authentication_error",
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_api_response(self) -> Dict[str, Any]:
        """
        Get API-friendly error response.
        
        Returns:
            Dictionary suitable for HTTP error responses
        """
        return {
            "detail": self.message,
            "type": self.error_code,
            "context": self.context
        }


class TokenValidationError(AuthenticationError):
    """
    Raised when JWT token validation fails.
    
    This exception is raised when:
    - JWT token is malformed or expired
    - Token signature validation fails
    - Token contains invalid claims
    
    **Requirements: 2.4, 2.5**
    """
    
    def __init__(
        self,
        message: str,
        token_type: str = "access_token",
        context: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize TokenValidationError.
        
        Args:
            message: Human-readable error message
            token_type: Type of token that failed validation
            context: Additional context about where the error occurred
            details: Additional error details for debugging
        """
        self.token_type = token_type
        
        super().__init__(
            message=message,
            error_code="token_validation_failed",
            context=context,
            details=details
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging.
        
        Returns:
            Dictionary representation of the error
        """
        result = super().to_dict()
        result["token_type"] = self.token_type
        return result


class BackwardCompatibilityError(Exception):
    """
    Raised when backward compatibility issues are detected.
    
    This exception is used for logging and monitoring backward
    compatibility issues without breaking the authentication flow.
    
    **Requirements: 4.1, 4.2, 4.5**
    """
    
    def __init__(
        self,
        message: str,
        compatibility_issue: str,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize BackwardCompatibilityError.
        
        Args:
            message: Human-readable error message
            compatibility_issue: Type of compatibility issue detected
            user_id: User ID associated with the issue
            details: Additional error details for debugging
        """
        self.compatibility_issue = compatibility_issue
        self.user_id = user_id
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": "backward_compatibility_error",
            "compatibility_issue": self.compatibility_issue,
            "message": str(self),
            "user_id": self.user_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }



class MCPExecutionError(Exception):
    """
    Raised when MCP tool execution fails.
    
    This exception is raised when:
    - MCP tool configuration is invalid
    - Tool execution times out
    - Tool returns an error response
    - Communication with MCP server fails
    """
    
    def __init__(
        self,
        message: str,
        execution_id: Optional[str] = None,
        tool_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize MCPExecutionError.
        
        Args:
            message: Human-readable error message
            execution_id: ID of the failed execution (if available)
            tool_id: ID of the tool that failed
            details: Additional error details for debugging
        """
        self.message = message
        self.execution_id = execution_id
        self.tool_id = tool_id
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        
        super().__init__(message)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error_type": "mcp_execution_error",
            "message": self.message,
            "execution_id": self.execution_id,
            "tool_id": self.tool_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
    
    def get_api_response(self) -> Dict[str, Any]:
        """
        Get API-friendly error response.
        
        Returns:
            Dictionary suitable for HTTP error responses
        """
        return {
            "detail": self.message,
            "type": "mcp_execution_error",
            "execution_id": self.execution_id,
            "tool_id": self.tool_id
        }
