"""Unit tests for ConnectionPoolManager"""

import pytest
import asyncio
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch

from app.services.connection_pool_manager import (
    ConnectionPoolManager,
    PoolConfig,
    MCPConnection,
    PoolStats
)
from app.core.exceptions import MCPExecutionError


@pytest.fixture
def pool_config():
    """Create a test pool configuration"""
    return PoolConfig(
        min_size=1,
        max_size=3,
        idle_timeout=5,  # 5 seconds for faster testing
        max_lifetime=60,  # 1 minute
        health_check_interval=2  # 2 seconds
    )


@pytest.fixture
async def pool_manager(pool_config):
    """Create a connection pool manager for testing"""
    manager = ConnectionPoolManager(config=pool_config)
    await manager.start()
    yield manager
    await manager.stop()


@pytest.mark.asyncio
async def test_pool_manager_initialization(pool_config):
    """Test that pool manager initializes correctly"""
    manager = ConnectionPoolManager(config=pool_config)
    
    assert manager.config.min_size == 1
    assert manager.config.max_size == 3
    assert manager.config.idle_timeout == 5
    assert manager.config.max_lifetime == 60
    assert len(manager._pools) == 0
    assert len(manager._active_connections) == 0


@pytest.mark.asyncio
async def test_create_connection(pool_manager):
    """Test creating a new connection"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        conn = await pool_manager._create_connection(tool_id, command, args, env)
        
        assert conn.tool_id == tool_id
        assert conn.command == command
        assert conn.args == args
        assert conn.is_healthy is True
        assert conn.use_count == 0


@pytest.mark.asyncio
async def test_get_connection_creates_new(pool_manager):
    """Test that get_connection creates a new connection when pool is empty"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        
        assert conn is not None
        assert conn.tool_id == tool_id
        assert conn.use_count == 1
        assert conn.connection_id in pool_manager._active_connections


@pytest.mark.asyncio
async def test_release_connection_returns_to_pool(pool_manager):
    """Test that releasing a connection returns it to the pool"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Get a connection
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        assert conn.connection_id in pool_manager._active_connections
        
        # Release it
        await pool_manager.release_connection(conn)
        
        # Check it's back in the pool
        tool_id_str = str(tool_id)
        assert tool_id_str in pool_manager._pools
        assert len(pool_manager._pools[tool_id_str]) == 1
        assert conn.connection_id not in pool_manager._active_connections


@pytest.mark.asyncio
async def test_connection_reuse(pool_manager):
    """Test that connections are reused from the pool"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Get a connection
        conn1 = await pool_manager.get_connection(tool_id, command, args, env)
        first_conn_id = conn1.connection_id
        assert conn1.use_count == 1
        
        # Release it
        await pool_manager.release_connection(conn1)
        
        # Get another connection - should reuse the same one
        conn2 = await pool_manager.get_connection(tool_id, command, args, env)
        
        assert conn2.connection_id == first_conn_id
        assert conn2.use_count == 2  # Should be incremented


@pytest.mark.asyncio
async def test_pool_capacity_limit(pool_manager):
    """Test that pool enforces maximum capacity"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Get max_size connections (3 in our test config)
        connections = []
        for _ in range(pool_manager.config.max_size):
            conn = await pool_manager.get_connection(tool_id, command, args, env)
            connections.append(conn)
        
        # Try to get one more - should fail
        with pytest.raises(MCPExecutionError) as exc_info:
            await pool_manager.get_connection(tool_id, command, args, env)
        
        assert "maximum capacity" in str(exc_info.value)


@pytest.mark.asyncio
async def test_health_check_healthy_connection(pool_manager):
    """Test health check on a healthy connection"""
    tool_id = uuid4()
    
    # Create a mock connection with a running process
    mock_process = Mock()
    mock_process.returncode = None  # Still running
    
    conn = MCPConnection(
        connection_id="test-conn",
        tool_id=tool_id,
        command="python",
        args=[],
        env={},
        process=mock_process
    )
    
    is_healthy = await pool_manager.health_check(conn)
    
    assert is_healthy is True
    assert conn.is_healthy is True


@pytest.mark.asyncio
async def test_health_check_terminated_connection(pool_manager):
    """Test health check on a terminated connection"""
    tool_id = uuid4()
    
    # Create a mock connection with a terminated process
    mock_process = Mock()
    mock_process.returncode = 1  # Process terminated
    
    conn = MCPConnection(
        connection_id="test-conn",
        tool_id=tool_id,
        command="python",
        args=[],
        env={},
        process=mock_process
    )
    
    is_healthy = await pool_manager.health_check(conn)
    
    assert is_healthy is False
    assert conn.is_healthy is False


@pytest.mark.asyncio
async def test_close_idle_connections(pool_manager):
    """Test that idle connections are closed"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        # Get and release a connection
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        await pool_manager.release_connection(conn)
        
        # Manually set last_used_at to simulate idle timeout
        tool_id_str = str(tool_id)
        pool = pool_manager._pools[tool_id_str]
        for c in pool:
            c.last_used_at = 0  # Very old timestamp
        
        # Close idle connections
        closed_count = await pool_manager.close_idle_connections()
        
        assert closed_count == 1
        assert tool_id_str not in pool_manager._pools or len(pool_manager._pools[tool_id_str]) == 0


