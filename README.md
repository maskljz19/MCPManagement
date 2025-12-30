# MCP Platform Backend

A comprehensive, production-ready backend service for managing Model Context Protocol (MCP) tools with AI-powered analysis, knowledge base services, GitHub integration, and dynamic server deployment.

## 🚀 Features

### Core Functionality
- **MCP Tool Management**: Full CRUD operations with version history tracking
- **Knowledge Base**: Document storage and basic text search (MongoDB)
- **AI Analysis**: Feasibility analysis, improvement suggestions, and auto-configuration generation
- **GitHub Integration**: Repository synchronization and webhook processing
- **Dynamic Deployments**: On-demand MCP server instances with health monitoring
- **Real-time Communication**: WebSocket and Server-Sent Events support

### Enterprise Features
- **Authentication & Authorization**: JWT-based auth with role-based access control (RBAC)
- **API Key Management**: Secure API key generation and validation
- **Async Task Processing**: Celery-based background job processing
- **Caching Layer**: Redis-based caching for improved performance
- **Rate Limiting**: Configurable rate limits per endpoint
- **Monitoring**: Prometheus metrics and structured logging
- **Database Migrations**: Alembic-based schema versioning

## 🏗️ Architecture

The platform uses a modern async-first architecture with polyglot persistence:

- **API Layer**: FastAPI with async/await support
- **Business Logic**: Service-oriented architecture with clear separation of concerns
- **Data Layer**: Multiple specialized databases for different data types
- **Task Queue**: Celery workers for long-running operations
- **Real-time**: WebSocket and SSE for live updates

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI 0.110+ | High-performance async web framework |
| ORM | SQLAlchemy 2.0 | Async database operations |
| Structured Data | MySQL 8.0+ | Users, tools, deployments |
| Document Store | MongoDB 6.0+ | Version history, task results, documents |
| Cache | Redis 7.0+ | Session management, caching |
| Task Queue | Celery 5.3+ | Async task processing |
| Message Broker | RabbitMQ 3.12+ | Task queue broker |
| AI Integration | LangChain 0.1+ | LLM orchestration |
| Authentication | JWT + OAuth2 | Secure authentication |

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

- **Python**: 3.11 or higher
- **MySQL**: 8.0 or higher
- **MongoDB**: 6.0 or higher
- **Redis**: 7.0 or higher
- **RabbitMQ**: 3.12 or higher
- **Docker** (optional): For containerized deployment

## 🚀 Quick Start

### Option 1: Local Development Setup

#### 1. Clone the repository

```bash
git clone <repository-url>
cd mcp-platform-backend
```

#### 2. Create and activate virtual environment

```bash
# Create virtual environment
python -m venv venv

# Activate on Windows
venv\Scripts\activate

# Activate on Unix/MacOS
source venv/bin/activate
```

#### 3. Install dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# IMPORTANT: Update the following:
# - Database credentials (MySQL, MongoDB, Redis)
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(32))")
# - OPENAI_API_KEY (for AI features)
# - GITHUB_TOKEN (for GitHub integration)
```

#### 5. Initialize databases

```bash
# Run database migrations
alembic upgrade head
```

#### 6. Start the services

```bash
# Terminal 1: Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
celery -A app.core.celery_app worker --loglevel=info

# Terminal 3: Start Celery beat (for scheduled tasks)
celery -A app.core.celery_app beat --loglevel=info
```

#### 7. Access the application

- **API**: http://localhost:8000
- **Interactive API Docs**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **Metrics**: http://localhost:8000/metrics
- **Health Check**: http://localhost:8000/health

### Option 2: Docker Deployment

For production deployment using Docker, see the [Docker Deployment Guide](docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md).

```bash
# Quick start with Docker Compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## 📚 Documentation

### Complete Documentation

For comprehensive documentation, see the [docs/](docs/) directory:

- **[API Documentation](docs/api/API_EXAMPLES.md)** - Complete API reference with examples
- **[Setup Guide](docs/setup/SETUP_COMPLETE.md)** - Detailed setup instructions
- **[Docker Deployment](docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md)** - Production deployment guide
- **[Implementation Guides](docs/implementation/)** - Service implementation details
- **[Testing Guide](docs/testing/TESTING_NOTES.md)** - Testing strategy and guidelines

### Quick API Reference

The API uses JWT-based authentication. First, obtain an access token:

```bash
# Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "email": "dev@example.com",
    "password": "SecurePassword123!"
  }'

# Login to get access token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "SecurePassword123!"
  }'
```

Use the access token in subsequent requests:

```bash
curl -X GET http://localhost:8000/api/v1/mcps \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

For detailed API documentation with examples, see [docs/api/API_EXAMPLES.md](docs/api/API_EXAMPLES.md).

### API Endpoints

#### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check for all services |
| `/metrics` | GET | Prometheus metrics |
| `/api/docs` | GET | Interactive API documentation |

#### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Register new user |
| `/api/v1/auth/login` | POST | Login and get JWT tokens |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/logout` | POST | Logout and invalidate tokens |
| `/api/v1/auth/api-keys` | POST | Create API key |
| `/api/v1/auth/api-keys` | GET | List user's API keys |
| `/api/v1/auth/api-keys/{key_id}` | DELETE | Revoke API key |

#### MCP Tool Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/mcps` | POST | Create new MCP tool |
| `/api/v1/mcps` | GET | List MCP tools (paginated) |
| `/api/v1/mcps/{tool_id}` | GET | Get tool details |
| `/api/v1/mcps/{tool_id}` | PUT | Update tool |
| `/api/v1/mcps/{tool_id}` | DELETE | Delete tool (soft delete) |
| `/api/v1/mcps/{tool_id}/history` | GET | Get version history |

#### Knowledge Base

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/knowledge/documents` | POST | Upload document |
| `/api/v1/knowledge/documents/{doc_id}` | GET | Get document |
| `/api/v1/knowledge/documents/{doc_id}` | DELETE | Delete document |
| `/api/v1/knowledge/search` | POST | Text search |

#### AI Analysis

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/analyze/feasibility` | POST | Analyze feasibility |
| `/api/v1/analyze/improvements` | POST | Get improvement suggestions |
| `/api/v1/analyze/generate-config` | POST | Generate configuration |
| `/api/v1/tasks/{task_id}` | GET | Get task status and result |

#### GitHub Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/github/connect` | POST | Connect repository |
| `/api/v1/github/sync/{connection_id}` | POST | Trigger sync |
| `/api/v1/github/disconnect/{connection_id}` | DELETE | Disconnect repository |
| `/api/v1/github/webhook` | POST | Webhook receiver |

#### Deployments

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/deployments` | POST | Deploy MCP tool |
| `/api/v1/deployments` | GET | List deployments |
| `/api/v1/deployments/{deployment_id}` | GET | Get deployment status |
| `/api/v1/deployments/{deployment_id}` | DELETE | Stop deployment |

#### Real-time Communication

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws` | WebSocket | WebSocket connection for real-time updates |
| `/events` | SSE | Server-Sent Events stream |

## 🧪 Development

### Project Structure

```
mcp-platform-backend/
├── app/
│   ├── api/                    # API layer
│   │   ├── v1/                 # API version 1
│   │   │   ├── auth.py         # Authentication endpoints
│   │   │   ├── mcps.py         # MCP tool endpoints
│   │   │   ├── knowledge.py    # Knowledge base endpoints
│   │   │   ├── analyze.py      # AI analysis endpoints
│   │   │   ├── github.py       # GitHub integration endpoints
│   │   │   ├── deployments.py  # Deployment endpoints
│   │   │   ├── tasks.py        # Task status endpoints
│   │   │   ├── websocket.py    # WebSocket handler
│   │   │   └── health.py       # Health check endpoint
│   │   ├── dependencies.py     # Dependency injection
│   │   └── middleware.py       # Custom middleware
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Application settings
│   │   ├── database.py         # Database connections
│   │   ├── security.py         # Security utilities
│   │   ├── permissions.py      # RBAC permissions
│   │   ├── celery_app.py       # Celery configuration
│   │   ├── logging_config.py   # Logging setup
│   │   └── monitoring.py       # Prometheus metrics
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── mcp_tool.py
│   │   ├── deployment.py
│   │   ├── github_connection.py
│   │   └── usage_stat.py
│   ├── schemas/                # Pydantic schemas
│   │   ├── auth.py
│   │   ├── mcp_tool.py
│   │   ├── knowledge.py
│   │   ├── ai_analysis.py
│   │   ├── github.py
│   │   └── deployment.py
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── mcp_manager.py
│   │   ├── knowledge_service.py
│   │   ├── ai_analyzer.py
│   │   ├── github_integration.py
│   │   ├── mcp_server_manager.py
│   │   ├── cache_service.py
│   │   └── task_tracker.py
│   ├── tasks/                  # Celery tasks
│   │   ├── ai_tasks.py
│   │   ├── github_tasks.py
│   │   └── embedding_tasks.py
│   └── main.py                 # Application entry point
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── tests/                      # Test suite
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── property/               # Property-based tests
├── scripts/                    # Utility scripts
├── .env.example                # Environment template
├── .gitignore
├── alembic.ini                 # Alembic configuration
├── docker-compose.yml          # Docker Compose setup
├── Dockerfile                  # API service Dockerfile
├── Dockerfile.worker           # Celery worker Dockerfile
├── pytest.ini                  # Pytest configuration
├── requirements.txt            # Python dependencies
└── README.md
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test categories
pytest tests/unit/              # Unit tests only
pytest tests/integration/       # Integration tests only
pytest tests/property/          # Property-based tests only

# Run specific test file
pytest tests/unit/test_ai_analyzer_unit.py

# Run tests with verbose output
pytest -v

# Run tests in parallel (faster)
pytest -n auto
```

