# API Usage Examples

This document provides comprehensive examples for using the MCP Platform Backend API.

## Table of Contents

- [Authentication](#authentication)
- [MCP Tool Management](#mcp-tool-management)
- [Knowledge Base](#knowledge-base)
- [AI Analysis](#ai-analysis)
- [GitHub Integration](#github-integration)
- [Deployments](#deployments)
- [WebSocket Communication](#websocket-communication)
- [Error Handling](#error-handling)

## Authentication

### Register a New User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "email": "dev@example.com",
    "password": "SecurePassword123!",
    "role": "developer"
  }'
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "developer",
  "email": "dev@example.com",
  "role": "developer",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Login and Get Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "SecurePassword123!"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJyb2xlcyI6WyJkZXZlbG9wZXIiXSwiZXhwIjoxNzA1MzE3MDAwfQ.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJ0eXBlIjoicmVmcmVzaCIsImV4cCI6MTcwNTkxNzAwMH0.signature",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Refresh Access Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

**Response:**
```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "token_type": "bearer",
  "expires_in": 900
}
```

### Create API Key

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "Production API Key",
  "key": "mcp_live_1234567890abcdef",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### Using API Key Authentication

```bash
curl -X GET http://localhost:8000/api/v1/mcps \
  -H "X-API-Key: mcp_live_1234567890abcdef"
```

## MCP Tool Management

### Create MCP Tool

```bash
curl -X POST http://localhost:8000/api/v1/mcps \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Weather MCP Tool",
    "slug": "weather-tool",
    "description": "Provides weather information via MCP protocol",
    "version": "1.0.0",
    "config": {
      "servers": [
        {
          "name": "weather-server",
          "url": "http://api.weather.com"
        }
      ],
      "tools": [
        {
          "name": "get_weather",
          "description": "Get current weather for a location",
          "parameters": {
            "location": {
              "type": "string",
              "description": "City name or coordinates"
            }
          }
        }
      ]
    }
  }'
```

**Response:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Weather MCP Tool",
  "slug": "weather-tool",
  "description": "Provides weather information via MCP protocol",
  "version": "1.0.0",
  "author_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### List MCP Tools

```bash
curl -X GET "http://localhost:8000/api/v1/mcps?page=1&page_size=10&status=active" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "name": "Weather MCP Tool",
      "slug": "weather-tool",
      "description": "Provides weather information via MCP protocol",
      "version": "1.0.0",
      "status": "active",
      "created_at": "2024-01-15T10:35:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 10,
  "pages": 1
}
```

### Get MCP Tool Details

```bash
curl -X GET http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Weather MCP Tool",
  "slug": "weather-tool",
  "description": "Provides weather information via MCP protocol",
  "version": "1.0.0",
  "author_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "config": {
    "servers": [...],
    "tools": [...]
  },
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### Update MCP Tool

```bash
curl -X PUT http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "status": "active",
    "description": "Updated weather tool with forecast support"
  }'
```

**Response:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "Weather MCP Tool",
  "slug": "weather-tool",
  "description": "Updated weather tool with forecast support",
  "version": "1.1.0",
  "status": "active",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

### Get Version History

```bash
curl -X GET http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002/history \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "versions": [
    {
      "version": "1.1.0",
      "changed_at": "2024-01-15T11:00:00Z",
      "changed_by": "550e8400-e29b-41d4-a716-446655440000",
      "change_type": "update",
      "config": {...}
    },
    {
      "version": "1.0.0",
      "changed_at": "2024-01-15T10:35:00Z",
      "changed_by": "550e8400-e29b-41d4-a716-446655440000",
      "change_type": "create",
      "config": {...}
    }
  ]
}
```

### Delete MCP Tool

```bash
curl -X DELETE http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "message": "MCP tool deleted successfully",
  "id": "770e8400-e29b-41d4-a716-446655440002"
}
```

## Knowledge Base

### Upload Document

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MCP Protocol Specification",
    "content": "The Model Context Protocol (MCP) is a standardized protocol for communication between AI models and external tools...",
    "metadata": {
      "source": "official-docs",
      "tags": ["mcp", "protocol", "specification"],
      "language": "en"
    }
  }'
```

**Response:**
```json
{
  "document_id": "880e8400-e29b-41d4-a716-446655440003",
  "title": "MCP Protocol Specification",
  "created_at": "2024-01-15T11:15:00Z",
  "embedding_id": "990e8400-e29b-41d4-a716-446655440004"
}
```

### Semantic Search

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How does MCP handle authentication?",
    "limit": 5,
    "filters": {
      "tags": ["mcp", "protocol"]
    }
  }'
```

**Response:**
```json
{
  "results": [
    {
      "document_id": "880e8400-e29b-41d4-a716-446655440003",
      "title": "MCP Protocol Specification",
      "content_snippet": "...MCP authentication uses JWT tokens for secure communication...",
      "similarity_score": 0.92,
      "metadata": {
        "source": "official-docs",
        "tags": ["mcp", "protocol", "specification"]
      }
    }
  ],
  "total": 1,
  "query_time_ms": 45
}
```

### Get Document

```bash
curl -X GET http://localhost:8000/api/v1/knowledge/documents/880e8400-e29b-41d4-a716-446655440003 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "document_id": "880e8400-e29b-41d4-a716-446655440003",
  "title": "MCP Protocol Specification",
  "content": "The Model Context Protocol (MCP) is a standardized protocol...",
  "metadata": {
    "source": "official-docs",
    "tags": ["mcp", "protocol", "specification"],
    "language": "en"
  },
  "created_at": "2024-01-15T11:15:00Z",
  "updated_at": "2024-01-15T11:15:00Z"
}
```

### Delete Document

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge/documents/880e8400-e29b-41d4-a716-446655440003 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "message": "Document deleted successfully",
  "document_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

## AI Analysis

### Analyze Feasibility

```bash
curl -X POST http://localhost:8000/api/v1/analyze/feasibility \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "name": "Database Query Tool",
      "description": "Execute SQL queries on production database",
      "requirements": {
        "database_access": true,
        "read_only": false
      }
    }
  }'
