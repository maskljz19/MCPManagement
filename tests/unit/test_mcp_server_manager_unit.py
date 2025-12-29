"""Unit tests for MCP Server Manager"""

import pytest
from uuid import uuid4
from app.services.mcp_server_manager import MCPServerManager
from app.schemas.deployment import DeploymentConfig
from app.models.deployment import DeploymentStatus, HealthStatus


@pytest.mark.asyncio
async def test_port_allocation(db_session):
    """Test that port allocation works correctly"""
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9105
    )
    
    # Allocate first port
    port1 = await manager._allocate_port()
    assert 9100 <= port1 <= 9105
    
    # Mark it as used
    manager._used_ports.add(port1)
    
    # Allocate second port (should be different)
    port2 = await manager._allocate_port()
    assert 9100 <= port2 <= 9105
    assert port2 != port1


@pytest.mark.asyncio
async def test_port_allocation_exhaustion(db_session):
    """Test that port allocation fails when all ports are used"""
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9102  # Only 3 ports available
    )
    
    # Use all ports
    manager._used_ports = {9100, 9101, 9102}
    
    # Should raise ValueError
    with pytest.raises(ValueError, match="No available ports"):
        await manager._allocate_port()


@pytest.mark.asyncio
async def test_deployment_record_creation(db_session, mcp_manager_fixture):
    """Test that deployment creates a record in the database"""
    from app.schemas.mcp_tool import MCPToolCreate
    from app.models.mcp_tool import ToolStatus
    
    # Create a tool first
    tool_data = MCPToolCreate(
        name="Test Tool",
        slug="test-tool",
        description="Test description",
        version="1.0.0",
        config={"test": "config"},
        author_id=uuid4(),
        status=ToolStatus.ACTIVE
    )
    tool = await mcp_manager_fixture.create_tool(tool_data)
    
    # Create server manager
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9200
    )
    
    # Deploy the tool
    config = DeploymentConfig()
    deployment = await manager.deploy_server(tool.id, config)
    
    # Verify deployment record
    assert deployment is not None
    assert deployment.tool_id == tool.id
    assert deployment.status == DeploymentStatus.RUNNING
    assert deployment.endpoint_url.startswith("http://localhost:")
    assert deployment.deployed_at is not None
    
    # Clean up
    await manager.stop_server(deployment.id)


@pytest.mark.asyncio
async def test_deployment_stop(db_session, mcp_manager_fixture):
    """Test that stopping a deployment updates the status"""
    from app.schemas.mcp_tool import MCPToolCreate
    from app.models.mcp_tool import ToolStatus
    
    # Create a tool first
    tool_data = MCPToolCreate(
        name="Test Tool",
        slug="test-tool-stop",
        description="Test description",
        version="1.0.0",
        config={"test": "config"},
        author_id=uuid4(),
        status=ToolStatus.ACTIVE
    )
    tool = await mcp_manager_fixture.create_tool(tool_data)
    
    # Create server manager
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9200
    )
    
    # Deploy the tool
    config = DeploymentConfig()
    deployment = await manager.deploy_server(tool.id, config)
    
    # Stop the deployment
    result = await manager.stop_server(deployment.id)
    assert result is True
    
    # Verify status in database
    from sqlalchemy import select
    from app.models.deployment import MCPDeploymentModel
    
    stmt = select(MCPDeploymentModel).where(
        MCPDeploymentModel.id == str(deployment.id)
    )
    db_result = await db_session.execute(stmt)
    deployment_model = db_result.scalar_one_or_none()
    
    assert deployment_model is not None
    assert deployment_model.status == DeploymentStatus.STOPPED
    assert deployment_model.stopped_at is not None


@pytest.mark.asyncio
async def test_stop_nonexistent_deployment(db_session):
    """Test that stopping a nonexistent deployment returns False"""
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9200
    )
    
    # Try to stop a deployment that doesn't exist
    result = await manager.stop_server(uuid4())
    assert result is False


@pytest.mark.asyncio
async def test_endpoint_url_generation(db_session, mcp_manager_fixture):
    """Test that endpoint URLs are generated correctly"""
    from app.schemas.mcp_tool import MCPToolCreate
    from app.models.mcp_tool import ToolStatus
    
    # Create a tool
    tool_data = MCPToolCreate(
        name="Test Tool",
        slug="test-tool-endpoint",
        description="Test description",
        version="1.0.0",
        config={"test": "config"},
        author_id=uuid4(),
        status=ToolStatus.ACTIVE
    )
    tool = await mcp_manager_fixture.create_tool(tool_data)
    
    # Create server manager
    manager = MCPServerManager(
        db_session=db_session,
        base_url="http://localhost",
        port_range_start=9100,
        port_range_end=9200
    )
    
    # Deploy the tool
    config = DeploymentConfig()
    deployment = await manager.deploy_server(tool.id, config)
    
    # Verify endpoint URL format
    assert deployment.endpoint_url.startswith("http://localhost:")
    assert deployment.endpoint_url.endswith("/mcp/v1")
    
    # Extract port and verify it's in range
    port_str = deployment.endpoint_url.split(":")[2].split("/")[0]
    port = int(port_str)
    assert 9100 <= port <= 9200
    
    # Clean up
    await manager.stop_server(deployment.id)
