# API 使用示例

本文档提供使用 MCP 平台后端 API 的全面示例。

## 目录

- [身份验证](#身份验证)
- [MCP 工具管理](#mcp-工具管理)
- [知识库](#知识库)
- [AI 分析](#ai-分析)
- [GitHub 集成](#github-集成)
- [部署](#部署)
- [WebSocket 通信](#websocket-通信)
- [错误处理](#错误处理)

## 身份验证

### 注册新用户

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

**响应：**
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

### 登录并获取访问令牌

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "SecurePassword123!"
  }'
```

**响应：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJyb2xlcyI6WyJkZXZlbG9wZXIiXSwiZXhwIjoxNzA1MzE3MDAwfQ.signature",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI1NTBlODQwMC1lMjliLTQxZDQtYTcxNi00NDY2NTU0NDAwMDAiLCJ0eXBlIjoicmVmcmVzaCIsImV4cCI6MTcwNTkxNzAwMH0.signature",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 刷新访问令牌

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "YOUR_REFRESH_TOKEN"
  }'
```

**响应：**
```json
{
  "access_token": "NEW_ACCESS_TOKEN",
  "token_type": "bearer",
  "expires_in": 900
}
```

### 创建 API 密钥

```bash
curl -X POST http://localhost:8000/api/v1/auth/api-keys \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "生产 API 密钥",
    "expires_at": "2025-12-31T23:59:59Z"
  }'
```

**响应：**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "name": "生产 API 密钥",
  "key": "mcp_live_1234567890abcdef",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2025-12-31T23:59:59Z"
}
```

### 使用 API 密钥身份验证

```bash
curl -X GET http://localhost:8000/api/v1/mcps \
  -H "X-API-Key: mcp_live_1234567890abcdef"
```

## MCP 工具管理

### 创建 MCP 工具

```bash
curl -X POST http://localhost:8000/api/v1/mcps \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "天气 MCP 工具",
    "slug": "weather-tool",
    "description": "通过 MCP 协议提供天气信息",
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
          "description": "获取位置的当前天气",
          "parameters": {
            "location": {
              "type": "string",
              "description": "城市名称或坐标"
            }
          }
        }
      ]
    }
  }'
```

**响应：**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "天气 MCP 工具",
  "slug": "weather-tool",
  "description": "通过 MCP 协议提供天气信息",
  "version": "1.0.0",
  "author_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "draft",
  "created_at": "2024-01-15T10:35:00Z",
  "updated_at": "2024-01-15T10:35:00Z"
}
```

### 列出 MCP 工具

```bash
curl -X GET "http://localhost:8000/api/v1/mcps?page=1&page_size=10&status=active" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "items": [
    {
      "id": "770e8400-e29b-41d4-a716-446655440002",
      "name": "天气 MCP 工具",
      "slug": "weather-tool",
      "description": "通过 MCP 协议提供天气信息",
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

### 获取 MCP 工具详情

```bash
curl -X GET http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "天气 MCP 工具",
  "slug": "weather-tool",
  "description": "通过 MCP 协议提供天气信息",
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

### 更新 MCP 工具

```bash
curl -X PUT http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.1.0",
    "status": "active",
    "description": "更新的天气工具，支持预报功能"
  }'
```

**响应：**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "name": "天气 MCP 工具",
  "slug": "weather-tool",
  "description": "更新的天气工具，支持预报功能",
  "version": "1.1.0",
  "status": "active",
  "updated_at": "2024-01-15T11:00:00Z"
}
```

### 获取版本历史

```bash
curl -X GET http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002/history \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
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

### 删除 MCP 工具

```bash
curl -X DELETE http://localhost:8000/api/v1/mcps/770e8400-e29b-41d4-a716-446655440002 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "message": "MCP 工具删除成功",
  "id": "770e8400-e29b-41d4-a716-446655440002"
}
```

## 知识库

### 上传文档

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/documents \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "MCP 协议规范",
    "content": "模型上下文协议（MCP）是 AI 模型与外部工具之间通信的标准化协议...",
    "metadata": {
      "source": "official-docs",
      "tags": ["mcp", "protocol", "specification"],
      "language": "zh"
    }
  }'
