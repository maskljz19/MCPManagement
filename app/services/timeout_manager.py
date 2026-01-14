"""Timeout Manager Service - Handles execution timeout configuration and enforcement"""

import asyncio
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from app.core.exceptions import MCPExecutionError


logger = logging.getLogger(__name__)


class TimeoutConfig:
    """Configuration for timeout management"""
    
    # System-wide timeout limits
    MIN_TIMEOUT_SECONDS = 1
    MAX_TIMEOUT_SECONDS = 3600  # 1 hour
    DEFAULT_TIMEOUT_SECONDS = 30
    
    # Timeout ranges by user tier (can be extended)
    TIER_TIMEOUT_LIMITS = {
        "viewer": {"min": 1, "max": 300},      # 5 minutes max
        "developer": {"min": 1, "max": 1800},  # 30 minutes max
        "admin": {"min": 1, "max": 3600}       # 1 hour max
    }


class TimeoutManager:
    """
    Manages execution timeouts including configuration, validation, and enforcement.
    
    Responsibilities:
    - Validate timeout values against allowed ranges
    - Get timeout from tool config or use defaults
    - Track timeout events for monitoring
    - Provide timeout context for logging
    """
    
    def __init__(self):
        self.timeout_events: Dict[str, Dict[str, Any]] = {}
    
    def get_timeout_for_execution(
        self,
        tool_config: Optional[Dict[str, Any]] = None,
        user_timeout: Optional[int] = None,
        user_tier: str = "viewer"
    ) -> int:
        """
        Determine the timeout value for an execution.
        
        Priority order:
        1. User-specified timeout (if valid)
        2. Tool configuration timeout
        3. System default timeout
        
        Args:
            tool_config: Tool configuration that may contain timeout setting
            user_timeout: User-specified timeout in seconds
            user_tier: User tier for determining timeout limits
            
        Returns:
            Timeout value in seconds
            
        Raises:
            MCPExecutionError: If timeout value is invalid
        """
        # Get tier limits
        tier_limits = TimeoutConfig.TIER_TIMEOUT_LIMITS.get(
            user_tier,
            TimeoutConfig.TIER_TIMEOUT_LIMITS["viewer"]
        )
        
        # If user specified a timeout, validate and use it
        if user_timeout is not None:
            validated_timeout = self.validate_timeout(
                user_timeout,
                min_timeout=tier_limits["min"],
                max_timeout=tier_limits["max"]
            )
            return validated_timeout
        
        # Check tool configuration for timeout
        if tool_config and "timeout" in tool_config:
            tool_timeout = tool_config["timeout"]
            if isinstance(tool_timeout, (int, float)):
                tool_timeout = int(tool_timeout)
                # Validate tool timeout against tier limits
                try:
                    validated_timeout = self.validate_timeout(
                        tool_timeout,
                        min_timeout=tier_limits["min"],
                        max_timeout=tier_limits["max"]
                    )
                    return validated_timeout
                except MCPExecutionError:
                    # Tool timeout is invalid, fall back to default
                    logger.warning(
                        f"Tool timeout {tool_timeout}s is outside allowed range "
                        f"[{tier_limits['min']}, {tier_limits['max']}], using default"
                    )
        
        # Use system default
        return TimeoutConfig.DEFAULT_TIMEOUT_SECONDS
    
    def validate_timeout(
        self,
        timeout: int,
        min_timeout: Optional[int] = None,
        max_timeout: Optional[int] = None
    ) -> int:
        """
        Validate a timeout value is within allowed range.
        
        Args:
            timeout: Timeout value to validate in seconds
            min_timeout: Minimum allowed timeout (defaults to system min)
            max_timeout: Maximum allowed timeout (defaults to system max)
            
        Returns:
            Validated timeout value
            
        Raises:
            MCPExecutionError: If timeout is outside allowed range
        """
        if min_timeout is None:
            min_timeout = TimeoutConfig.MIN_TIMEOUT_SECONDS
        if max_timeout is None:
            max_timeout = TimeoutConfig.MAX_TIMEOUT_SECONDS
        
        if not isinstance(timeout, int):
            raise MCPExecutionError(
                f"Timeout must be an integer, got {type(timeout).__name__}"
            )
        
        if timeout < min_timeout:
            raise MCPExecutionError(
                f"Timeout {timeout}s is below minimum allowed timeout of {min_timeout}s"
            )
        
        if timeout > max_timeout:
            raise MCPExecutionError(
                f"Timeout {timeout}s exceeds maximum allowed timeout of {max_timeout}s"
            )
        
        return timeout
    
    def validate_timeout_for_tier(
        self,
        timeout: int,
        user_tier: str = "viewer"
    ) -> int:
        """
        Validate timeout against tier-specific limits.
        
        Args:
            timeout: Timeout value to validate in seconds
            user_tier: User tier (viewer, developer, admin)
            
        Returns:
            Validated timeout value
            
        Raises:
            MCPExecutionError: If timeout is outside tier limits
        """
        tier_limits = TimeoutConfig.TIER_TIMEOUT_LIMITS.get(
            user_tier,
            TimeoutConfig.TIER_TIMEOUT_LIMITS["viewer"]
        )
        
        return self.validate_timeout(
            timeout,
            min_timeout=tier_limits["min"],
            max_timeout=tier_limits["max"]
        )
    
    def record_timeout_event(
        self,
        execution_id: UUID,
        tool_id: UUID,
        tool_name: str,
        timeout_seconds: int,
        elapsed_seconds: float,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record a timeout event for monitoring and logging.
        
        Args:
            execution_id: ID of the execution that timed out
            tool_id: ID of the tool
            tool_name: Name of the tool
            timeout_seconds: Configured timeout value
            elapsed_seconds: Actual elapsed time before timeout
            context: Additional context information
        """
        execution_id_str = str(execution_id)
        
        timeout_event = {
            "execution_id": execution_id_str,
            "tool_id": str(tool_id),
            "tool_name": tool_name,
            "timeout_seconds": timeout_seconds,
            "elapsed_seconds": elapsed_seconds,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context or {}
        }
        
        self.timeout_events[execution_id_str] = timeout_event
        
        # Log the timeout event
        logger.warning(
            f"Execution timeout: execution_id={execution_id_str}, "
            f"tool={tool_name}, timeout={timeout_seconds}s, "
            f"elapsed={elapsed_seconds:.2f}s"
        )
    
    def get_timeout_event(
        self,
        execution_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get timeout event details for an execution.
        
        Args:
            execution_id: ID of the execution
            
        Returns:
            Timeout event details if available, None otherwise
        """
        return self.timeout_events.get(str(execution_id))
    
    def clear_timeout_event(
        self,
        execution_id: UUID
    ) -> None:
        """
        Clear timeout event from tracking.
        
        Args:
            execution_id: ID of the execution
        """
        execution_id_str = str(execution_id)
        if execution_id_str in self.timeout_events:
            del self.timeout_events[execution_id_str]
    
    async def execute_with_timeout(
        self,
        coro,
        timeout_seconds: int,
        execution_id: Optional[UUID] = None,
        tool_id: Optional[UUID] = None,
        tool_name: Optional[str] = None,
        cleanup_callback: Optional[callable] = None
    ):
        """
        Execute a coroutine with timeout enforcement and resource cleanup.
        
        Args:
            coro: Coroutine to execute
            timeout_seconds: Timeout in seconds
            execution_id: Optional execution ID for logging
            tool_id: Optional tool ID for logging
            tool_name: Optional tool name for logging
            cleanup_callback: Optional async callback for resource cleanup
            
        Returns:
            Result of the coroutine
            
        Raises:
            MCPExecutionError: If execution times out
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result
            
        except asyncio.TimeoutError:
            elapsed_seconds = asyncio.get_event_loop().time() - start_time
            
            # Record timeout event
            if execution_id and tool_id and tool_name:
                self.record_timeout_event(
                    execution_id=execution_id,
                    tool_id=tool_id,
                    tool_name=tool_name,
                    timeout_seconds=timeout_seconds,
                    elapsed_seconds=elapsed_seconds
                )
            
            # Execute cleanup callback if provided
            if cleanup_callback:
                try:
                    if asyncio.iscoroutinefunction(cleanup_callback):
                        await cleanup_callback()
                    else:
                        cleanup_callback()
                except Exception as e:
                    logger.error(
                        f"Error during timeout cleanup: {str(e)}",
                        exc_info=True
                    )
            
            # Raise timeout error
            error_msg = f"Execution timed out after {timeout_seconds} seconds"
            if tool_name:
                error_msg = f"Tool '{tool_name}' execution timed out after {timeout_seconds} seconds"
            
            raise MCPExecutionError(error_msg)
    
    def get_timeout_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about timeout events.
        
        Returns:
            Dictionary with timeout statistics
        """
        if not self.timeout_events:
            return {
                "total_timeouts": 0,
                "tools_with_timeouts": [],
                "average_timeout_duration": 0
            }
        
        tools = {}
        total_elapsed = 0
        
        for event in self.timeout_events.values():
            tool_name = event["tool_name"]
            if tool_name not in tools:
                tools[tool_name] = 0
            tools[tool_name] += 1
            total_elapsed += event["elapsed_seconds"]
        
        return {
            "total_timeouts": len(self.timeout_events),
            "tools_with_timeouts": [
                {"tool": tool, "count": count}
                for tool, count in sorted(
                    tools.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ],
            "average_timeout_duration": total_elapsed / len(self.timeout_events)
        }