```

**Response (Async Task):**
```json
{
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "pending",
  "message": "Feasibility analysis queued for processing"
}
```

### Get Improvement Suggestions

```bash
curl -X POST http://localhost:8000/api/v1/analyze/improvements \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "770e8400-e29b-41d4-a716-446655440002"
  }'
```

**Response (Async Task):**
```json
{
  "task_id": "bb0e8400-e29b-41d4-a716-446655440006",
  "status": "pending",
  "message": "Improvement analysis queued for processing"
}
```

### Generate Configuration

```bash
curl -X POST http://localhost:8000/api/v1/analyze/generate-config \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "requirements": {
      "tool_type": "weather",
      "features": ["current_weather", "forecast", "alerts"],
      "data_sources": ["openweathermap"]
    }
  }'
```

**Response (Async Task):**
```json
{
  "task_id": "cc0e8400-e29b-41d4-a716-446655440007",
  "status": "pending",
  "message": "Configuration generation queued for processing"
}
```

### Get Task Status and Result

```bash
curl -X GET http://localhost:8000/api/v1/tasks/aa0e8400-e29b-41d4-a716-446655440005 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (Completed Task):**
```json
{
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "completed",
  "result": {
    "score": 0.75,
    "is_feasible": true,
    "reasoning": "The proposed database query tool is feasible with proper security controls...",
    "risks": [
      "Direct database access poses security risks",
      "Write operations could corrupt data"
    ],
    "recommendations": [
      "Implement read-only mode by default",
      "Add query validation and sanitization",
      "Use connection pooling for performance"
    ]
  },
  "created_at": "2024-01-15T11:30:00Z",
  "completed_at": "2024-01-15T11:30:15Z"
}
```

## GitHub Integration

### Connect Repository

```bash
curl -X POST http://localhost:8000/api/v1/github/connect \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "repository_url": "https://github.com/username/mcp-tools",
    "tool_id": "770e8400-e29b-41d4-a716-446655440002",
    "access_token": "ghp_your_github_token"
  }'
```

**Response:**
```json
{
  "connection_id": "dd0e8400-e29b-41d4-a716-446655440008",
  "repository_url": "https://github.com/username/mcp-tools",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "connected",
  "created_at": "2024-01-15T11:45:00Z"
}
```

### Trigger Repository Sync

```bash
curl -X POST http://localhost:8000/api/v1/github/sync/dd0e8400-e29b-41d4-a716-446655440008 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response (Async Task):**
```json
{
  "task_id": "ee0e8400-e29b-41d4-a716-446655440009",
  "status": "pending",
  "message": "Repository sync queued for processing"
}
```

### Disconnect Repository

```bash
curl -X DELETE http://localhost:8000/api/v1/github/disconnect/dd0e8400-e29b-41d4-a716-446655440008 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "message": "Repository disconnected successfully",
  "connection_id": "dd0e8400-e29b-41d4-a716-446655440008"
}
```

### GitHub Webhook

```bash
# This endpoint is called by GitHub, not by users directly
curl -X POST http://localhost:8000/api/v1/github/webhook \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d '{
    "ref": "refs/heads/main",
    "repository": {
      "full_name": "username/mcp-tools"
    },
    "commits": [...]
  }'