@pytest.mark.asyncio
async def test_get_pool_stats(pool_manager):
    """Test getting pool statistics"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_subprocess.return_value = mock_process
        
        # Get some connections
        conn1 = await pool_manager.get_connection(tool_id, command, args, env)
        conn2 = await pool_manager.get_connection(tool_id, command, args, env)
        
        # Release one
        await pool_manager.release_connection(conn1)
        
        # Get stats
        stats = await pool_manager.get_pool_stats()
        
        assert stats.total_connections == 2
        assert stats.idle_connections == 1
        assert stats.active_connections == 1
        assert stats.healthy_connections == 2
        assert str(tool_id) in stats.pools_by_tool


@pytest.mark.asyncio
async def test_connection_max_lifetime(pool_manager):
    """Test that connections exceeding max lifetime are not reused"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        # Get a connection
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        first_conn_id = conn.connection_id
        
        # Release it
        await pool_manager.release_connection(conn)
        
        # Manually set created_at to simulate max lifetime exceeded
        tool_id_str = str(tool_id)
        pool = pool_manager._pools[tool_id_str]
        for c in pool:
            c.created_at = 0  # Very old timestamp
        
        # Get another connection - should create a new one due to max lifetime
        conn2 = await pool_manager.get_connection(tool_id, command, args, env)
        
        # Should be a different connection
        assert conn2.connection_id != first_conn_id


@pytest.mark.asyncio
async def test_unhealthy_connection_not_reused(pool_manager):
    """Test that unhealthy connections are not reused"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        # First call creates a healthy process
        mock_process1 = AsyncMock()
        mock_process1.returncode = None
        
        # Second call also creates a healthy process (for the replacement)
        mock_process2 = AsyncMock()
        mock_process2.returncode = None
        
        # Set up the mock to return different processes
        mock_subprocess.side_effect = [mock_process1, mock_process2]
        
        # Get a connection
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        first_conn_id = conn.connection_id
        
        # Release it
        await pool_manager.release_connection(conn)
        
        # Mark the connection as unhealthy by setting process returncode
        tool_id_str = str(tool_id)
        pool = pool_manager._pools[tool_id_str]
        for c in pool:
            c.is_healthy = False
            c.process.returncode = 1  # Simulate terminated process
        
        # Get another connection - should create a new one due to failed health check
        conn2 = await pool_manager.get_connection(tool_id, command, args, env)
        
        # Should be a different connection
        assert conn2.connection_id != first_conn_id


@pytest.mark.asyncio
async def test_release_unhealthy_connection_closes_it(pool_manager):
    """Test that releasing an unhealthy connection closes it instead of pooling"""
    tool_id = uuid4()
    command = "python"
    args = ["-c", "import time; time.sleep(10)"]
    env = {}
    
    # Mock the subprocess creation
    with patch('asyncio.create_subprocess_exec') as mock_subprocess:
        mock_process = AsyncMock()
        mock_process.returncode = None
        mock_process.terminate = AsyncMock()
        mock_process.wait = AsyncMock()
        mock_subprocess.return_value = mock_process
        
        # Get a connection
        conn = await pool_manager.get_connection(tool_id, command, args, env)
        
        # Mark it as unhealthy
        conn.is_healthy = False
        
        # Release it
        await pool_manager.release_connection(conn)
        
        # Should not be in the pool
        tool_id_str = str(tool_id)
        assert tool_id_str not in pool_manager._pools or len(pool_manager._pools[tool_id_str]) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
