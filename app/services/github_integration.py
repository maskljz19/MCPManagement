"""GitHub Integration Service"""

import re
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from github import Github, GithubException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.github_connection import GitHubConnectionModel
from app.models.mcp_tool import MCPToolModel
from app.core.database import get_mongodb
from app.tasks.github_tasks import sync_repository_task


class GitHubIntegrationService:
    """
    Service for GitHub repository integration.
    
    Handles repository connections, synchronization, and webhook processing.
    Validates: Requirements 4.1, 4.2, 4.4, 4.5
    """
    
    def __init__(self, db_session: AsyncSession):
        """
        Initialize GitHub integration service.
        
        Args:
            db_session: Async SQLAlchemy session for database operations
        """
        self.db_session = db_session
    
    async def connect_repository(
        self,
        user_id: UUID,
        repository_url: str,
        access_token: str,
        tool_id: Optional[UUID] = None
    ) -> GitHubConnectionModel:
        """
        Connect a GitHub repository to the platform.
        
        Validates repository access and stores connection details in MySQL.
        
        Args:
            user_id: User creating the connection
            repository_url: GitHub repository URL
            access_token: GitHub personal access token
            tool_id: Optional MCP tool to associate with this repository
        
        Returns:
            GitHubConnectionModel with connection details
        
        Raises:
            ValueError: If repository URL is invalid or inaccessible
            GithubException: If GitHub API authentication fails
        
        Validates: Requirements 4.1
        """
        # Validate repository URL format
        if not self._is_valid_github_url(repository_url):
            raise ValueError(f"Invalid GitHub repository URL: {repository_url}")
        
        # Extract owner and repo name from URL
        owner, repo_name = self._parse_github_url(repository_url)
        
        # Validate GitHub access
        try:
            github_client = Github(access_token)
            repo = github_client.get_repo(f"{owner}/{repo_name}")
            
            # Test access by fetching basic repo info
            _ = repo.name
            _ = repo.default_branch
            
        except GithubException as e:
            if e.status == 401:
                raise ValueError("Invalid GitHub access token")
            elif e.status == 404:
                raise ValueError(f"Repository not found or not accessible: {repository_url}")
            else:
                raise ValueError(f"GitHub API error: {e.data.get('message', str(e))}")
        
        # Validate tool_id exists if provided
        if tool_id:
            result = await self.db_session.execute(
                select(MCPToolModel).where(MCPToolModel.id == str(tool_id))
            )
            tool = result.scalar_one_or_none()
            if not tool:
                raise ValueError(f"MCP tool not found: {tool_id}")
        
        # Create connection record
        connection = GitHubConnectionModel(
            id=str(uuid4()),
            user_id=str(user_id),
            tool_id=str(tool_id) if tool_id else None,
            repository_url=repository_url,
            last_sync_sha=None,
            last_sync_at=None
        )
        
        self.db_session.add(connection)
        await self.db_session.commit()
        await self.db_session.refresh(connection)
        
        return connection
    
    async def disconnect_repository(
        self,
        connection_id: UUID
    ) -> bool:
        """
        Disconnect a GitHub repository from the platform.
        
        Removes connection details while preserving associated tool data.
        
        Args:
            connection_id: GitHub connection identifier
        
        Returns:
            True if disconnection successful, False if connection not found
        
        Validates: Requirements 4.4
        """
        # Fetch connection
        result = await self.db_session.execute(
            select(GitHubConnectionModel).where(
                GitHubConnectionModel.id == str(connection_id)
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            return False
        
        # Delete connection (tool data is preserved due to SET NULL on FK)
        await self.db_session.delete(connection)
        await self.db_session.commit()
        
        return True
    
    async def trigger_sync(
        self,
        connection_id: UUID,
        access_token: str
    ) -> Dict[str, Any]:
        """
        Trigger asynchronous repository synchronization.
        
        Queues a Celery task to fetch repository contents and update tool configurations.
        
        Args:
            connection_id: GitHub connection identifier
            access_token: GitHub personal access token
        
        Returns:
            Dict with task_id and status
        
        Raises:
            ValueError: If connection not found
        
        Validates: Requirements 4.2, 9.2
        """
        # Fetch connection
        result = await self.db_session.execute(
            select(GitHubConnectionModel).where(
                GitHubConnectionModel.id == str(connection_id)
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            raise ValueError(f"GitHub connection not found: {connection_id}")
        
        # Queue sync task
        task = sync_repository_task.delay(
            connection_id=str(connection_id),
            repository_url=connection.repository_url,
            access_token=access_token
        )
        
        return {
            "task_id": task.id,
            "status": "queued",
            "connection_id": str(connection_id)
        }
    
    async def process_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process GitHub webhook events.
        
        Queues webhook events for asynchronous processing.
        
        Args:
            event_type: GitHub event type (push, pull_request, etc.)
            payload: Webhook payload from GitHub
        
        Returns:
            Dict with processing status
        
        Validates: Requirements 4.5
        """
        # Extract repository URL from payload
        repository_url = payload.get("repository", {}).get("html_url")
        
        if not repository_url:
            raise ValueError("Invalid webhook payload: missing repository URL")
        
        # Find matching connection
        result = await self.db_session.execute(
            select(GitHubConnectionModel).where(
                GitHubConnectionModel.repository_url == repository_url
            )
        )
        connection = result.scalar_one_or_none()
        
        if not connection:
            return {
                "status": "ignored",
                "reason": "No connection found for repository"
            }
        
        # Store webhook event in MongoDB for async processing
        mongo_db = get_mongodb()
        webhook_collection = mongo_db["github_webhooks"]
        
        webhook_doc = {
            "connection_id": connection.id,
            "event_type": event_type,
            "payload": payload,
            "processed": False,
            "created_at": datetime.utcnow()
        }
        
        result = await webhook_collection.insert_one(webhook_doc)
        
        # TODO: Queue webhook processing task when implemented
        # For now, just store the event
        
        return {
            "status": "queued",
            "webhook_id": str(result.inserted_id),
            "connection_id": connection.id
        }
    
    def _is_valid_github_url(self, url: str) -> bool:
        """
        Validate GitHub repository URL format.
        
        Args:
            url: Repository URL to validate
        
        Returns:
            True if valid GitHub URL, False otherwise
        """
        patterns = [
            r'^https://github\.com/[\w-]+/[\w.-]+/?$',
            r'^git@github\.com:[\w-]+/[\w.-]+\.git$'
        ]
        
        return any(re.match(pattern, url) for pattern in patterns)
    
    def _parse_github_url(self, url: str) -> tuple[str, str]:
        """
        Parse owner and repository name from GitHub URL.
        
        Args:
            url: GitHub repository URL
        
        Returns:
            Tuple of (owner, repo_name)
        
        Raises:
            ValueError: If URL cannot be parsed
        """
        # HTTPS URL pattern
        https_match = re.match(r'^https://github\.com/([\w-]+)/([\w.-]+)/?$', url)
        if https_match:
            owner, repo = https_match.groups()
            return owner, repo.rstrip('.git')
        
        # SSH URL pattern
        ssh_match = re.match(r'^git@github\.com:([\w-]+)/([\w.-]+)\.git$', url)
        if ssh_match:
            return ssh_match.groups()
        
        raise ValueError(f"Cannot parse GitHub URL: {url}")
