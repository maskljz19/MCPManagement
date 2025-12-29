# Implementation Plan: MCP Platform Backend

## Overview

This implementation plan breaks down the MCP Platform Backend into incremental, testable steps. The approach follows a bottom-up strategy: starting with core infrastructure (database connections, models), then building business logic components, followed by API endpoints, and finally integration features. Each major component includes property-based tests to validate correctness properties from the design document.

## Tasks

- [x] 1. Project Setup and Infrastructure
  - Create project directory structure following best practices
  - Set up Python virtual environment with Python 3.11+
  - Create requirements.txt with all dependencies (FastAPI, SQLAlchemy, Motor, Celery, etc.)
  - Create .env.example file with all required environment variables
  - Set up basic FastAPI application with health check endpoint
  - _Requirements: 14.1, 14.2, 14.4_

- [x] 1.1 Write unit test for health check endpoint
  - Test health check returns 200 when all services are healthy
  - Test health check returns 503 when any service is unavailable
  - _Requirements: 12.3, 14.4_

- [-] 2. Database Configuration and Models
  - [x] 2.1 Configure MySQL connection with SQLAlchemy async
    - Create async engine with asyncpg/aiomysql driver
    - Implement async session factory with dependency injection
    - Add connection pooling configuration
    - _Requirements: 7.1, 14.4_

  - [x] 2.2 Configure MongoDB connection with Motor
    - Create async MongoDB client
    - Implement database and collection accessors
    - _Requirements: 7.2_

  - [x] 2.3 Configure Redis connection with aioredis
    - Create async Redis client
    - Implement connection retry logic
    - _Requirements: 8.1, 8.3_

  - [x] 2.4 Configure Qdrant vector database client
    - Create Qdrant client with async support
    - Create collection for document embeddings
    - _Requirements: 2.1_

  - [x] 2.5 Write property test for database connections
    - **Property 32: Cache Fallback on Failure**
    - **Validates: Requirements 8.4**

- [x] 3. SQLAlchemy Models and Alembic Migrations
  - [x] 3.1 Define SQLAlchemy models for all MySQL tables
    - Create Base model with common fields (id, created_at, updated_at)
    - Implement MCPToolModel with relationships
    - Implement MCPDeploymentModel
    - Implement MCPUsageStatModel
    - Implement UserModel with password hashing
    - Implement APIKeyModel
    - Implement GitHubConnectionModel
    - _Requirements: 7.1, 7.3_

  - [x] 3.2 Set up Alembic for database migrations
    - Initialize Alembic configuration
    - Create initial migration for all tables
    - Add migration helper scripts
    - _Requirements: 15.1, 15.2_

  - [x] 3.3 Write property test for migration execution
    - **Property 51: Migration Execution Order**
    - **Validates: Requirements 15.2**

  - [x] 3.4 Write property test for migration rollback
    - **Property 52: Migration Rollback on Failure**
    - **Validates: Requirements 15.3**

  - [x] 3.5 Write property test for migration downgrade
    - **Property 53: Migration Downgrade Support**
    - **Validates: Requirements 15.5**

- [x] 4. Pydantic Models and Validation
  - Create Pydantic models for all API request/response schemas
  - Implement MCPToolCreate, MCPToolUpdate, MCPTool schemas
  - Implement DocumentCreate, Document, SearchResult schemas
  - Implement FeasibilityReport, Improvement, ConfigRequirements schemas
  - Implement User, Token, APIKey schemas
  - Add custom validators for complex fields (slug pattern, version format)
  - _Requirements: 10.2, 11.1_

- [x] 4.1 Write property test for input validation
  - **Property 35: Input Validation Rejection**
  - **Validates: Requirements 10.2, 11.1**

- [x] 4.2 Write property test for validation error details
  - **Property 36: Validation Error Detail**
  - **Validates: Requirements 10.3**