```

**Response:**
```json
{
  "message": "Webhook received and queued for processing",
  "event_type": "push"
}
```

## Deployments

### Deploy MCP Tool

```bash
curl -X POST http://localhost:8000/api/v1/deployments \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "770e8400-e29b-41d4-a716-446655440002",
    "config": {
      "environment": "production",
      "replicas": 2,
      "resources": {
        "cpu": "500m",
        "memory": "512Mi"
      }
    }
  }'
```

**Response:**
```json
{
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "endpoint_url": "http://localhost:8000/mcp/weather-tool/v1",
  "status": "starting",
  "deployed_at": "2024-01-15T12:00:00Z"
}
```

### List Deployments

```bash
curl -X GET "http://localhost:8000/api/v1/deployments?status=running" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "deployments": [
    {
      "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
      "tool_id": "770e8400-e29b-41d4-a716-446655440002",
      "tool_name": "Weather MCP Tool",
      "endpoint_url": "http://localhost:8000/mcp/weather-tool/v1",
      "status": "running",
      "health_status": "healthy",
      "deployed_at": "2024-01-15T12:00:00Z",
      "last_health_check": "2024-01-15T12:05:00Z"
    }
  ],
  "total": 1
}
```

### Get Deployment Status

```bash
curl -X GET http://localhost:8000/api/v1/deployments/ff0e8400-e29b-41d4-a716-446655440010 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "tool_name": "Weather MCP Tool",
  "endpoint_url": "http://localhost:8000/mcp/weather-tool/v1",
  "status": "running",
  "health_status": "healthy",
  "deployed_at": "2024-01-15T12:00:00Z",
  "last_health_check": "2024-01-15T12:05:00Z",
  "metrics": {
    "requests_total": 1523,
    "avg_response_time_ms": 45,
    "error_rate": 0.02
  }
}
```

### Stop Deployment

```bash
curl -X DELETE http://localhost:8000/api/v1/deployments/ff0e8400-e29b-41d4-a716-446655440010 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Response:**
```json
{
  "message": "Deployment stopped successfully",
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "stopped_at": "2024-01-15T12:10:00Z"
}
```

### Access Deployed MCP Tool

```bash
# Once deployed, access the tool through its endpoint
curl -X POST http://localhost:8000/mcp/weather-tool/v1/tools/get_weather \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "San Francisco, CA"
  }'
```

**Response:**
```json
{
  "location": "San Francisco, CA",
  "temperature": 18,
  "conditions": "Partly Cloudy",
  "humidity": 65,
  "wind_speed": 12
}
```

## WebSocket Communication

### Connect to WebSocket

**JavaScript Example:**

```javascript
// Connect to WebSocket with authentication
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

// Connection opened
ws.onopen = (event) => {
  console.log("WebSocket connected");
  
  // Subscribe to task updates
  ws.send(JSON.stringify({
    type: "subscribe",
    task_id: "aa0e8400-e29b-41d4-a716-446655440005"
  }));
};

// Listen for messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Received:", data);
  
  if (data.type === "task_update") {
    console.log(`Task ${data.task_id} status: ${data.status}`);
    if (data.status === "completed") {
      console.log("Result:", data.result);
    }
  }
};

// Handle errors
ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

// Connection closed
ws.onclose = (event) => {
  console.log("WebSocket disconnected");
};
```

**Python Example:**

```python
import asyncio
import websockets
import json

async def connect_websocket():
    token = "YOUR_ACCESS_TOKEN"
    uri = f"ws://localhost:8000/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # Subscribe to task updates
        await websocket.send(json.dumps({
            "type": "subscribe",
            "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
        }))
        
        # Listen for messages
        async for message in websocket:
            data = json.loads(message)
            print(f"Received: {data}")
            
            if data["type"] == "task_update":
                print(f"Task {data['task_id']} status: {data['status']}")
                if data["status"] == "completed":
                    print(f"Result: {data['result']}")
                    break

# Run the WebSocket client
asyncio.run(connect_websocket())
```

### WebSocket Message Types

**Subscribe to Task Updates:**
```json
{
  "type": "subscribe",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
}
```

**Unsubscribe from Task Updates:**
```json
{
  "type": "unsubscribe",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
}
```

**Task Update Message (Server to Client):**
```json
{
  "type": "task_update",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "running",
  "progress": 45,
  "message": "Analyzing configuration..."
}
```

