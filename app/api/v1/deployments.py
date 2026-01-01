"""Deployment Management API Endpoints"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.api.dependencies import require_permission
from app.api.v1.auth import get_current_user
from app.models.user import UserModel
from app.models.deployment import MCPDeploymentModel, DeploymentStatus
from app.schemas.deployment import (
    DeploymentCreate,
    Deployment,
    HealthCheckResult
)
from app.services.mcp_server_manager import MCPServerManager


router = APIRouter(prefix="/deployments", tags=["deployments"])


def get_mcp_server_manager(db: AsyncSession = Depends(get_db)) -> MCPServerManager:
    """Dependency to get MCP Server Manager instance"""
    return MCPServerManager(db_session=db)


@router.post(
    "",
    response_model=Deployment,
    status_code=status.HTTP_201_CREATED,
    summary="Deploy MCP Tool",
    description="Deploy an MCP tool as a running server instance"
)
@require_permission("deployments", "create")
async def deploy_mcp_tool(
    deployment_data: DeploymentCreate,
    current_user: UserModel = Depends(get_current_user),
    manager: MCPServerManager = Depends(get_mcp_server_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy an MCP tool.
    
    Creates a new deployment instance for the specified MCP tool,
    starts the server process, and returns deployment details.
    
    **Requirements: 5.1, 5.5**
    """
    try:
        deployment = await manager.deploy_server(
            tool_id=deployment_data.tool_id,
            config=deployment_data.config
        )
        await db.commit()
        return deployment
    except ValueError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy MCP tool: {str(e)}"
        )


@router.get(
    "/{deployment_id}",
    response_model=Deployment,
    summary="Get Deployment Status",
    description="Retrieve the status and details of a specific deployment"
)
@require_permission("deployments", "read")
async def get_deployment(
    deployment_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get deployment status.
    
    Retrieves detailed information about a specific deployment
    including its current status, health, and endpoint URL.
    
    **Requirements: 5.1, 5.5**
    """
    stmt = select(MCPDeploymentModel).where(
        MCPDeploymentModel.id == str(deployment_id)
    )
    result = await db.execute(stmt)
    deployment_model = result.scalar_one_or_none()
    
    if not deployment_model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deployment {deployment_id} not found"
        )
    
    return Deployment.model_validate(deployment_model)


@router.delete(
    "/{deployment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop Deployment",
    description="Stop a running MCP deployment"
)
@require_permission("deployments", "delete")
async def stop_deployment(
    deployment_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    manager: MCPServerManager = Depends(get_mcp_server_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Stop an MCP deployment.
    
    Gracefully shuts down the MCP server instance and updates
    the deployment status to stopped.
    
    **Requirements: 5.5**
    """
    try:
        success = await manager.stop_server(deployment_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found"
            )
        
        await db.commit()
        return None
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop deployment: {str(e)}"
        )


@router.get(
    "",
    response_model=List[Deployment],
    summary="List Deployments",
    description="List all deployments with optional filtering"
)
@require_permission("deployments", "read")
async def list_deployments(
    tool_id: Optional[UUID] = None,
    status_filter: Optional[DeploymentStatus] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    List deployments.
    
    Retrieves a list of all deployments with optional filtering
    by tool ID and deployment status.
    
    **Requirements: 5.1**
    """
    stmt = select(MCPDeploymentModel)
    
    # Apply filters
    if tool_id:
        stmt = stmt.where(MCPDeploymentModel.tool_id == str(tool_id))
    
    if status_filter:
        stmt = stmt.where(MCPDeploymentModel.status == status_filter)
    
    # Apply pagination
    stmt = stmt.limit(limit).offset(offset)
    
    result = await db.execute(stmt)
    deployments = result.scalars().all()
    
    return [Deployment.model_validate(d) for d in deployments]


@router.get(
    "/{deployment_id}/health",
    response_model=HealthCheckResult,
    summary="Check Deployment Health",
    description="Perform a health check on a deployment"
)
@require_permission("deployments", "read")
async def check_deployment_health(
    deployment_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    manager: MCPServerManager = Depends(get_mcp_server_manager),
    db: AsyncSession = Depends(get_db)
):
    """
    Check deployment health.
    
    Performs a health check on the deployed MCP server and
    returns the current health status.
    
    **Requirements: 5.4**
    """
    try:
        health_result = await manager.check_health(deployment_id)
        await db.commit()
        return health_result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