- [x] 5. Authentication Service Implementation
  - [x] 5.1 Implement password hashing with passlib
    - Create password hashing utilities
    - Implement password verification
    - _Requirements: 6.1_

  - [x] 5.2 Implement JWT token generation and validation
    - Create JWT token generation with claims
    - Implement token verification and decoding
    - Add refresh token support
    - _Requirements: 6.1, 6.2, 6.3_

  - [x] 5.3 Implement API key authentication
    - Create API key generation with secure hashing
    - Implement API key verification
    - _Requirements: 6.5_

  - [x] 5.4 Implement RBAC permission checking
    - Define role-permission mappings
    - Create permission checking function
    - _Requirements: 6.4_

  - [x] 5.5 Write property test for JWT token claims
    - **Property 20: JWT Token Claims Completeness**
    - **Validates: Requirements 6.1**

  - [x] 5.6 Write property test for JWT round-trip validation
    - **Property 21: JWT Token Round-Trip Validation**
    - **Validates: Requirements 6.2**

  - [x] 5.7 Write property test for expired token rejection
    - **Property 22: Expired Token Rejection**
    - **Validates: Requirements 6.3**

  - [x] 5.8 Write property test for authorization checks
    - **Property 23: Authorization Permission Check**
    - **Validates: Requirements 6.4**

  - [x] 5.9 Write property test for API key authentication
    - **Property 24: API Key Authentication**
    - **Validates: Requirements 6.5**

- [x] 6. Checkpoint - Verify authentication and database setup
  - Ensure all tests pass, ask the user if questions arise.

- [-] 7. MCP Manager Component
  - [x] 7.1 Implement MCP tool CRUD operations
    - Create create_tool method with MySQL insert
    - Create get_tool method with caching
    - Create update_tool method with version history
    - Create delete_tool method with soft delete
    - Create list_tools method with pagination
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 7.2 Implement version history management
    - Create MongoDB history append on updates
    - Create get_tool_history method
    - _Requirements: 7.2, 7.5_

  - [ ] 7.3 Write property test for tool creation persistence
    - **Property 1: MCP Tool Creation Persistence**
    - **Validates: Requirements 1.1, 1.2**

  - [ ] 7.4 Write property test for version history on update
    - **Property 2: Version History on Update**
    - **Validates: Requirements 1.3**

  - [ ] 7.5 Write property test for soft delete preservation
    - **Property 3: Soft Delete Preservation**
    - **Validates: Requirements 1.4**

  - [ ] 7.6 Write property test for pagination invariants
    - **Property 4: Pagination Invariants**
    - **Validates: Requirements 1.5**

  - [ ] 7.7 Write property test for state persistence
    - **Property 25: State Persistence in MySQL**
    - **Validates: Requirements 7.1, 7.3**

  - [ ] 7.8 Write property test for configuration history append
    - **Property 26: Configuration History Append**
    - **Validates: Requirements 7.2**

  - [ ] 7.9 Write property test for version history retrieval
    - **Property 28: Version History Retrieval**
    - **Validates: Requirements 7.5**

- [ ] 8. Cache Layer Implementation
  - [ ] 8.1 Implement Redis caching for MCP tools
    - Create cache key generation utilities
    - Implement cache get/set/delete operations
    - Add cache invalidation on updates
    - _Requirements: 8.1, 8.2_

  - [ ] 8.2 Implement session management in Redis
    - Create session storage with TTL
    - Implement session retrieval and deletion
    - _Requirements: 8.3_

  - [ ] 8.3 Write property test for cache hit on repeated access
    - **Property 29: Cache Hit on Repeated Access**
    - **Validates: Requirements 8.1**

  - [ ] 8.4 Write property test for cache invalidation
    - **Property 30: Cache Invalidation on Update**
    - **Validates: Requirements 8.2**

  - [ ] 8.5 Write property test for session storage with TTL
    - **Property 31: Session Storage with TTL**
    - **Validates: Requirements 8.3**

