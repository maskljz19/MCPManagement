"""Structured Logging Configuration with structlog"""

import logging
import sys
from typing import Any, Dict
import structlog
from structlog.types import EventDict, Processor
from app.core.config import settings


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Add application context to all log entries.
    
    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary
    
    Returns:
        Modified event dictionary with app context
    """
    event_dict["app"] = "mcp_platform"
    event_dict["version"] = "1.0.0"
    event_dict["environment"] = settings.ENVIRONMENT
    return event_dict


def censor_sensitive_data(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """
    Censor sensitive data in log entries.
    
    Redacts passwords, tokens, API keys, and other sensitive information.
    
    Args:
        logger: Logger instance
        method_name: Method name being called
        event_dict: Event dictionary
    
    Returns:
        Modified event dictionary with censored data
    
    **Requirements: 11.4**
    """
    sensitive_keys = {
        'password', 'token', 'api_key', 'secret', 'authorization',
        'access_token', 'refresh_token', 'jwt', 'bearer',
        'mysql_password', 'redis_password', 'rabbitmq_password',
        'openai_api_key', 'github_token', 'github_client_secret'
    }
    
    def censor_dict(d: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively censor sensitive keys in dictionary"""
        censored = {}
        for key, value in d.items():
            key_lower = key.lower()
            # Check if key contains any sensitive keyword
            if any(sensitive in key_lower for sensitive in sensitive_keys):
                censored[key] = "***REDACTED***"
            elif isinstance(value, dict):
                censored[key] = censor_dict(value)
            elif isinstance(value, list):
                censored[key] = [
                    censor_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                censored[key] = value
        return censored
    
    # Censor the event dict
    return censor_dict(event_dict)


def configure_structlog() -> None:
    """
    Configure structlog for structured logging.
    
    Sets up processors, formatters, and output configuration.
    
    **Requirements: 12.2**
    """
    # Determine log level from settings
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )
    
    # Define processors
    processors: list[Processor] = [
        # Add log level
        structlog.stdlib.add_log_level,
        # Add logger name
        structlog.stdlib.add_logger_name,
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        # Add application context
        add_app_context,
        # Censor sensitive data
        censor_sensitive_data,
        # Add stack info for exceptions
        structlog.processors.StackInfoRenderer(),
        # Format exceptions
        structlog.processors.format_exc_info,
        # Decode unicode
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Add appropriate renderer based on environment
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        # Use console renderer for development (human-readable)
        processors.append(structlog.dev.ConsoleRenderer())
    else:
        # Use JSON renderer for production (machine-readable)
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.stdlib.BoundLogger:
    """
    Get a structured logger instance.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured structlog logger
    
    Usage:
        logger = get_logger(__name__)
        logger.info("user_created", user_id=user.id, username=user.username)
    """
    return structlog.get_logger(name)


# Configure structlog on module import
configure_structlog()


# Export commonly used items
__all__ = [
    'configure_structlog',
    'get_logger',
]
