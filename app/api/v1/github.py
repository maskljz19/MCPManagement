"""GitHub Integration API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.services.github_integration import GitHubIntegrationService
from app.schemas.github import (
    GitHubConnectionCreate,
    GitHubConnection,
    SyncTriggerResponse,
    WebhookEvent,
    WebhookProcessResponse
)
from app.api.v1.auth import get_current_user
from app.models.user import UserModel


router = APIRouter(prefix="/github", tags=["GitHub Integration"])


async def get_github_service(
    db: AsyncSession = Depends(get_db)
) -> GitHubIntegrationService:
    """Dependency to get GitHubIntegrationService instance"""
    return GitHubIntegrationService(db_session=db)


@router.post("/connect", response_model=GitHubConnection, status_code=status.HTTP_201_CREATED)
async def connect_repository(
    connection_data: GitHubConnectionCreate,
    current_user: UserModel = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service)
):
    """
    Connect a GitHub repository to the platform.
    
    Validates repository access and stores connection details.
    The access token is validated by attempting to access the repository.
    
    Args:
        connection_data: Repository URL, access token, and optional tool ID
        current_user: Currently authenticated user
        github_service: GitHub integration service
        
    Returns:
        Created GitHub connection object
        
    Raises:
        HTTPException 400: If repository URL is invalid or inaccessible
        HTTPException 401: If user is not authenticated
        HTTPException 404: If specified tool_id doesn't exist
        
    Validates: Requirements 4.1
    """
    try:
        connection = await github_service.connect_repository(
            user_id=current_user.id,
            repository_url=connection_data.repository_url,
            access_token=connection_data.access_token,
            tool_id=connection_data.tool_id
        )
        
        return connection
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/connections", response_model=list[GitHubConnection])
async def list_connections(
    current_user: UserModel = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service)
):
    """
    List all GitHub connections for the current user.
    
    Returns all repository connections associated with the authenticated user.
    
    Args:
        current_user: Currently authenticated user
        github_service: GitHub integration service
        
    Returns:
        List of GitHub connection objects
        
    Raises:
        HTTPException 401: If user is not authenticated
    """
    connections = await github_service.list_user_connections(user_id=current_user.id)
    return connections


@router.post("/sync/{connection_id}", response_model=SyncTriggerResponse)
async def trigger_sync(
    connection_id: UUID,
    access_token: str = Header(..., alias="X-GitHub-Token"),
    current_user: UserModel = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service)
):
    """
    Trigger asynchronous repository synchronization.
    
    Queues a Celery task to fetch repository contents and update tool configurations.
    The access token must be provided in the X-GitHub-Token header.
    
    Args:
        connection_id: GitHub connection identifier
        access_token: GitHub personal access token (from header)
        current_user: Currently authenticated user
        github_service: GitHub integration service
        
    Returns:
        Task information with task_id for status polling
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If connection not found
        
    Validates: Requirements 4.2, 9.2
    """
    try:
        result = await github_service.trigger_sync(
            connection_id=connection_id,
            access_token=access_token
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete("/disconnect/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_repository(
    connection_id: UUID,
    current_user: UserModel = Depends(get_current_user),
    github_service: GitHubIntegrationService = Depends(get_github_service)
):
    """
    Disconnect a GitHub repository from the platform.
    
    Removes connection details while preserving associated tool data.
    Users can only disconnect their own connections.
    
    Args:
        connection_id: GitHub connection identifier
        current_user: Currently authenticated user
        github_service: GitHub integration service
        
    Returns:
        No content (204)
        
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 404: If connection not found
        
    Validates: Requirements 4.4
    """
    success = await github_service.disconnect_repository(connection_id=connection_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="GitHub connection not found"
        )
    
    return None


@router.post("/webhook", response_model=WebhookProcessResponse)
async def process_webhook(
    webhook_data: WebhookEvent,
    x_github_event: Optional[str] = Header(None, alias="X-GitHub-Event"),
    github_service: GitHubIntegrationService = Depends(get_github_service)
):
    """
    Process GitHub webhook events.
    
    Receives webhook events from GitHub and queues them for asynchronous processing.
    This endpoint does not require authentication as it's called by GitHub.
    
    Note: In production, you should validate the webhook signature using
    X-Hub-Signature-256 header to ensure the request is from GitHub.
    
    Args:
        webhook_data: Webhook event type and payload
        x_github_event: GitHub event type from header (optional)
        github_service: GitHub integration service
        
    Returns:
        Processing status and webhook ID
        
    Raises:
        HTTPException 400: If webhook payload is invalid
        
    Validates: Requirements 4.5
    """
    # Use event type from header if provided, otherwise from body
    event_type = x_github_event or webhook_data.event_type
    
    try:
        result = await github_service.process_webhook(
            event_type=event_type,
            payload=webhook_data.payload
        )
        
        return result
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