- [ ] 9. Knowledge Base Service
  - [ ] 9.1 Implement document storage in MongoDB
    - Create store_document method
    - Create get_document method
    - Create delete_document method
    - _Requirements: 2.1, 2.3, 2.4_

  - [ ] 9.2 Implement embedding generation with LangChain
    - Set up OpenAI embeddings integration
    - Create generate_embeddings method
    - Implement batch embedding generation
    - _Requirements: 2.1, 2.5_

  - [ ] 9.3 Implement vector storage in Qdrant
    - Create vector insertion with metadata
    - Implement vector deletion
    - _Requirements: 2.1, 2.4_

  - [ ] 9.4 Implement semantic search
    - Create search_documents method with vector similarity
    - Implement result ranking and filtering
    - Add metadata-based post-filtering
    - _Requirements: 2.2_

  - [ ] 9.5 Write property test for dual-store consistency
    - **Property 5: Dual-Store Document Consistency**
    - **Validates: Requirements 2.1**

  - [ ] 9.6 Write property test for search result ordering
    - **Property 6: Search Result Ordering**
    - **Validates: Requirements 2.2**

  - [ ] 9.7 Write property test for document deletion consistency
    - **Property 7: Document Deletion Consistency**
    - **Validates: Requirements 2.4**

  - [ ] 9.8 Write property test for embedding dimension consistency
    - **Property 8: Embedding Dimension Consistency**
    - **Validates: Requirements 2.5**

- [ ] 10. Checkpoint - Verify core services
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. AI Analyzer Component
  - [ ] 11.1 Set up LangChain with OpenAI integration
    - Configure ChatOpenAI client
    - Create prompt templates for analysis tasks
    - Set up Pydantic output parsers
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ] 11.2 Implement feasibility analysis
    - Create analyze_feasibility method
    - Build feasibility analysis prompt
    - Parse and validate response
    - _Requirements: 3.1_

  - [ ] 11.3 Implement improvement suggestions
    - Create suggest_improvements method
    - Build improvement suggestion prompt
    - _Requirements: 3.2_

  - [ ] 11.4 Implement auto-configuration generation
    - Create generate_config method
    - Build configuration generation prompt
    - Validate generated configuration
    - _Requirements: 3.3_

  - [ ] 11.5 Implement result persistence in MongoDB
    - Store analysis results with task_id
    - Add TTL index for auto-cleanup
    - _Requirements: 3.5_

  - [ ] 11.6 Write property test for analysis response completeness
    - **Property 9: AI Analysis Response Completeness**
    - **Validates: Requirements 3.1**

  - [ ] 11.7 Write property test for improvement suggestions
    - **Property 10: Improvement Suggestions Non-Empty**
    - **Validates: Requirements 3.2**

  - [ ] 11.8 Write property test for generated config validity
    - **Property 11: Generated Configuration Validity**
    - **Validates: Requirements 3.3**

  - [ ] 11.9 Write property test for analysis result persistence
    - **Property 12: Analysis Result Persistence**
    - **Validates: Requirements 3.5**

- [ ] 12. Celery Task Queue Setup
  - [ ] 12.1 Configure Celery with RabbitMQ broker
    - Create Celery app configuration
    - Set up RabbitMQ connection
    - Configure Redis as result backend
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ] 12.2 Implement async task definitions
    - Create AI analysis task
    - Create GitHub sync task
    - Create embedding generation task
    - Add task retry logic with exponential backoff
    - _Requirements: 9.1, 9.2, 9.3_

  - [ ] 12.3 Implement task status tracking
    - Store task status in Redis
    - Create task status query endpoint
    - _Requirements: 9.4_

  - [ ] 12.4 Write property test for async task queuing
    - **Property 33: Async Task Queuing**
    - **Validates: Requirements 9.1, 9.2, 9.3**

  - [ ] 12.5 Write property test for task status update
    - **Property 34: Task Status Update on Completion**
    - **Validates: Requirements 9.4**

- [ ] 13. GitHub Integration Component
  - [ ] 13.1 Implement repository connection
    - Create connect_repository method with validation
    - Store connection details in MySQL
    - _Requirements: 4.1_

  - [ ] 13.2 Implement repository synchronization
    - Create sync_repository Celery task
    - Fetch repository contents using PyGithub
    - Update tool configurations from repository
    - _Requirements: 4.2_

  - [ ] 13.3 Implement webhook processing
    - Create process_webhook method
    - Queue webhook events for async processing
    - _Requirements: 4.5_

  - [ ] 13.4 Implement repository disconnection
    - Create disconnect_repository method
    - Remove connection while preserving tool data
    - _Requirements: 4.4_

  - [ ] 13.5 Write property test for GitHub connection validation
    - **Property 13: GitHub Connection Validation**
    - **Validates: Requirements 4.1**

  - [ ] 13.6 Write property test for repository sync consistency
    - **Property 14: Repository Sync Consistency**
    - **Validates: Requirements 4.2**

  - [ ] 13.7 Write property test for disconnect preservation
    - **Property 15: GitHub Disconnect Preservation**
    - **Validates: Requirements 4.4**

  - [ ] 13.8 Write property test for webhook async processing
    - **Property 16: Webhook Async Processing**
    - **Validates: Requirements 4.5**

