"""Connection Pool Manager - Manages reusable connections to MCP servers"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import deque
import logging

from app.core.exceptions import MCPExecutionError

logger = logging.getLogger(__name__)


@dataclass
class PoolConfig:
    """Configuration for connection pool"""
    min_size: int = 2
    max_size: int = 10
    idle_timeout: int = 300  # seconds (5 minutes)
    max_lifetime: int = 3600  # seconds (1 hour)
    health_check_interval: int = 30  # seconds


@dataclass
class MCPConnection:
    """Represents a connection to an MCP server"""
    connection_id: str
    tool_id: UUID
    command: str
    args: List[str]
    env: Dict[str, str]
    process: Optional[asyncio.subprocess.Process] = None
    created_at: float = field(default_factory=time.time)
    last_used_at: float = field(default_factory=time.time)
    last_health_check_at: float = field(default_factory=time.time)
    is_healthy: bool = True
    use_count: int = 0
    
    def is_idle_timeout_exceeded(self, idle_timeout: int) -> bool:
        """Check if connection has been idle for too long"""
        return (time.time() - self.last_used_at) > idle_timeout
    
    def is_max_lifetime_exceeded(self, max_lifetime: int) -> bool:
        """Check if connection has exceeded its maximum lifetime"""
        return (time.time() - self.created_at) > max_lifetime
    
    def should_health_check(self, health_check_interval: int) -> bool:
        """Check if it's time for a health check"""
        return (time.time() - self.last_health_check_at) > health_check_interval
    
    def mark_used(self) -> None:
        """Mark connection as used"""
        self.last_used_at = time.time()
        self.use_count += 1
    
    def mark_health_checked(self, is_healthy: bool) -> None:
        """Mark connection as health checked"""
        self.last_health_check_at = time.time()
        self.is_healthy = is_healthy


@dataclass
class PoolStats:
    """Statistics about the connection pool"""
    total_connections: int
    idle_connections: int
    active_connections: int
    healthy_connections: int
    unhealthy_connections: int
    total_uses: int
    pools_by_tool: Dict[str, int]


