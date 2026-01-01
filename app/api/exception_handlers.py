"""Custom exception handlers for FastAPI application"""

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from typing import Union
import traceback

from app.core.exceptions import (
    RoleValidationError,
    AuthenticationError,
    TokenValidationError,
    BackwardCompatibilityError
)
from app.core.logging_config import get_logger


logger = get_logger(__name__)


async def role_validation_exception_handler(
    request: Request,
    exc: RoleValidationError
) -> JSONResponse:
    """
    Handle RoleValidationError exceptions.
    
    Provides user-friendly error responses for role validation failures.
    
    **Requirements: 2.4, 2.5**
    """
    # Log the error with context
    logger.error(
        "role_validation_error_handled",
        request_path=request.url.path,
        request_method=request.method,
        invalid_role=exc.invalid_role,
        valid_roles=exc.valid_roles,
        context=exc.context,
        error_details=exc.details,
        exc_info=True
    )
    
    # Return user-friendly error response
    return JSONResponse(
        status_code=400,
        content={
            "detail": str(exc),
            "type": "role_validation_error",
            "field": "role",
            "invalid_value": exc.invalid_role,
            "valid_options": exc.valid_roles,
            "timestamp": exc.timestamp.isoformat()
        }
    )


async def authentication_exception_handler(
    request: Request,
    exc: AuthenticationError
) -> JSONResponse:
    """
    Handle AuthenticationError exceptions.
    
    Provides secure error responses for authentication failures.
    
    **Requirements: 2.4, 2.5**
    """
    # Log the error with context
    logger.error(
        "authentication_error_handled",
        request_path=request.url.path,
        request_method=request.method,
        error_code=exc.error_code,
        context=exc.context,
        error_details=exc.details,
        exc_info=True
    )
    
    # Return secure error response (don't expose sensitive details)
    return JSONResponse(
        status_code=401,
        content={
            "detail": exc.message,
            "type": exc.error_code,
            "timestamp": exc.timestamp.isoformat()
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def token_validation_exception_handler(
    request: Request,
    exc: TokenValidationError
) -> JSONResponse:
    """
    Handle TokenValidationError exceptions.
    
    Provides secure error responses for token validation failures.
    
    **Requirements: 2.4, 2.5**
    """
    # Log the error with context
    logger.error(
        "token_validation_error_handled",
        request_path=request.url.path,
        request_method=request.method,
        token_type=exc.token_type,
        error_code=exc.error_code,
        context=exc.context,
        error_details=exc.details,
        exc_info=True
    )
    
    # Return secure error response
    return JSONResponse(
        status_code=401,
        content={
            "detail": exc.message,
            "type": exc.error_code,
            "token_type": exc.token_type,
            "timestamp": exc.timestamp.isoformat()
        },
        headers={"WWW-Authenticate": "Bearer"}
    )


async def backward_compatibility_exception_handler(
    request: Request,
    exc: BackwardCompatibilityError
) -> JSONResponse:
    """
    Handle BackwardCompatibilityError exceptions.
    
    These are typically logged for monitoring but don't fail the request.
    This handler is for cases where they do need to be surfaced.
    
    **Requirements: 4.1, 4.2, 4.5**
    """
    # Log the compatibility issue
    logger.warning(
        "backward_compatibility_error_handled",
        request_path=request.url.path,
        request_method=request.method,
        compatibility_issue=exc.compatibility_issue,
        user_id=exc.user_id,
        error_details=exc.details,
        exc_info=True
    )
    
    # Return informational response
    return JSONResponse(
        status_code=200,  # Don't fail the request
        content={
            "message": "Request processed with compatibility adjustments",
            "compatibility_issue": exc.compatibility_issue,
            "timestamp": exc.timestamp.isoformat()
        }
    )


async def validation_exception_handler(
    request: Request,
    exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors with enhanced role validation messages.
    
    Provides detailed error information for validation failures,
    with special handling for role validation errors.
    
    **Requirements: 5.3**
    """
    # Extract error details
    errors = []
    
    if isinstance(exc, RequestValidationError):
        for error in exc.errors():
            error_detail = {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            }
            
            # Check if this is a role validation error
            if "role" in error_detail["field"] and "Invalid role" in error_detail["message"]:
                # Extract valid roles from the message if possible
                message = error_detail["message"]
                if "Valid options:" in message:
                    try:
                        valid_part = message.split("Valid options:")[1].strip()
                        # Parse the list from string representation
                        import ast
                        valid_roles = ast.literal_eval(valid_part)
                        error_detail["valid_options"] = valid_roles
                    except:
                        pass  # If parsing fails, just use the original message
            
            errors.append(error_detail)
    
    elif isinstance(exc, ValidationError):
        for error in exc.errors():
            errors.append({
                "field": ".".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"]
            })
    
    # Log the validation error
    logger.warning(
        "validation_error_handled",
        request_path=request.url.path,
        request_method=request.method,
        errors=errors,
        exc_info=True
    )
    
    # Return detailed validation error response
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "type": "validation_error",
            "errors": errors
        }
    )


async def http_exception_handler(
    request: Request,
    exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """
    Handle HTTP exceptions with enhanced logging.
    
    Provides consistent error response format for HTTP exceptions.
    """
    # Log the HTTP exception
    logger.warning(
        "http_exception_handled",
        request_path=request.url.path,
        request_method=request.method,
        status_code=exc.status_code,
        detail=str(exc.detail),
        exc_info=True
    )
    
    # Return standard HTTP error response
    content = {"detail": exc.detail}
    
    # Add additional context for specific status codes
    if exc.status_code == 401:
        content["type"] = "authentication_required"
    elif exc.status_code == 403:
        content["type"] = "permission_denied"
    elif exc.status_code == 404:
        content["type"] = "not_found"
    elif exc.status_code == 429:
        content["type"] = "rate_limit_exceeded"
    
    headers = getattr(exc, "headers", None)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=headers
    )


async def general_exception_handler(
    request: Request,
    exc: Exception
) -> JSONResponse:
    """
    Handle unexpected exceptions with secure error responses.
    
    Logs detailed error information but returns generic error messages
    to avoid exposing sensitive information.
    """
    # Log the unexpected error with full traceback
    logger.error(
        "unexpected_exception_handled",
        request_path=request.url.path,
        request_method=request.method,
        error_type=type(exc).__name__,
        error_message=str(exc),
        traceback=traceback.format_exc(),
        exc_info=True
    )
    
    # Return generic error response for security
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": "internal_server_error"
        }
    )


def register_exception_handlers(app):
    """
    Register all custom exception handlers with the FastAPI application.
    
    Args:
        app: FastAPI application instance
    """
    # Register custom exception handlers
    app.add_exception_handler(RoleValidationError, role_validation_exception_handler)
    app.add_exception_handler(AuthenticationError, authentication_exception_handler)
    app.add_exception_handler(TokenValidationError, token_validation_exception_handler)
    app.add_exception_handler(BackwardCompatibilityError, backward_compatibility_exception_handler)
    
    # Register enhanced validation error handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Register enhanced HTTP exception handler
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # Register general exception handler as fallback
    app.add_exception_handler(Exception, general_exception_handler)
    
    logger.info(
        "exception_handlers_registered",
        handlers=[
            "RoleValidationError",
            "AuthenticationError", 
            "TokenValidationError",
            "BackwardCompatibilityError",
            "RequestValidationError",
            "ValidationError",
            "HTTPException",
            "StarletteHTTPException",
            "Exception"
        ]
    )