- [ ] 14. MCP Server Manager Component
  - [ ] 14.1 Implement deployment lifecycle management
    - Create deploy_server method with subprocess/Docker
    - Generate unique endpoint URLs
    - Store deployment records in MySQL
    - _Requirements: 5.1, 7.3_

  - [ ] 14.2 Implement request routing
    - Create route_request method
    - Map slugs to deployment endpoints
    - Forward HTTP requests to deployed servers
    - _Requirements: 5.2_

  - [ ] 14.3 Implement server shutdown
    - Create stop_server method
    - Gracefully terminate server processes
    - Update deployment status
    - _Requirements: 5.5_

  - [ ] 14.4 Implement health monitoring
    - Create check_health method
    - Schedule periodic health checks
    - _Requirements: 5.4_

  - [ ] 14.5 Write property test for deployment endpoint uniqueness
    - **Property 17: Deployment Endpoint Uniqueness**
    - **Validates: Requirements 5.1**

  - [ ] 14.6 Write property test for request routing correctness
    - **Property 18: Request Routing Correctness**
    - **Validates: Requirements 5.2**

  - [ ] 14.7 Write property test for deployment shutdown status
    - **Property 19: Deployment Shutdown Status**
    - **Validates: Requirements 5.5**

- [ ] 15. Checkpoint - Verify all core components
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. API Endpoints - Authentication
  - [ ] 16.1 Implement authentication endpoints
    - POST /api/v1/auth/login - User login with JWT generation
    - POST /api/v1/auth/refresh - Refresh access token
    - POST /api/v1/auth/logout - Invalidate refresh token
    - POST /api/v1/auth/register - User registration
    - _Requirements: 6.1, 6.2_

  - [ ] 16.2 Implement API key management endpoints
    - POST /api/v1/auth/api-keys - Create API key
    - GET /api/v1/auth/api-keys - List user's API keys
    - DELETE /api/v1/auth/api-keys/{key_id} - Revoke API key
    - _Requirements: 6.5_

  - [ ] 16.3 Write integration tests for auth endpoints
    - Test login flow with valid/invalid credentials
    - Test token refresh flow
    - Test API key creation and usage
    - _Requirements: 6.1, 6.2, 6.5_

- [ ] 17. API Endpoints - MCP Management
  - [ ] 17.1 Implement MCP tool CRUD endpoints
    - POST /api/v1/mcps - Create MCP tool
    - GET /api/v1/mcps/{tool_id} - Get tool details
    - PUT /api/v1/mcps/{tool_id} - Update tool
    - DELETE /api/v1/mcps/{tool_id} - Delete tool
    - GET /api/v1/mcps - List tools with pagination
    - GET /api/v1/mcps/{tool_id}/history - Get version history
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 7.5_

  - [ ] 17.2 Add authentication and authorization middleware
    - Implement JWT validation dependency
    - Add permission checking decorators
    - _Requirements: 6.2, 6.4_

  - [ ] 17.3 Write property test for response schema consistency
    - **Property 37: Response Schema Consistency**
    - **Validates: Requirements 10.4**

  - [ ] 17.4 Write property test for API version routing
    - **Property 38: API Version Routing**
    - **Validates: Requirements 10.5**

- [ ] 18. API Endpoints - Knowledge Base
  - [ ] 18.1 Implement knowledge base endpoints
    - POST /api/v1/knowledge/documents - Upload document
    - GET /api/v1/knowledge/documents/{doc_id} - Get document
    - DELETE /api/v1/knowledge/documents/{doc_id} - Delete document
    - POST /api/v1/knowledge/search - Semantic search
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 18.2 Write integration tests for knowledge endpoints
    - Test document upload and retrieval
    - Test semantic search with various queries
    - Test document deletion
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