```

**响应：**
```json
{
  "document_id": "880e8400-e29b-41d4-a716-446655440003",
  "title": "MCP 协议规范",
  "created_at": "2024-01-15T11:15:00Z",
  "embedding_id": "990e8400-e29b-41d4-a716-446655440004"
}
```

### 语义搜索

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "MCP 如何处理身份验证？",
    "limit": 5,
    "filters": {
      "tags": ["mcp", "protocol"]
    }
  }'
```

**响应：**
```json
{
  "results": [
    {
      "document_id": "880e8400-e29b-41d4-a716-446655440003",
      "title": "MCP 协议规范",
      "content_snippet": "...MCP 身份验证使用 JWT 令牌进行安全通信...",
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

### 获取文档

```bash
curl -X GET http://localhost:8000/api/v1/knowledge/documents/880e8400-e29b-41d4-a716-446655440003 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "document_id": "880e8400-e29b-41d4-a716-446655440003",
  "title": "MCP 协议规范",
  "content": "模型上下文协议（MCP）是一个标准化协议...",
  "metadata": {
    "source": "official-docs",
    "tags": ["mcp", "protocol", "specification"],
    "language": "zh"
  },
  "created_at": "2024-01-15T11:15:00Z",
  "updated_at": "2024-01-15T11:15:00Z"
}
```

### 删除文档

```bash
curl -X DELETE http://localhost:8000/api/v1/knowledge/documents/880e8400-e29b-41d4-a716-446655440003 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "message": "文档删除成功",
  "document_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

## AI 分析

### 分析可行性

```bash
curl -X POST http://localhost:8000/api/v1/analyze/feasibility \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "name": "数据库查询工具",
      "description": "在生产数据库上执行 SQL 查询",
      "requirements": {
        "database_access": true,
        "read_only": false
      }
    }
  }'
```

**响应（异步任务）：**
```json
{
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "pending",
  "message": "可行性分析已排队处理"
}
```

### 获取改进建议

```bash
curl -X POST http://localhost:8000/api/v1/analyze/improvements \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "770e8400-e29b-41d4-a716-446655440002"
  }'
```

**响应（异步任务）：**
```json
{
  "task_id": "bb0e8400-e29b-41d4-a716-446655440006",
  "status": "pending",
  "message": "改进分析已排队处理"
}
```

### 生成配置

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

**响应（异步任务）：**
```json
{
  "task_id": "cc0e8400-e29b-41d4-a716-446655440007",
  "status": "pending",
  "message": "配置生成已排队处理"
}
```

### 获取任务状态和结果

```bash
curl -X GET http://localhost:8000/api/v1/tasks/aa0e8400-e29b-41d4-a716-446655440005 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应（已完成任务）：**
```json
{
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "completed",
  "result": {
    "score": 0.75,
    "is_feasible": true,
    "reasoning": "提议的数据库查询工具在适当的安全控制下是可行的...",
    "risks": [
      "直接数据库访问存在安全风险",
      "写操作可能损坏数据"
    ],
    "recommendations": [
      "默认实现只读模式",
      "添加查询验证和清理",
      "使用连接池提高性能"
    ]
  },
  "created_at": "2024-01-15T11:30:00Z",
  "completed_at": "2024-01-15T11:30:15Z"
}
```
## GitHub 集成

### 连接仓库

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

**响应：**
```json
{
  "connection_id": "dd0e8400-e29b-41d4-a716-446655440008",
  "repository_url": "https://github.com/username/mcp-tools",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "connected",
  "created_at": "2024-01-15T11:45:00Z"
}
```

### 触发仓库同步

```bash
curl -X POST http://localhost:8000/api/v1/github/sync/dd0e8400-e29b-41d4-a716-446655440008 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应（异步任务）：**
```json
{
  "task_id": "ee0e8400-e29b-41d4-a716-446655440009",
  "status": "pending",
  "message": "仓库同步已排队处理"
}
```

### 断开仓库连接

```bash
curl -X DELETE http://localhost:8000/api/v1/github/disconnect/dd0e8400-e29b-41d4-a716-446655440008 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "message": "仓库连接断开成功",
  "connection_id": "dd0e8400-e29b-41d4-a716-446655440008"
}
```

### GitHub Webhook

