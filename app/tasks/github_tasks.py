"""GitHub Integration Celery Tasks"""

import asyncio
import json
import re
from typing import Dict, Any, Optional
from datetime import datetime
from github import Github, GithubException

from app.core.celery_app import celery_app
from app.core.database import get_async_session, get_mongodb
from app.models.github_connection import GitHubConnectionModel
from app.models.mcp_tool import MCPToolModel
from sqlalchemy import select


def _parse_github_url(url: str) -> tuple[str, str]:
    """Parse owner and repo name from GitHub URL"""
    https_match = re.match(r'^https://github\.com/([\w-]+)/([\w.-]+)/?$', url)
    if https_match:
        owner, repo = https_match.groups()
        return owner, repo.rstrip('.git')
    
    ssh_match = re.match(r'^git@github\.com:([\w-]+)/([\w.-]+)\.git$', url)
    if ssh_match:
        return ssh_match.groups()
    
    raise ValueError(f"Cannot parse GitHub URL: {url}")


async def _sync_repository_async(
    connection_id: str,
    repository_url: str,
    access_token: str
) -> Dict[str, Any]:
    """
    Async implementation of repository synchronization.
    
    Fetches repository contents and updates tool configurations.
    """
    # Get database session
    async for session in get_async_session():
        try:
            # Fetch connection from database
            result = await session.execute(
                select(GitHubConnectionModel).where(
                    GitHubConnectionModel.id == connection_id
                )
            )
            connection = result.scalar_one_or_none()
            
            if not connection:
                return {
                    "connection_id": connection_id,
                    "status": "failed",
                    "message": f"Connection not found: {connection_id}",
                    "files_updated": 0
                }
            
            # Parse repository URL
            owner, repo_name = _parse_github_url(repository_url)
            
            # Authenticate with GitHub
            github_client = Github(access_token)
            repo = github_client.get_repo(f"{owner}/{repo_name}")
            
            # Get latest commit SHA
            default_branch = repo.default_branch
            latest_commit = repo.get_branch(default_branch).commit
            latest_sha = latest_commit.sha
            
            # Check if sync is needed
            if connection.last_sync_sha == latest_sha:
                return {
                    "connection_id": connection_id,
                    "status": "up_to_date",
                    "message": "Repository is already up to date",
                    "files_updated": 0,
                    "last_sync_sha": latest_sha
                }
            
            # Fetch MCP configuration files
            files_updated = 0
            config_data = None
            
            # Look for common MCP config file names
            config_filenames = [
                "mcp.json",
                "mcp-config.json",
                ".mcp/config.json",
                "config/mcp.json"
            ]
            
            for filename in config_filenames:
                try:
                    file_content = repo.get_contents(filename)
                    if not isinstance(file_content, list):
                        content = file_content.decoded_content.decode('utf-8')
                        config_data = json.loads(content)
                        files_updated += 1
                        break
                except GithubException:
                    continue
            
            # Update tool configuration if found and tool is associated
            if config_data and connection.tool_id:
                result = await session.execute(
                    select(MCPToolModel).where(
                        MCPToolModel.id == connection.tool_id
                    )
                )
                tool = result.scalar_one_or_none()
                
                if tool:
                    # Store old config in MongoDB history
                    mongo_db = get_mongodb()
                    history_collection = mongo_db["mcp_config_history"]
                    
                    history_doc = {
                        "tool_id": tool.id,
                        "version": tool.version,
                        "config": config_data,
                        "changed_by": connection.user_id,
                        "changed_at": datetime.utcnow(),
                        "change_type": "github_sync",
                        "sync_sha": latest_sha
                    }
                    
                    await history_collection.insert_one(history_doc)
                    
                    # Update tool version if specified in config
                    if "version" in config_data:
                        tool.version = config_data["version"]
                    
                    tool.updated_at = datetime.utcnow()
            
            # Update connection sync status
            connection.last_sync_sha = latest_sha
            connection.last_sync_at = datetime.utcnow()
            
            await session.commit()
            
            return {
                "connection_id": connection_id,
                "status": "success",
                "message": f"Successfully synced repository from commit {latest_sha[:7]}",
                "files_updated": files_updated,
                "last_sync_sha": latest_sha
            }
            
        except GithubException as e:
            await session.rollback()
            return {
                "connection_id": connection_id,
                "status": "failed",
                "message": f"GitHub API error: {e.data.get('message', str(e))}",
                "files_updated": 0
            }
        except Exception as e:
            await session.rollback()
            return {
                "connection_id": connection_id,
                "status": "failed",
                "message": f"Sync error: {str(e)}",
                "files_updated": 0
            }
        finally:
            await session.close()


@celery_app.task(
    bind=True,
    name="app.tasks.github_tasks.sync_repository",
    max_retries=3,
    default_retry_delay=120
)
def sync_repository_task(
    self,
    connection_id: str,
    repository_url: str,
    access_token: str
) -> Dict[str, Any]:
    """
    Celery task for GitHub repository synchronization.
    
    This task runs asynchronously to fetch repository contents
    and update tool configurations from GitHub.
    
    Args:
        connection_id: GitHub connection identifier
        repository_url: Repository URL to sync
        access_token: GitHub access token
    
    Returns:
        Sync result with status and updated files count
    
    Retry Strategy:
        - Max retries: 3
        - Exponential backoff: 120s * (2 ** retry_count)
    
    Validates: Requirements 4.2, 9.2
    """
    try:
        # Run async sync logic
        result = asyncio.run(
            _sync_repository_async(connection_id, repository_url, access_token)
        )
        
        # Retry on failure
        if result["status"] == "failed":
            countdown = 120 * (2 ** self.request.retries)
            raise self.retry(
                exc=Exception(result["message"]),
                countdown=countdown
            )
        
        return result
        
    except Exception as exc:
        # Retry with exponential backoff
        countdown = 120 * (2 ** self.request.retries)
        raise self.retry(exc=exc, countdown=countdown)
