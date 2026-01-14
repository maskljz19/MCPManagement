"""Unit tests for TimeoutManager"""

import pytest
import asyncio
from uuid import uuid4
from app.services.timeout_manager import TimeoutManager, TimeoutConfig
from app.core.exceptions import MCPExecutionError


class TestTimeoutManager:
    """Test suite for TimeoutManager"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.timeout_manager = TimeoutManager()
    
    def test_get_timeout_uses_default_when_no_config(self):
        """Test that default timeout is used when no config provided"""
        timeout = self.timeout_manager.get_timeout_for_execution()
        assert timeout == TimeoutConfig.DEFAULT_TIMEOUT_SECONDS
    
    def test_get_timeout_uses_tool_config(self):
        """Test that tool config timeout is used when provided"""
        tool_config = {"timeout": 60}
        timeout = self.timeout_manager.get_timeout_for_execution(
            tool_config=tool_config
        )
        assert timeout == 60
    
    def test_get_timeout_uses_user_timeout_over_tool_config(self):
        """Test that user timeout takes priority over tool config"""
        tool_config = {"timeout": 60}
        timeout = self.timeout_manager.get_timeout_for_execution(
            tool_config=tool_config,
            user_timeout=120
        )
        assert timeout == 120
    
    def test_get_timeout_respects_tier_limits(self):
        """Test that timeout respects tier-based limits"""
        # Viewer tier max is 300 seconds
        timeout = self.timeout_manager.get_timeout_for_execution(
            user_timeout=200,
            user_tier="viewer"
        )
        assert timeout == 200
        
        # Developer tier max is 1800 seconds
        timeout = self.timeout_manager.get_timeout_for_execution(
            user_timeout=1000,
            user_tier="developer"
        )
        assert timeout == 1000
    
    def test_get_timeout_falls_back_to_default_when_tool_timeout_invalid(self):
        """Test that default is used when tool timeout exceeds tier limit"""
        tool_config = {"timeout": 500}  # Exceeds viewer limit of 300
        timeout = self.timeout_manager.get_timeout_for_execution(
            tool_config=tool_config,
            user_tier="viewer"
        )
        assert timeout == TimeoutConfig.DEFAULT_TIMEOUT_SECONDS
    
    def test_validate_timeout_accepts_valid_value(self):
        """Test that valid timeout values are accepted"""
        timeout = self.timeout_manager.validate_timeout(30)
        assert timeout == 30
    
    def test_validate_timeout_rejects_below_minimum(self):
        """Test that timeout below minimum is rejected"""
        with pytest.raises(MCPExecutionError) as exc_info:
            self.timeout_manager.validate_timeout(0)
        assert "below minimum" in str(exc_info.value)
    
    def test_validate_timeout_rejects_above_maximum(self):
        """Test that timeout above maximum is rejected"""
        with pytest.raises(MCPExecutionError) as exc_info:
            self.timeout_manager.validate_timeout(5000)
        assert "exceeds maximum" in str(exc_info.value)
    
    def test_validate_timeout_rejects_non_integer(self):
        """Test that non-integer timeout is rejected"""
        with pytest.raises(MCPExecutionError) as exc_info:
            self.timeout_manager.validate_timeout("30")
        assert "must be an integer" in str(exc_info.value)
    
    def test_validate_timeout_for_tier_viewer(self):
        """Test tier-specific validation for viewer"""
        # Valid for viewer
        timeout = self.timeout_manager.validate_timeout_for_tier(200, "viewer")
        assert timeout == 200
        
        # Invalid for viewer (exceeds 300s limit)
        with pytest.raises(MCPExecutionError):
            self.timeout_manager.validate_timeout_for_tier(400, "viewer")
    
    def test_validate_timeout_for_tier_developer(self):
        """Test tier-specific validation for developer"""
        # Valid for developer
        timeout = self.timeout_manager.validate_timeout_for_tier(1000, "developer")
        assert timeout == 1000
        
        # Invalid for developer (exceeds 1800s limit)
        with pytest.raises(MCPExecutionError):
            self.timeout_manager.validate_timeout_for_tier(2000, "developer")
    
    def test_validate_timeout_for_tier_admin(self):
        """Test tier-specific validation for admin"""
        # Valid for admin
        timeout = self.timeout_manager.validate_timeout_for_tier(3000, "admin")
        assert timeout == 3000
        
        # Invalid for admin (exceeds 3600s limit)
        with pytest.raises(MCPExecutionError):
            self.timeout_manager.validate_timeout_for_tier(4000, "admin")
    
    def test_record_timeout_event(self):
        """Test that timeout events are recorded"""
        execution_id = uuid4()
        tool_id = uuid4()
        
        self.timeout_manager.record_timeout_event(
            execution_id=execution_id,
            tool_id=tool_id,
            tool_name="test-tool",
            timeout_seconds=30,
            elapsed_seconds=30.5,
            context={"user_id": "test-user"}
        )
        
        event = self.timeout_manager.get_timeout_event(execution_id)
        assert event is not None
        assert event["execution_id"] == str(execution_id)
        assert event["tool_id"] == str(tool_id)
        assert event["tool_name"] == "test-tool"
        assert event["timeout_seconds"] == 30
        assert event["elapsed_seconds"] == 30.5
        assert event["context"]["user_id"] == "test-user"
    
    def test_get_timeout_event_returns_none_when_not_found(self):
        """Test that get_timeout_event returns None for unknown execution"""
        event = self.timeout_manager.get_timeout_event(uuid4())
        assert event is None
    
    def test_clear_timeout_event(self):
        """Test that timeout events can be cleared"""
        execution_id = uuid4()
        
        self.timeout_manager.record_timeout_event(
            execution_id=execution_id,
            tool_id=uuid4(),
            tool_name="test-tool",
            timeout_seconds=30,
            elapsed_seconds=30.5
        )
        
        # Event should exist
        assert self.timeout_manager.get_timeout_event(execution_id) is not None
        
        # Clear event
        self.timeout_manager.clear_timeout_event(execution_id)
        
        # Event should be gone
        assert self.timeout_manager.get_timeout_event(execution_id) is None
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self):
        """Test successful execution within timeout"""
        async def quick_task():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await self.timeout_manager.execute_with_timeout(
            quick_task(),
            timeout_seconds=1
        )
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout_exceeds(self):
        """Test execution that exceeds timeout"""
        async def slow_task():
            await asyncio.sleep(2)
            return "should not reach here"
        
        with pytest.raises(MCPExecutionError) as exc_info:
            await self.timeout_manager.execute_with_timeout(
                slow_task(),
                timeout_seconds=0.5,
                execution_id=uuid4(),
                tool_id=uuid4(),
                tool_name="slow-tool"
            )
        
        assert "timed out" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_execute_with_timeout_calls_cleanup(self):
        """Test that cleanup callback is called on timeout"""
        cleanup_called = False
        
        async def cleanup():
            nonlocal cleanup_called
            cleanup_called = True
        
        async def slow_task():
            await asyncio.sleep(2)
        
        with pytest.raises(MCPExecutionError):
            await self.timeout_manager.execute_with_timeout(
                slow_task(),
                timeout_seconds=0.5,
                cleanup_callback=cleanup
            )
        
        assert cleanup_called
    
    def test_get_timeout_statistics_empty(self):
        """Test statistics when no timeouts recorded"""
        stats = self.timeout_manager.get_timeout_statistics()
        assert stats["total_timeouts"] == 0
        assert stats["tools_with_timeouts"] == []
        assert stats["average_timeout_duration"] == 0
    
    def test_get_timeout_statistics_with_events(self):
        """Test statistics with recorded timeout events"""
        # Record multiple timeout events
        for i in range(3):
            self.timeout_manager.record_timeout_event(
                execution_id=uuid4(),
                tool_id=uuid4(),
                tool_name="tool-a",
                timeout_seconds=30,
                elapsed_seconds=30.0 + i
            )
        
        for i in range(2):
            self.timeout_manager.record_timeout_event(
                execution_id=uuid4(),
                tool_id=uuid4(),
                tool_name="tool-b",
                timeout_seconds=60,
                elapsed_seconds=60.0 + i
            )
        
        stats = self.timeout_manager.get_timeout_statistics()
        assert stats["total_timeouts"] == 5
        assert len(stats["tools_with_timeouts"]) == 2
        
        # Check tool counts (sorted by count descending)
        assert stats["tools_with_timeouts"][0]["tool"] == "tool-a"
        assert stats["tools_with_timeouts"][0]["count"] == 3
        assert stats["tools_with_timeouts"][1]["tool"] == "tool-b"
        assert stats["tools_with_timeouts"][1]["count"] == 2
        
        # Check average
        expected_avg = (30.0 + 31.0 + 32.0 + 60.0 + 61.0) / 5
        assert abs(stats["average_timeout_duration"] - expected_avg) < 0.01
