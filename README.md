# MCP Platform Backend

A comprehensive backend service for managing Model Context Protocol (MCP) tools with AI-powered analysis, knowledge base services, and dynamic server deployment.

## Features

- **MCP Tool Management**: Full CRUD operations with version history
- **Knowledge Base**: Semantic search using vector embeddings
- **AI Analysis**: Feasibility analysis and improvement suggestions
- **GitHub Integration**: Repository synchronization and webhooks
- **Dynamic Deployments**: On-demand MCP server instances
- **Real-time Communication**: WebSocket and Server-Sent Events support

## Technology Stack

- **Framework**: FastAPI 0.110+
- **Databases**: MySQL, MongoDB, Redis, Qdrant
- **Task Queue**: Celery with RabbitMQ
- **AI**: LangChain with OpenAI
- **Authentication**: JWT with OAuth2

## Prerequisites

- Python 3.11 or higher
- MySQL 8.0+
- MongoDB 6.0+
- Redis 7.0+
- Qdrant 1.7+
- RabbitMQ 3.12+

## Setup

### 1. Clone the repository

```bash
git clone <repository-url>
cd mcp-platform-backend
```

### 2. Create virtual environment

```bash
python -m venv venv

# On Windows
venv\Scripts\activate

# On Unix/MacOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Update database credentials, API keys, etc.
```

### 5. Run the application

```bash
# Development server with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py
```

### Project Structure

```
mcp-platform-backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── health.py    # Health check endpoint
│   └── core/
│       ├── __init__.py
│       └── config.py        # Configuration settings
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Health check tests
├── .env.example             # Example environment variables
├── .gitignore
├── pytest.ini               # Pytest configuration
├── requirements.txt         # Python dependencies
└── README.md
```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Health Check

Check service health:

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "services": {
    "mysql": true,
    "mongodb": true,
    "redis": true,
    "qdrant": true,
    "rabbitmq": true
  }
}
```

## License

See LICENSE file for details.