```bash
# 此端点由 GitHub 调用，不是用户直接调用
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

**响应：**
```json
{
  "message": "Webhook 已接收并排队处理",
  "event_type": "push"
}
```

## 部署

### 部署 MCP 工具

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

**响应：**
```json
{
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "endpoint_url": "http://localhost:8000/mcp/weather-tool/v1",
  "status": "starting",
  "deployed_at": "2024-01-15T12:00:00Z"
}
```

### 列出部署

```bash
curl -X GET "http://localhost:8000/api/v1/deployments?status=running" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "deployments": [
    {
      "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
      "tool_id": "770e8400-e29b-41d4-a716-446655440002",
      "tool_name": "天气 MCP 工具",
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

### 获取部署状态

```bash
curl -X GET http://localhost:8000/api/v1/deployments/ff0e8400-e29b-41d4-a716-446655440010 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "tool_id": "770e8400-e29b-41d4-a716-446655440002",
  "tool_name": "天气 MCP 工具",
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

### 停止部署

```bash
curl -X DELETE http://localhost:8000/api/v1/deployments/ff0e8400-e29b-41d4-a716-446655440010 \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**响应：**
```json
{
  "message": "部署停止成功",
  "deployment_id": "ff0e8400-e29b-41d4-a716-446655440010",
  "stopped_at": "2024-01-15T12:10:00Z"
}
```

### 访问已部署的 MCP 工具

```bash
# 部署后，通过其端点访问工具
curl -X POST http://localhost:8000/mcp/weather-tool/v1/tools/get_weather \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "北京"
  }'
```

**响应：**
```json
{
  "location": "北京",
  "temperature": 18,
  "conditions": "多云",
  "humidity": 65,
  "wind_speed": 12
}
```

## WebSocket 通信

### 连接到 WebSocket

**JavaScript 示例：**

```javascript
// 使用身份验证连接到 WebSocket
const token = "YOUR_ACCESS_TOKEN";
const ws = new WebSocket(`ws://localhost:8000/ws?token=${token}`);

// 连接打开
ws.onopen = (event) => {
  console.log("WebSocket 已连接");
  
  // 订阅任务更新
  ws.send(JSON.stringify({
    type: "subscribe",
    task_id: "aa0e8400-e29b-41d4-a716-446655440005"
  }));
};

// 监听消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("收到:", data);
  
  if (data.type === "task_update") {
    console.log(`任务 ${data.task_id} 状态: ${data.status}`);
    if (data.status === "completed") {
      console.log("结果:", data.result);
    }
  }
};

// 处理错误
ws.onerror = (error) => {
  console.error("WebSocket 错误:", error);
};

// 连接关闭
ws.onclose = (event) => {
  console.log("WebSocket 已断开连接");
};
```

**Python 示例：**

```python
import asyncio
import websockets
import json

async def connect_websocket():
    token = "YOUR_ACCESS_TOKEN"
    uri = f"ws://localhost:8000/ws?token={token}"
    
    async with websockets.connect(uri) as websocket:
        # 订阅任务更新
        await websocket.send(json.dumps({
            "type": "subscribe",
            "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
        }))
        
        # 监听消息
        async for message in websocket:
            data = json.loads(message)
            print(f"收到: {data}")
            
            if data["type"] == "task_update":
                print(f"任务 {data['task_id']} 状态: {data['status']}")
                if data["status"] == "completed":
                    print(f"结果: {data['result']}")
                    break

# 运行 WebSocket 客户端
asyncio.run(connect_websocket())
```

### WebSocket 消息类型

**订阅任务更新：**
```json
{
  "type": "subscribe",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
}
```

**取消订阅任务更新：**
```json
{
  "type": "unsubscribe",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005"
}
```

**任务更新消息（服务器到客户端）：**
```json
{
  "type": "task_update",
  "task_id": "aa0e8400-e29b-41d4-a716-446655440005",
  "status": "running",
  "progress": 45,
  "message": "正在分析配置..."
}
```

**任务完成消息（服务器到客户端）：**
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

### 服务器发送事件（SSE）

**JavaScript 示例：**

```javascript
// 连接到 SSE 端点
const token = "YOUR_ACCESS_TOKEN";
const eventSource = new EventSource(`http://localhost:8000/events?token=${token}`);

// 监听所有事件
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log("收到事件:", data);
};