- [ ] 19. API Endpoints - AI Analysis
  - [ ] 19.1 Implement AI analysis endpoints
    - POST /api/v1/analyze/feasibility - Analyze feasibility
    - POST /api/v1/analyze/improvements - Get improvement suggestions
    - POST /api/v1/analyze/generate-config - Generate configuration
    - GET /api/v1/tasks/{task_id} - Get task status and result
    - _Requirements: 3.1, 3.2, 3.3, 9.4_

  - [ ] 19.2 Write integration tests for analysis endpoints
    - Test feasibility analysis flow
    - Test improvement suggestions
    - Test config generation
    - Test async task status polling
    - _Requirements: 3.1, 3.2, 3.3, 9.4_

- [ ] 20. API Endpoints - GitHub Integration
  - [ ] 20.1 Implement GitHub integration endpoints
    - POST /api/v1/github/connect - Connect repository
    - POST /api/v1/github/sync/{connection_id} - Trigger sync
    - DELETE /api/v1/github/disconnect/{connection_id} - Disconnect
    - POST /api/v1/github/webhook - Webhook receiver
    - _Requirements: 4.1, 4.2, 4.4, 4.5_

  - [ ] 20.2 Write integration tests for GitHub endpoints
    - Test repository connection
    - Test sync triggering
    - Test disconnection
    - Test webhook processing
    - _Requirements: 4.1, 4.2, 4.4, 4.5_