class ConnectionPoolManager:
    """
    Manages reusable connections to MCP servers for performance optimization.
    
    Features:
    - Connection pooling with min/max size configuration
    - Connection reuse to avoid startup overhead
    - Health check mechanism to detect failed connections
    - Idle timeout to free unused connections
    - Connection lifecycle management (creation, reuse, cleanup)
    
    Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
    """
    
    def __init__(self, config: Optional[PoolConfig] = None):
        """
        Initialize the connection pool manager.
        
        Args:
            config: Pool configuration (uses defaults if not provided)
        """
        self.config = config or PoolConfig()
        
        # Pool storage: tool_id -> deque of available connections
        self._pools: Dict[str, deque[MCPConnection]] = {}
        
        # Active connections being used: connection_id -> connection
        self._active_connections: Dict[str, MCPConnection] = {}
        
        # Lock for thread-safe pool operations
        self._pool_locks: Dict[str, asyncio.Lock] = {}
        
        # Background task for cleanup
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        logger.info(
            f"ConnectionPoolManager initialized with config: "
            f"min_size={self.config.min_size}, max_size={self.config.max_size}, "
            f"idle_timeout={self.config.idle_timeout}s, max_lifetime={self.config.max_lifetime}s"
        )
    
    async def start(self) -> None:
        """Start the connection pool manager and background tasks"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            logger.info("ConnectionPoolManager background cleanup task started")
    
    async def stop(self) -> None:
        """Stop the connection pool manager and close all connections"""
        logger.info("Stopping ConnectionPoolManager...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel cleanup task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connections
        for tool_id in list(self._pools.keys()):
            await self._close_all_connections_for_tool(tool_id)
        
        # Close active connections
        for conn_id in list(self._active_connections.keys()):
            conn = self._active_connections[conn_id]
            await self._close_connection(conn)
            del self._active_connections[conn_id]
        
        logger.info("ConnectionPoolManager stopped")
    
    async def get_connection(
        self,
        tool_id: UUID,
        command: str,
        args: List[str],
        env: Dict[str, str]
    ) -> MCPConnection:
        """
        Get a connection from the pool or create a new one.
        
        This implements connection reuse logic - if a healthy connection exists
        in the pool, it will be reused. Otherwise, a new connection is created.
        
        Args:
            tool_id: ID of the MCP tool
            command: Command to execute
            args: Command arguments
            env: Environment variables
            
        Returns:
            MCPConnection ready for use
            
        Raises:
            MCPExecutionError: If connection cannot be created or pool is at capacity
        """
        tool_id_str = str(tool_id)
        
        # Get or create lock for this tool
        if tool_id_str not in self._pool_locks:
            self._pool_locks[tool_id_str] = asyncio.Lock()
        
        async with self._pool_locks[tool_id_str]:
            # Try to get an existing connection from the pool
            if tool_id_str in self._pools and self._pools[tool_id_str]:
                # Get connection from pool
                conn = self._pools[tool_id_str].popleft()
                
                # Always check health before reusing
                is_healthy = await self.health_check(conn)
                if not is_healthy:
                    # Connection is unhealthy, close it and create a new one
                    logger.warning(
                        f"Connection {conn.connection_id} for tool {tool_id} "
                        f"failed health check, creating new connection"
                    )
                    await self._close_connection(conn)
                    conn = await self._create_connection(tool_id, command, args, env)
                
                # Check if connection exceeded max lifetime
                if conn.is_max_lifetime_exceeded(self.config.max_lifetime):
                    logger.info(
                        f"Connection {conn.connection_id} for tool {tool_id} "
                        f"exceeded max lifetime, creating new connection"
                    )
                    await self._close_connection(conn)
                    conn = await self._create_connection(tool_id, command, args, env)
                
                # Mark connection as used
                conn.mark_used()
                
                # Move to active connections
                self._active_connections[conn.connection_id] = conn
                
                logger.debug(
                    f"Reusing connection {conn.connection_id} for tool {tool_id} "
                    f"(use count: {conn.use_count})"
                )
                
                return conn
            
            # No available connection, check if we can create a new one
            total_connections = self._get_total_connections_for_tool(tool_id_str)
            
            if total_connections >= self.config.max_size:
                # Pool is at capacity, need to wait or reject
                logger.warning(
                    f"Connection pool for tool {tool_id} is at capacity "
                    f"({total_connections}/{self.config.max_size})"
                )
                raise MCPExecutionError(
                    f"Connection pool for tool {tool_id} is at maximum capacity. "
                    f"Please try again later."
                )
            
            # Create a new connection
            conn = await self._create_connection(tool_id, command, args, env)
            conn.mark_used()
            
            # Move to active connections
            self._active_connections[conn.connection_id] = conn
            
            logger.info(
                f"Created new connection {conn.connection_id} for tool {tool_id} "
                f"(total: {total_connections + 1}/{self.config.max_size})"
            )
            
            return conn
    
    async def release_connection(self, connection: MCPConnection) -> None:
        """
        Release a connection back to the pool.
        
        The connection will be returned to the pool for reuse if it's healthy
        and hasn't exceeded its lifetime. Otherwise, it will be closed.
        
        Args:
            connection: Connection to release
        """
        tool_id_str = str(connection.tool_id)
        
        # Remove from active connections
        if connection.connection_id in self._active_connections:
            del self._active_connections[connection.connection_id]
        
        # Check if connection should be closed
        if not connection.is_healthy:
            logger.info(
                f"Closing unhealthy connection {connection.connection_id} "
                f"for tool {connection.tool_id}"
            )
            await self._close_connection(connection)
            return
        
        if connection.is_max_lifetime_exceeded(self.config.max_lifetime):
            logger.info(
                f"Closing connection {connection.connection_id} for tool {connection.tool_id} "
                f"(exceeded max lifetime)"
            )
            await self._close_connection(connection)
            return
        
        # Return to pool
        if tool_id_str not in self._pools:
            self._pools[tool_id_str] = deque()
        
        self._pools[tool_id_str].append(connection)
        
        logger.debug(
            f"Released connection {connection.connection_id} back to pool "
            f"for tool {connection.tool_id}"
        )
    
    async def health_check(self, connection: MCPConnection) -> bool:
        """
        Check if a connection is healthy.
        
        A connection is considered healthy if its process is still running.
        
        Args:
            connection: Connection to check
            
        Returns:
            True if connection is healthy, False otherwise
        """
        try:
            # Check if process is still running
            if connection.process is None:
                connection.mark_health_checked(False)
                return False
            
            # Check if process has terminated
            if connection.process.returncode is not None:
                logger.warning(
                    f"Connection {connection.connection_id} process terminated "
                    f"with code {connection.process.returncode}"
                )
                connection.mark_health_checked(False)
                return False
            
            # Process is running
            connection.mark_health_checked(True)
            return True
            
        except Exception as e:
            logger.error(
                f"Error during health check for connection {connection.connection_id}: {e}"
            )
            connection.mark_health_checked(False)
            return False
    
    async def close_idle_connections(self) -> int:
        """
        Close connections that have been idle for too long.
        
        This is called periodically by the cleanup loop to free resources.
        
        Returns:
            Number of connections closed
        """
        closed_count = 0
        
        for tool_id_str in list(self._pools.keys()):
            if tool_id_str not in self._pool_locks:
                self._pool_locks[tool_id_str] = asyncio.Lock()
            
            async with self._pool_locks[tool_id_str]:
                if tool_id_str not in self._pools:
                    continue
                
                pool = self._pools[tool_id_str]
                connections_to_keep = deque()
                
                while pool:
                    conn = pool.popleft()
                    
                    # Check if connection is idle for too long
                    if conn.is_idle_timeout_exceeded(self.config.idle_timeout):
                        logger.info(
                            f"Closing idle connection {conn.connection_id} "
                            f"for tool {conn.tool_id} "
                            f"(idle for {int(time.time() - conn.last_used_at)}s)"
                        )
                        await self._close_connection(conn)
                        closed_count += 1
                    else:
                        connections_to_keep.append(conn)
                
                # Update pool with connections to keep
                self._pools[tool_id_str] = connections_to_keep
                
                # Remove empty pools
                if not self._pools[tool_id_str]:
                    del self._pools[tool_id_str]
        
        if closed_count > 0:
            logger.info(f"Closed {closed_count} idle connections")
        
        return closed_count
    
    async def get_pool_stats(self) -> PoolStats:
        """
        Get statistics about the connection pool.
        
        Returns:
            PoolStats with current pool state
        """
        total_connections = 0
        idle_connections = 0
        active_connections = len(self._active_connections)
        healthy_connections = 0
        unhealthy_connections = 0
        total_uses = 0
        pools_by_tool = {}
        
        # Count idle connections in pools
        for tool_id_str, pool in self._pools.items():
            pool_size = len(pool)
            idle_connections += pool_size
            total_connections += pool_size
            pools_by_tool[tool_id_str] = pool_size
            
            for conn in pool:
                if conn.is_healthy:
                    healthy_connections += 1
                else:
                    unhealthy_connections += 1
                total_uses += conn.use_count
        
        # Count active connections
        for conn in self._active_connections.values():
            total_connections += 1
            if conn.is_healthy:
                healthy_connections += 1
            else:
                unhealthy_connections += 1
            total_uses += conn.use_count
            
            tool_id_str = str(conn.tool_id)
            pools_by_tool[tool_id_str] = pools_by_tool.get(tool_id_str, 0) + 1
        
        return PoolStats(
            total_connections=total_connections,
            idle_connections=idle_connections,
            active_connections=active_connections,
            healthy_connections=healthy_connections,
            unhealthy_connections=unhealthy_connections,
            total_uses=total_uses,
            pools_by_tool=pools_by_tool
        )
    
    async def _create_connection(
        self,
        tool_id: UUID,
        command: str,
        args: List[str],
        env: Dict[str, str]
    ) -> MCPConnection:
        """
        Create a new connection to an MCP server.
        
        This starts a subprocess for the MCP server that will be kept alive
        for reuse.
        
        Args:
            tool_id: ID of the MCP tool
            command: Command to execute
            args: Command arguments
            env: Environment variables
            
        Returns:
            New MCPConnection
            
        Raises:
            MCPExecutionError: If connection cannot be created
        """
        import uuid
        
        connection_id = str(uuid.uuid4())
        
        try:
            # Build the command
            cmd = [command] + args
            
            # Start the process
            # Note: For MCP servers, we keep the process alive for reuse
            # The process will handle multiple JSON-RPC requests over stdio
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**env}
            )
            
            # Give the process a moment to start
            await asyncio.sleep(0.1)
            
            # Check if process started successfully
            if process.returncode is not None:
                raise MCPExecutionError(
                    f"Process failed to start with exit code {process.returncode}"
                )
            
            # Create connection object
            connection = MCPConnection(
                connection_id=connection_id,
                tool_id=tool_id,
                command=command,
                args=args,
                env=env,
                process=process,
                created_at=time.time(),
                last_used_at=time.time(),
                last_health_check_at=time.time(),
                is_healthy=True,
                use_count=0
            )
            
            logger.debug(
                f"Created connection {connection_id} for tool {tool_id} "
                f"with command: {command}"
            )
            
            return connection
            
        except FileNotFoundError:
            raise MCPExecutionError(
                f"Command '{command}' not found. Make sure it's installed."
            )
        except Exception as e:
            raise MCPExecutionError(
                f"Failed to create connection: {str(e)}"
            )
    
    async def _close_connection(self, connection: MCPConnection) -> None:
        """
        Close a connection and clean up resources.
        
        Args:
            connection: Connection to close
        """
        try:
            if connection.process and connection.process.returncode is None:
                # Terminate the process gracefully
                try:
                    connection.process.terminate()
                except Exception:
                    pass  # Process might already be terminated
                
                try:
                    # Wait up to 5 seconds for graceful termination
                    await asyncio.wait_for(connection.process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    # Force kill if graceful termination fails
                    try:
                        connection.process.kill()
                        await connection.process.wait()
                    except Exception:
                        pass  # Process might already be dead
            
            logger.debug(
                f"Closed connection {connection.connection_id} for tool {connection.tool_id}"
            )
            
        except Exception as e:
            logger.error(
                f"Error closing connection {connection.connection_id}: {e}"
            )
    
    async def _close_all_connections_for_tool(self, tool_id_str: str) -> None:
        """
        Close all connections for a specific tool.
        
        Args:
            tool_id_str: Tool ID as string
        """
        if tool_id_str not in self._pools:
            return
        
        async with self._pool_locks.get(tool_id_str, asyncio.Lock()):
            pool = self._pools[tool_id_str]
            
            while pool:
                conn = pool.popleft()
                await self._close_connection(conn)
            
            del self._pools[tool_id_str]
    
    def _get_total_connections_for_tool(self, tool_id_str: str) -> int:
        """
        Get total number of connections (idle + active) for a tool.
        
        Args:
            tool_id_str: Tool ID as string
            
        Returns:
            Total connection count
        """
        idle_count = len(self._pools.get(tool_id_str, []))
        active_count = sum(
            1 for conn in self._active_connections.values()
            if str(conn.tool_id) == tool_id_str
        )
        return idle_count + active_count
    
    async def _cleanup_loop(self) -> None:
        """
        Background task that periodically cleans up idle connections.
        
        This runs every 60 seconds and closes connections that have been
        idle for longer than the configured idle_timeout.
        """
        logger.info("Connection pool cleanup loop started")
        
        while not self._shutdown_event.is_set():
            try:
                # Wait for 60 seconds or until shutdown
                await asyncio.wait_for(
                    self._shutdown_event.wait(),
                    timeout=60.0
                )
                # If we get here, shutdown was signaled
                break
                
            except asyncio.TimeoutError:
                # Timeout is expected, continue with cleanup
                pass
            
            try:
                # Close idle connections
                await self.close_idle_connections()
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
        
        logger.info("Connection pool cleanup loop stopped")