// 监听特定事件类型
eventSource.addEventListener("task_update", (event) => {
  const data = JSON.parse(event.data);
  console.log("任务更新:", data);
});

eventSource.addEventListener("deployment_status", (event) => {
  const data = JSON.parse(event.data);
  console.log("部署状态:", data);
});

// 处理错误
eventSource.onerror = (error) => {
  console.error("SSE 错误:", error);
  eventSource.close();
};
```

**Python 示例：**

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
                    print(f"收到事件: {data}")

listen_to_events()
```

## 错误处理

### 常见错误响应

#### 400 错误请求

```json
{
  "detail": "无效的请求格式",
  "error_code": "INVALID_REQUEST"
}
```

#### 401 未授权

```json
{
  "detail": "无效或过期的令牌",
  "error_code": "UNAUTHORIZED"
}
```

#### 403 禁止访问

```json
{
  "detail": "权限不足，无法执行此操作",
  "error_code": "FORBIDDEN",
  "required_permission": "mcps:delete"
}
```

#### 404 未找到

```json
{
  "detail": "未找到 MCP 工具",
  "error_code": "NOT_FOUND",
  "resource_type": "mcp_tool",
  "resource_id": "770e8400-e29b-41d4-a716-446655440002"
}
```

#### 422 验证错误

```json
{
  "detail": [
    {
      "loc": ["body", "version"],
      "msg": "字符串不匹配正则表达式 '^\\d+\\.\\d+\\.\\d+$'",
      "type": "value_error.str.regex",
      "ctx": {
        "pattern": "^\\d+\\.\\d+\\.\\d+$"
      }
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

#### 429 请求过多

```json
{
  "detail": "超出速率限制。请稍后重试。",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

#### 500 内部服务器错误

```json
{
  "detail": "发生内部错误",
  "error_code": "INTERNAL_ERROR",
  "request_id": "abc123-def456-ghi789"
}
```

### 错误处理最佳实践

**1. 始终检查 HTTP 状态码：**

```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/mcps",
    headers={"Authorization": f"Bearer {token}"},
    json=tool_data
)

if response.status_code == 201:
    tool = response.json()
    print(f"工具已创建: {tool['id']}")
elif response.status_code == 422:
    errors = response.json()["detail"]
    print("验证错误:")
    for error in errors:
        print(f"  - {error['loc']}: {error['msg']}")
elif response.status_code == 401:
    print("身份验证失败。请重新登录。")
else:
    print(f"错误: {response.status_code} - {response.json()['detail']}")
```

**2. 使用指数退避处理速率限制：**

```python
import time

def make_request_with_retry(url, headers, data, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 60)
            wait_time = retry_after * (2 ** attempt)  # 指数退避
            print(f"速率受限。等待 {wait_time} 秒...")
            time.sleep(wait_time)
            continue
        
        return response
    
    raise Exception("超出最大重试次数")
```

**3. 使用请求 ID 进行调试：**

```python
response = requests.get(
    "http://localhost:8000/api/v1/mcps/invalid-id",
    headers={"Authorization": f"Bearer {token}"}
)

if response.status_code >= 500:
    error_data = response.json()
    request_id = error_data.get("request_id")
    print(f"服务器错误发生。请求 ID: {request_id}")
    print("请联系支持并提供此请求 ID。")
```

**4. 发送前验证数据：**

```python
from pydantic import BaseModel, ValidationError, Field

class MCPToolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., pattern=r'^[a-z0-9-]+$')
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    config: dict

try:
    tool_data = MCPToolCreate(
        name="我的工具",
        slug="my-tool",
        version="1.0.0",
        config={"servers": []}
    )
    
    # 发送验证的数据
    response = requests.post(
        "http://localhost:8000/api/v1/mcps",
        headers={"Authorization": f"Bearer {token}"},
        json=tool_data.dict()
    )
except ValidationError as e:
    print("发送前验证失败:")
    print(e.json())
```

## 其他资源

- **交互式 API 文档**：http://localhost:8000/api/docs
- **ReDoc 文档**：http://localhost:8000/api/redoc
- **健康检查**：http://localhost:8000/health
- **Prometheus 指标**：http://localhost:8000/metrics

## 支持

如有问题或疑问：
- 在 GitHub 上开启 issue
- 查看交互式 API 文档
- 查看部署指南了解生产设置