- [ ] 21. API Endpoints - Deployments
  - [ ] 21.1 Implement deployment management endpoints
    - POST /api/v1/deployments - Deploy MCP tool
    - GET /api/v1/deployments/{deployment_id} - Get deployment status
    - DELETE /api/v1/deployments/{deployment_id} - Stop deployment
    - GET /api/v1/deployments - List deployments
    - _Requirements: 5.1, 5.5_

  - [ ] 21.2 Implement dynamic MCP service routing
    - Create catch-all route for /mcp/{slug}/v1/*
    - Route requests to deployed MCP servers
    - _Requirements: 5.2_

  - [ ] 21.3 Implement usage statistics recording
    - Add middleware to record API usage
    - Store statistics in MySQL
    - _Requirements: 7.4_

  - [ ] 21.4 Write property test for usage statistics recording
    - **Property 27: Usage Statistics Recording**
    - **Validates: Requirements 7.4**

- [ ] 22. Middleware Implementation
  - [ ] 22.1 Implement CORS middleware
    - Configure allowed origins from environment
    - Validate origins against whitelist
    - _Requirements: 11.5_

  - [ ] 22.2 Implement rate limiting middleware
    - Use slowapi for rate limiting
    - Configure limits per endpoint
    - _Requirements: 11.2_

  - [ ] 22.3 Implement logging middleware
    - Add request ID generation
    - Log request/response with correlation IDs
    - Implement sensitive data redaction
    - _Requirements: 12.2, 12.4, 11.4_

  - [ ] 22.4 Implement error handling middleware
    - Create global exception handler
    - Format error responses consistently
    - _Requirements: 10.3_

  - [ ] 22.5 Write property test for rate limit enforcement
    - **Property 39: Rate Limit Enforcement**
    - **Validates: Requirements 11.2**

  - [ ] 22.6 Write property test for sensitive data redaction
    - **Property 40: Sensitive Data Redaction**
    - **Validates: Requirements 11.4**

  - [ ] 22.7 Write property test for CORS validation
    - **Property 41: CORS Origin Validation**
    - **Validates: Requirements 11.5**

  - [ ] 22.8 Write property test for structured error logging
    - **Property 42: Structured Error Logging**
    - **Validates: Requirements 12.2**

  - [ ] 22.9 Write property test for request correlation ID
    - **Property 43: Request Correlation ID**
    - **Validates: Requirements 12.4**

- [ ] 23. Checkpoint - Verify all API endpoints
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 24. WebSocket and SSE Implementation
  - [ ] 24.1 Implement WebSocket endpoint
    - Create /ws endpoint with authentication
    - Implement connection management
    - Add subscription mechanism for task updates
    - _Requirements: 13.1, 13.2_

  - [ ] 24.2 Implement Server-Sent Events endpoint
    - Create /events endpoint
    - Implement event streaming
    - _Requirements: 13.3_

  - [ ] 24.3 Implement broadcast functionality
    - Create broadcast message handler
    - Deliver to all connected clients
    - _Requirements: 13.5_

  - [ ] 24.4 Implement connection cleanup
    - Handle disconnections gracefully
    - Clean up resources
    - _Requirements: 13.4_

  - [ ] 24.5 Write property test for WebSocket authentication
    - **Property 44: WebSocket Authentication**
    - **Validates: Requirements 13.1**

  - [ ] 24.6 Write property test for WebSocket status push
    - **Property 45: WebSocket Status Push**
    - **Validates: Requirements 13.2**

  - [ ] 24.7 Write property test for SSE event delivery
    - **Property 46: SSE Event Delivery**
    - **Validates: Requirements 13.3**

  - [ ] 24.8 Write property test for connection cleanup
    - **Property 47: Connection Cleanup**
    - **Validates: Requirements 13.4**

  - [ ] 24.9 Write property test for broadcast delivery
    - **Property 48: Broadcast Message Delivery**
    - **Validates: Requirements 13.5**

- [ ] 25. Monitoring and Observability
  - [ ] 25.1 Implement Prometheus metrics
    - Add prometheus-client integration
    - Create /metrics endpoint
    - Implement custom metrics (tools, deployments, cache hit rate)
    - _Requirements: 12.1_

  - [ ] 25.2 Implement structured logging
    - Configure structlog
    - Add context to all log entries
    - _Requirements: 12.2_

  - [ ] 25.3 Enhance health check endpoint
    - Add dependency checks (MySQL, MongoDB, Redis, Qdrant, RabbitMQ)
    - Return detailed status
    - _Requirements: 12.3_

  - [ ] 25.4 Write unit tests for monitoring features
    - Test metrics endpoint returns Prometheus format
    - Test health check verifies all dependencies
    - _Requirements: 12.1, 12.3_

- [ ] 26. Docker and Deployment Configuration
  - [ ] 26.1 Create Dockerfile for API service
    - Multi-stage build for optimization
    - Include all dependencies
    - Set up non-root user
    - _Requirements: 14.1_

  - [ ] 26.2 Create Dockerfile for Celery worker
    - Reuse base image from API
    - Configure worker-specific settings
    - _Requirements: 14.1_

  - [ ] 26.3 Create docker-compose.yml
    - Define all services (api, worker, beat, databases, broker)
    - Configure networking and volumes
    - Add health checks
    - _Requirements: 14.1, 14.3_

  - [ ] 26.4 Create environment configuration files
    - Create .env.example with all variables
    - Document each configuration option
    - _Requirements: 14.2_

  - [ ] 26.5 Write property test for environment config loading
    - **Property 49: Environment Configuration Loading**
    - **Validates: Requirements 14.2**

  - [ ] 26.6 Write property test for invalid config rejection
    - **Property 50: Invalid Configuration Rejection**
    - **Validates: Requirements 14.5**

- [ ] 27. Documentation and Examples
  - [ ] 27.1 Create README.md
    - Project overview and features
    - Installation instructions
    - Quick start guide
    - API documentation links

  - [ ] 27.2 Create API usage examples
    - Example requests for each endpoint
    - Authentication flow examples
    - WebSocket connection examples

  - [ ] 27.3 Create deployment guide
    - Docker deployment instructions
    - Environment configuration guide
    - Scaling recommendations

- [ ] 28. Final Integration and Testing
  - [ ] 28.1 Run full test suite
    - Execute all unit tests
    - Execute all property tests (100 iterations)
    - Execute all integration tests
    - Verify 80%+ code coverage

  - [ ] 28.2 Test Docker deployment
    - Build all Docker images
    - Start services with docker-compose
    - Verify all health checks pass
    - Test end-to-end API flows

  - [ ] 28.3 Performance testing
    - Load test API endpoints with Locust
    - Verify response times meet requirements
    - Test concurrent WebSocket connections

  - [ ] 28.4 Security audit
    - Verify all endpoints require authentication
    - Test rate limiting
    - Verify input sanitization
    - Check for exposed secrets

- [ ] 29. Final Checkpoint
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- Integration tests verify end-to-end flows
- Checkpoints ensure incremental validation throughout implementation
- All async operations use proper async/await patterns
- Database operations use connection pooling and proper session management
- Error handling follows the exception hierarchy defined in the design
- Security is enforced at multiple layers (validation, authentication, authorization)