### Code Quality

```bash
# Format code with black
black app/ tests/

# Sort imports
isort app/ tests/

# Lint with flake8
flake8 app/ tests/

# Type checking with mypy
mypy app/
```

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

## 🔧 Configuration

### Environment Variables

All configuration is done through environment variables. See [.env.example](.env.example) for a complete list of available options.

Key configuration areas:

- **Application**: Debug mode, environment, logging
- **Databases**: MySQL, MongoDB, Redis connection strings
- **Security**: JWT secret, token expiration, CORS settings
- **External Services**: OpenAI API key, GitHub token
- **Performance**: Rate limiting, worker concurrency
- **Monitoring**: Log level, metrics export

### Security Best Practices

1. **Change default credentials**: Update all passwords and secret keys
2. **Use strong secrets**: Generate secure random keys for JWT signing
3. **Enable HTTPS**: Use TLS/SSL in production
4. **Configure CORS**: Restrict allowed origins to your frontend domains
5. **Rate limiting**: Enable and configure appropriate limits
6. **API keys**: Use API keys for service-to-service communication
7. **Environment isolation**: Use separate databases for dev/staging/prod

## 📊 Monitoring

### Health Checks

The platform provides comprehensive health checks:

```bash
curl http://localhost:8000/health
```

Response includes status for all dependencies:

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "services": {
    "mysql": {
      "status": "healthy",
      "response_time_ms": 5
    },
    "mongodb": {
      "status": "healthy",
      "response_time_ms": 3
    },
    "redis": {
      "status": "healthy",
      "response_time_ms": 1
    },
    "rabbitmq": {
      "status": "healthy",
      "response_time_ms": 4
    }
  }
}
```

### Prometheus Metrics

Metrics are exposed at `/metrics` endpoint:

```bash
curl http://localhost:8000/metrics
```

Available metrics:

- `http_requests_total`: Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds`: Request duration histogram
- `mcp_tools_total`: Total number of MCP tools
- `mcp_deployments_active`: Number of active deployments
- `cache_hit_rate`: Redis cache hit rate
- `celery_tasks_total`: Total Celery tasks by status

### Logging

Structured JSON logging is enabled by default in production:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "app.api.v1.mcps",
  "message": "MCP tool created",
  "request_id": "abc123",
  "user_id": "user-uuid",
  "tool_id": "tool-uuid"
}
```

## 🚢 Deployment

### Docker Deployment

See [docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md](docs/deployment/DOCKER_DEPLOYMENT_GUIDE.md) for detailed deployment instructions.

Quick start:

```bash
# Build and start all services
docker-compose up -d

# Scale API servers
docker-compose up -d --scale api=3

# View logs
docker-compose logs -f api

# Stop all services
docker-compose down
```

### Production Checklist

- [ ] Update all default passwords and secrets
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up database backups
- [ ] Configure monitoring and alerting
- [ ] Set up log aggregation
- [ ] Enable rate limiting
- [ ] Configure CORS for production domains
- [ ] Set DEBUG=false
- [ ] Use production-grade database instances
- [ ] Set up load balancer
- [ ] Configure auto-scaling
- [ ] Set up CI/CD pipeline

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Write tests for new features
- Follow PEP 8 style guide
- Add docstrings to functions and classes
- Update documentation for API changes
- Run tests and linting before committing

## 📝 License

See [LICENSE](LICENSE) file for details.

## 🆘 Support

For issues, questions, or contributions:

- **Issues**: Open an issue on GitHub
- **Documentation**: See [docs/](docs/) for comprehensive documentation
- **API Docs**: See `/api/docs` for interactive API documentation
- **Examples**: See [docs/api/API_EXAMPLES.md](docs/api/API_EXAMPLES.md) for usage examples

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [LangChain](https://python.langchain.com/) - LLM application framework
- [Celery](https://docs.celeryq.dev/) - Distributed task queue
