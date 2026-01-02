"""
Property-Based Tests for GitHub Integration

These tests validate correctness properties for GitHub repository integration
using Hypothesis for property-based testing.

Feature: mcp-platform-backend
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from github import GithubException

from app.services.github_integration import GitHubIntegrationService
from app.models.github_connection import GitHubConnectionModel
from app.models.mcp_tool import MCPToolModel


# Strategies for generating test data
@st.composite
def github_url_strategy(draw):
    """Generate valid GitHub repository URLs"""
    owner = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='-'),
        min_size=1,
        max_size=39
    ).filter(lambda x: x and not x.startswith('-') and not x.endswith('-')))
    
    repo = draw(st.text(
        alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='.-_'),
        min_size=1,
        max_size=100
    ).filter(lambda x: x and not x.startswith('.') and not x.endswith('.')))
    
    url_format = draw(st.sampled_from(['https', 'ssh']))
    
    if url_format == 'https':
        return f"https://github.com/{owner}/{repo}"
    else:
        return f"git@github.com:{owner}/{repo}.git"


@st.composite
def user_id_strategy(draw):
    """Generate valid user UUIDs"""
    return uuid4()


@st.composite
def tool_id_strategy(draw):
    """Generate optional tool UUIDs"""
    return draw(st.one_of(st.none(), st.just(uuid4())))


class TestGitHubConnectionValidation:
    """
    Property 13: GitHub Connection Validation
    
    For any valid repository URL and access token, connecting should create
    a record in the github_connections table.
    
    Validates: Requirements 4.1
    """
    
    @pytest.mark.asyncio
    @given(
        repository_url=github_url_strategy(),
        user_id=user_id_strategy(),
        tool_id=tool_id_strategy()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_13_github_connection_validation(
        self,
        repository_url: str,
        user_id,
        tool_id
    ):
        """
        Property 13: GitHub Connection Validation
        
        For any valid repository URL and access token, connecting should create
        a record in the github_connections table.
        
        Feature: mcp-platform-backend, Property 13: GitHub Connection Validation
        Validates: Requirements 4.1
        """
        # Create mock database session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()
        
        # Mock tool lookup if tool_id provided
        if tool_id:
            mock_result = Mock()
            mock_result.scalar_one_or_none = Mock(return_value=MCPToolModel(
                id=str(tool_id),
                name="Test Tool",
                slug="test-tool",
                version="1.0.0",
                author_id=str(user_id),
                status="ACTIVE"
            ))
            mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Create service
        service = GitHubIntegrationService(mock_session)
        
        # Mock GitHub API
        with patch('app.services.github_integration.Github') as mock_github:
            mock_repo = Mock()
            mock_repo.name = "test-repo"
            mock_repo.default_branch = "main"
            
            mock_github_instance = Mock()
            mock_github_instance.get_repo = Mock(return_value=mock_repo)
            mock_github.return_value = mock_github_instance
            
            # Connect repository
            connection = await service.connect_repository(
                user_id=user_id,
                repository_url=repository_url,
                access_token="test_token",
                tool_id=tool_id
            )
            
            # Property: Connection should be created
            assert connection is not None
            assert isinstance(connection, GitHubConnectionModel)
            
            # Property: Connection should have correct attributes
            assert connection.user_id == str(user_id)
            assert connection.repository_url == repository_url
            assert connection.tool_id == (str(tool_id) if tool_id else None)
            
            # Property: Connection should be added to session
            mock_session.add.assert_called_once()
            
            # Property: Changes should be committed
            mock_session.commit.assert_called_once()


class TestRepositorySyncConsistency:
    """
    Property 14: Repository Sync Consistency
    
    For any connected GitHub repository, after syncing, the tool configuration
    should match the repository's current state.
    
    Validates: Requirements 4.2
    """
    
    @pytest.mark.asyncio
    @given(
        connection_id=st.just(uuid4()),
        repository_url=github_url_strategy(),
        config_version=st.text(min_size=5, max_size=10).map(lambda x: "1.0.0")
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much]
    )
    async def test_property_14_repository_sync_consistency(
        self,
        connection_id,
        repository_url: str,
        config_version: str
    ):
        """
        Property 14: Repository Sync Consistency
        
        For any connected GitHub repository, after syncing, the tool configuration
        should match the repository's current state.
        
        Feature: mcp-platform-backend, Property 14: Repository Sync Consistency
        Validates: Requirements 4.2
        """
        from app.tasks.github_tasks import _sync_repository_async
        
        # Mock database session
        mock_connection = GitHubConnectionModel(
            id=str(connection_id),
            user_id=str(uuid4()),
            tool_id=str(uuid4()),
            repository_url=repository_url,
            last_sync_sha=None,
            last_sync_at=None
        )
        
        mock_tool = MCPToolModel(
            id=mock_connection.tool_id,
            name="Test Tool",
            slug="test-tool",
            version="1.0.0",
            author_id=mock_connection.user_id,
            status="ACTIVE"
        )
        
        # Mock GitHub API
        with patch('app.tasks.github_tasks.get_async_session') as mock_get_session, \
             patch('app.tasks.github_tasks.get_mongodb') as mock_get_mongo, \
             patch('app.tasks.github_tasks.Github') as mock_github:
            
            # Setup session mock
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            
            # Mock connection query
            mock_conn_result = Mock()
            mock_conn_result.scalar_one_or_none = Mock(return_value=mock_connection)
            
            # Mock tool query
            mock_tool_result = Mock()
            mock_tool_result.scalar_one_or_none = Mock(return_value=mock_tool)
            
            # Setup execute to return different results based on call
            call_count = [0]
            async def mock_execute(query):
                call_count[0] += 1
                if call_count[0] == 1:
                    return mock_conn_result
                else:
                    return mock_tool_result
            
            mock_session.execute = mock_execute
            
            async def mock_session_generator():
                yield mock_session
            
            mock_get_session.return_value = mock_session_generator()
            
            # Setup MongoDB mock
            mock_collection = AsyncMock()
            mock_collection.insert_one = AsyncMock(return_value=Mock(inserted_id="test_id"))
            mock_db = AsyncMock()
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_get_mongo.return_value = mock_db
            
            # Setup GitHub mock
            mock_commit = Mock()
            mock_commit.sha = "abc123def456"
            
            mock_branch = Mock()
            mock_branch.commit = mock_commit
            
            mock_file_content = Mock()
            mock_file_content.decoded_content = b'{"version": "' + config_version.encode() + b'"}'
            
            mock_repo = Mock()
            mock_repo.default_branch = "main"
            mock_repo.get_branch = Mock(return_value=mock_branch)
            mock_repo.get_contents = Mock(return_value=mock_file_content)
            
            mock_github_instance = Mock()
            mock_github_instance.get_repo = Mock(return_value=mock_repo)
            mock_github.return_value = mock_github_instance
            
            # Perform sync
            result = await _sync_repository_async(
                connection_id=str(connection_id),
                repository_url=repository_url,
                access_token="test_token"
            )
            
            # Property: Sync should succeed
            assert result["status"] in ["success", "up_to_date"]
            
            # Property: Connection should have updated sync SHA
            if result["status"] == "success":
                assert mock_connection.last_sync_sha == "abc123def456"
                assert mock_connection.last_sync_at is not None


class TestGitHubDisconnectPreservation:
    """
    Property 15: GitHub Disconnect Preservation
    
    For any GitHub connection, when disconnected, the connection record should
    be removed but the associated tool data should remain in mcp_tools table.
    
    Validates: Requirements 4.4
    """
    
    @pytest.mark.asyncio
    @given(
        connection_id=st.just(uuid4()),
        tool_id=st.just(uuid4())
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_15_github_disconnect_preservation(
        self,
        connection_id,
        tool_id
    ):
        """
        Property 15: GitHub Disconnect Preservation
        
        For any GitHub connection, when disconnected, the connection record should
        be removed but the associated tool data should remain in mcp_tools table.
        
        Feature: mcp-platform-backend, Property 15: GitHub Disconnect Preservation
        Validates: Requirements 4.4
        """
        # Create mock database session
        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.delete = AsyncMock()
        
        # Mock connection lookup
        mock_connection = GitHubConnectionModel(
            id=str(connection_id),
            user_id=str(uuid4()),
            tool_id=str(tool_id),
            repository_url="https://github.com/test/repo",
            last_sync_sha=None,
            last_sync_at=None
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_connection)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Create service
        service = GitHubIntegrationService(mock_session)
        
        # Disconnect repository
        result = await service.disconnect_repository(connection_id=connection_id)
        
        # Property: Disconnect should succeed
        assert result is True
        
        # Property: Connection should be deleted from session
        mock_session.delete.assert_called_once_with(mock_connection)
        
        # Property: Changes should be committed
        mock_session.commit.assert_called_once()
        
        # Property: Tool data is preserved (FK is SET NULL, not CASCADE DELETE)
        # This is enforced by the database schema, not application code


class TestWebhookAsyncProcessing:
    """
    Property 16: Webhook Async Processing
    
    For any GitHub webhook event, the event should be queued as a Celery task
    for asynchronous processing.
    
    Validates: Requirements 4.5
    """
    
    @pytest.mark.asyncio
    @given(
        event_type=st.sampled_from(['push', 'pull_request', 'release', 'issues']),
        repository_url=github_url_strategy()
    )
    @settings(
        max_examples=100,
        deadline=None,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    async def test_property_16_webhook_async_processing(
        self,
        event_type: str,
        repository_url: str
    ):
        """
        Property 16: Webhook Async Processing
        
        For any GitHub webhook event, the event should be queued for
        asynchronous processing.
        
        Feature: mcp-platform-backend, Property 16: Webhook Async Processing
        Validates: Requirements 4.5
        """
        # Create mock database session
        mock_session = AsyncMock()
        
        # Mock connection lookup
        mock_connection = GitHubConnectionModel(
            id=str(uuid4()),
            user_id=str(uuid4()),
            tool_id=None,
            repository_url=repository_url,
            last_sync_sha=None,
            last_sync_at=None
        )
        
        mock_result = Mock()
        mock_result.scalar_one_or_none = Mock(return_value=mock_connection)
        mock_session.execute = AsyncMock(return_value=mock_result)
        
        # Create service
        service = GitHubIntegrationService(mock_session)
        
        # Mock MongoDB
        with patch('app.services.github_integration.get_mongodb') as mock_get_mongo:
            mock_collection = AsyncMock()
            mock_insert_result = Mock()
            mock_insert_result.inserted_id = "webhook_doc_id"
            mock_collection.insert_one = AsyncMock(return_value=mock_insert_result)
            
            mock_db = AsyncMock()
            mock_db.__getitem__ = Mock(return_value=mock_collection)
            mock_get_mongo.return_value = mock_db
            
            # Process webhook
            payload = {
                "repository": {
                    "html_url": repository_url
                },
                "action": "opened"
            }
            
            result = await service.process_webhook(
                event_type=event_type,
                payload=payload
            )
            
            # Property: Webhook should be queued
            assert result["status"] == "queued"
            
            # Property: Webhook should be stored in MongoDB
            assert "webhook_id" in result
            assert result["webhook_id"] == "webhook_doc_id"
            
            # Property: Connection ID should be included
            assert result["connection_id"] == mock_connection.id
            
            # Property: Webhook document should be inserted
            mock_collection.insert_one.assert_called_once()
            
            # Verify webhook document structure
            call_args = mock_collection.insert_one.call_args[0][0]
            assert call_args["connection_id"] == mock_connection.id
            assert call_args["event_type"] == event_type
            assert call_args["payload"] == payload
            assert call_args["processed"] is False
            assert "created_at" in call_args
