"""MCP Server Manager Service - Handles deployment lifecycle and request routing"""

import asyncio
import subprocess
import signal
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.models.deployment import (
    MCPDeploymentModel,
    DeploymentStatus,
    HealthStatus
)
from app.schemas.deployment import (
    DeploymentConfig,
    Deployment,
    HealthCheckResult
)


class MCPServerManager:
    """
    MCP Server Manager handles deployment lifecycle and request routing.
    
    Responsibilities:
    - Deploy MCP servers as subprocesses
    - Generate unique endpoint URLs
    - Route requests to deployed servers
    - Monitor server health
    - Gracefully shutdown servers
    """
    
    def __init__(
        self,
        db_session: AsyncSession,
        base_url: str = "http://localhost",
        port_range_start: int = 8100,
        port_range_end: int = 8200
    ):
        self.db = db_session
        self.base_url = base_url
        self.port_range_start = port_range_start
        self.port_range_end = port_range_end
        
        # Track active processes and their ports
        self._processes: Dict[str, subprocess.Popen] = {}
        self._port_assignments: Dict[str, int] = {}
        self._used_ports: set = set()
    
    # ========================================================================
    # Deployment Lifecycle Management
    # ========================================================================
    
    async def deploy_server(
        self,
        tool_id: UUID,
        config: DeploymentConfig
    ) -> Deployment:
        """
        Deploy an MCP server instance.
        
        Args:
            tool_id: ID of the MCP tool to deploy
            config: Deployment configuration
            
        Returns:
            Deployment record
            
        Raises:
            ValueError: If tool not found or deployment fails
        """
        # Generate unique deployment ID
        deployment_id = str(uuid4())
        
        # Assign port
        port = config.port or await self._allocate_port()
        
        # Generate unique endpoint URL
        endpoint_url = f"{self.base_url}:{port}/mcp/v1"
        
        # Create deployment record in MySQL
        deployment_model = MCPDeploymentModel(
            id=deployment_id,
            tool_id=str(tool_id),
            endpoint_url=endpoint_url,
            status=DeploymentStatus.STARTING,
            health_status=HealthStatus.UNKNOWN,
            deployed_at=datetime.utcnow()
        )
        
        self.db.add(deployment_model)
        await self.db.flush()
        await self.db.refresh(deployment_model)
        
        try:
            # Start the MCP server process
            process = await self._start_server_process(
                deployment_id=deployment_id,
                tool_id=tool_id,
                port=port,
                environment=config.environment
            )
            
            # Store process reference
            self._processes[deployment_id] = process
            self._port_assignments[deployment_id] = port
            self._used_ports.add(port)
            
            # Update status to running
            deployment_model.status = DeploymentStatus.RUNNING
            await self.db.flush()
            await self.db.refresh(deployment_model)
            
        except Exception as e:
            # Update status to failed
            deployment_model.status = DeploymentStatus.FAILED
            await self.db.flush()
            raise ValueError(f"Failed to deploy server: {str(e)}")
        
        # Convert to Pydantic model
        return Deployment.model_validate(deployment_model)
    
    async def stop_server(self, deployment_id: UUID) -> bool:
        """
        Gracefully stop an MCP server deployment.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            True if stopped successfully, False if not found
        """
        deployment_id_str = str(deployment_id)
        
        # Get deployment record
        stmt = select(MCPDeploymentModel).where(
            MCPDeploymentModel.id == deployment_id_str
        )
        result = await self.db.execute(stmt)
        deployment_model = result.scalar_one_or_none()
        
        if not deployment_model:
            return False
        
        # Stop the process if it exists
        if deployment_id_str in self._processes:
            process = self._processes[deployment_id_str]
            
            try:
                # Send SIGTERM for graceful shutdown
                process.terminate()
                
                # Wait up to 10 seconds for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    process.kill()
                    process.wait()
                
            except Exception as e:
                # Process might already be dead
                pass
            
            # Clean up tracking
            del self._processes[deployment_id_str]
            
            if deployment_id_str in self._port_assignments:
                port = self._port_assignments[deployment_id_str]
                self._used_ports.discard(port)
                del self._port_assignments[deployment_id_str]
        
        # Update deployment status
        deployment_model.status = DeploymentStatus.STOPPED
        deployment_model.stopped_at = datetime.utcnow()
        await self.db.flush()
        
        return True
    
    # ========================================================================
    # Request Routing
    # ========================================================================
    
    async def route_request(
        self,
        slug: str,
        path: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None
    ) -> httpx.Response:
        """
        Route an HTTP request to the appropriate deployed MCP server.
        
        Args:
            slug: Tool slug to route to
            path: Request path
            method: HTTP method
            headers: Request headers
            body: Request body
            
        Returns:
            HTTP response from the deployed server
            
        Raises:
            ValueError: If no active deployment found for slug
        """
        # Find active deployment for this slug
        from app.models.mcp_tool import MCPToolModel
        
        # Join deployments with tools to find by slug
        stmt = (
            select(MCPDeploymentModel)
            .join(MCPToolModel, MCPDeploymentModel.tool_id == MCPToolModel.id)
            .where(
                MCPToolModel.slug == slug,
                MCPDeploymentModel.status == DeploymentStatus.RUNNING,
                MCPToolModel.deleted_at.is_(None)
            )
        )
        
        result = await self.db.execute(stmt)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise ValueError(f"No active deployment found for slug: {slug}")
        
        # Forward request to deployment endpoint
        target_url = f"{deployment.endpoint_url}{path}"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=target_url,
                headers=headers,
                content=body
            )
        
        return response
    
    # ========================================================================
    # Health Monitoring
    # ========================================================================
    
    async def check_health(self, deployment_id: UUID) -> HealthCheckResult:
        """
        Check health of a deployed MCP server.
        
        Args:
            deployment_id: Deployment identifier
            
        Returns:
            Health check result
        """
        deployment_id_str = str(deployment_id)
        
        # Get deployment record
        stmt = select(MCPDeploymentModel).where(
            MCPDeploymentModel.id == deployment_id_str
        )
        result = await self.db.execute(stmt)
        deployment_model = result.scalar_one_or_none()
        
        if not deployment_model:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        health_status = HealthStatus.UNKNOWN
        details = {}
        
        # Check if process is still running
        if deployment_id_str in self._processes:
            process = self._processes[deployment_id_str]
            
            if process.poll() is None:
                # Process is running, check HTTP endpoint
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(
                            f"{deployment_model.endpoint_url}/health"
                        )
                        
                        if response.status_code == 200:
                            health_status = HealthStatus.HEALTHY
                            details = {"http_status": 200}
                        else:
                            health_status = HealthStatus.UNHEALTHY
                            details = {"http_status": response.status_code}
                            
                except Exception as e:
                    health_status = HealthStatus.UNHEALTHY
                    details = {"error": str(e)}
            else:
                # Process has terminated
                health_status = HealthStatus.UNHEALTHY
                details = {"error": "Process terminated", "exit_code": process.returncode}
        else:
            # No process tracked
            health_status = HealthStatus.UNHEALTHY
            details = {"error": "No process found"}
        
        # Update deployment record
        deployment_model.health_status = health_status
        deployment_model.last_health_check = datetime.utcnow()
        await self.db.flush()
        
        return HealthCheckResult(
            deployment_id=deployment_id,
            status=health_status,
            checked_at=datetime.utcnow(),
            details=details
        )
    
    # ========================================================================
    # Private Helper Methods
    # ========================================================================
    
    async def _allocate_port(self) -> int:
        """Allocate an available port from the port range"""
        for port in range(self.port_range_start, self.port_range_end + 1):
            if port not in self._used_ports:
                return port
        
        raise ValueError("No available ports in the configured range")
    
    async def _start_server_process(
        self,
        deployment_id: str,
        tool_id: UUID,
        port: int,
        environment: Dict[str, str]
    ) -> subprocess.Popen:
        """
        Start an MCP server process.
        
        This is a simplified implementation that starts a placeholder process.
        In production, this would start the actual MCP server with proper configuration.
        
        Args:
            deployment_id: Deployment identifier
            tool_id: Tool identifier
            port: Port to bind to
            environment: Environment variables
            
        Returns:
            Process handle
        """
        # Build environment
        env = {
            **environment,
            "MCP_DEPLOYMENT_ID": deployment_id,
            "MCP_TOOL_ID": str(tool_id),
            "MCP_PORT": str(port)
        }
        
        # In a real implementation, this would start the actual MCP server
        # For now, we'll start a simple HTTP server as a placeholder
        # This allows the deployment to be tracked and health checked
        
        # Start process (simplified - in production would use proper MCP server)
        process = subprocess.Popen(
            ["python", "-m", "http.server", str(port)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True
        )
        
        # Give the process a moment to start
        await asyncio.sleep(0.5)
        
        # Check if process started successfully
        if process.poll() is not None:
            raise RuntimeError(f"Process failed to start with exit code {process.returncode}")
        
        return process