**Task Completed Message (Server to Client):**
```json
{
  "type": "task_update",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "completed",
  "result": {
    "score": 0.75,
    "is_feasible": true,
    "reasoning": "..."
  }
}
```

### Server-Sent Events (SSE)

**JavaScript Example:**

```javascript
// Connect to SSE endpoint
const token = "YOUR_ACCESS_TOKEN";
const eventSource = new EventSource(`http://localhost:8000/events?token=${token}`);

// Listen for all events
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("Event received:", data);
};

// Listen for specific event types
eventSource.addEventListener("task_update", (event) => {
  const data = JSON.parse(event.data);
  console.log("Task update:", data);
});

eventSource.addEventListener("deployment_status", (event) => {
  const data = JSON.parse(event.data);
  console.log("Deployment status:", data);
});

// Handle errors
eventSource.onerror = (error) => {
  console.error("SSE error:", error);
  eventSource.close();
};
```

**Python Example:**

```python
import requests
import json

def listen_to_events():
    token = "YOUR_ACCESS_TOKEN"
    url = f"http://localhost:8000/events?token={token}"
    
    with requests.get(url, stream=True, headers={"Accept": "text/event-stream"}) as response:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    print(f"Event received: {data}")

listen_to_events()
```

## Error Handling

### Common Error Responses

#### 400 Bad Request

```json
{
  "detail": "Invalid request format",
  "error_code": "INVALID_REQUEST"
}
```

#### 401 Unauthorized

```json
{
  "detail": "Invalid or expired token",
  "error_code": "UNAUTHORIZED"
}
```

#### 403 Forbidden

```json
{
  "detail": "Insufficient permissions to perform this action",
  "error_code": "FORBIDDEN",
  "required_permission": "mcps:delete"
}
```

#### 404 Not Found

```json
{
  "detail": "MCP tool not found",
  "error_code": "NOT_FOUND",
  "resource_type": "mcp_tool",
  "resource_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

#### 422 Validation Error

```json
{
  "detail": [
    {
      "loc": ["body", "version"],
      "msg": "string does not match regex '^\\d+\\.\\d+\\.\\d+$'",
      "type": "value_error.str.regex",
      "ctx": {
        "pattern": "^\\d+\\.\\d+\\.\\d+$"
      }
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

#### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

#### 500 Internal Server Error

```json
{
  "detail": "An internal error occurred",
  "error_code": "INTERNAL_ERROR",
  "request_id": "abc123-def456-ghi789"
}
```

### Error Handling Best Practices

**1. Always check HTTP status codes:**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/mcps",
    headers={"Authorization": f"Bearer {token}"},
    json=tool_data
)

if response.status_code == 201:
    tool = response.json()
    print(f"Tool created: {tool['id']}")
elif response.status_code == 422:
    errors = response.json()["detail"]
    print("Validation errors:")
    for error in errors:
        print(f"  - {error['loc']}: {error['msg']}")
elif response.status_code == 401:
    print("Authentication failed. Please login again.")
else:
    print(f"Error: {response.status_code} - {response.json()['detail']}")
```

**2. Handle rate limiting with exponential backoff:**

```python
import time

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 60)
            wait_time = retry_after * (2 ** attempt)  # Exponential backoff
            print(f"Rate limited. Waiting {wait_time} seconds...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

**3. Use request IDs for debugging:**

```python
response = requests.get(
    "http://localhost:8000/api/v1/mcps/invalid-id",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code >= 500:
    error_data = response.json()
    request_id = error_data.get("request_id")
    print(f"Server error occurred. Request ID: {request_id}")
    print("Please contact support with this request ID.")
```

**4. Validate data before sending:**

```python
from pydantic import BaseModel, ValidationError, Field

class MCPToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$')
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    config: dict

try:
    tool_data = MCPToolCreate(
        name="My Tool",
        slug="my-tool",
        version="1.0.0",
        config={"servers": []}
    )
    
    # Send validated data
    response = requests.post(
        "http://localhost:8000/api/v1/mcps",
        headers={"Authorization": f"Bearer {token}"},
        json=tool_data.dict()
    )
except ValidationError as e:
    print("Validation failed before sending:")
    print(e.json())
```

## Additional Resources

- **Interactive API Documentation**: http://localhost:8000/api/docs
- **ReDoc Documentation**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/health
- **Prometheus Metrics**: http://localhost:8000/metrics

## Support

For issues or questions:
- Open an issue on GitHub
- Check the interactive API documentation
- Review the deployment guide for production setup
