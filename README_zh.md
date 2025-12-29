# MCP 平台后端

一个全面的、生产就绪的后端服务，用于管理模型上下文协议（MCP）工具，具有 AI 驱动的分析、知识库服务、GitHub 集成和动态服务器部署功能。

## 🚀 功能特性

### 核心功能
- **MCP 工具管理**：完整的 CRUD 操作，支持版本历史跟踪
- **知识库**：使用向量嵌入的语义搜索（Qdrant）
- **AI 分析**：可行性分析、改进建议和自动配置生成
- **GitHub 集成**：仓库同步和 webhook 处理
- **动态部署**：按需 MCP 服务器实例，支持健康监控
- **实时通信**：WebSocket 和服务器发送事件支持

### 企业级功能
- **身份验证和授权**：基于 JWT 的身份验证，支持基于角色的访问控制（RBAC）
- **API 密钥管理**：安全的 API 密钥生成和验证
- **异步任务处理**：基于 Celery 的后台作业处理
- **缓存层**：基于 Redis 的缓存，提升性能
- **速率限制**：每个端点可配置的速率限制
- **监控**：Prometheus 指标和结构化日志
- **数据库迁移**：基于 Alembic 的模式版本控制

## 🏗️ 架构

该平台采用现代异步优先架构，支持多语言持久化：

- **API 层**：FastAPI，支持 async/await
- **业务逻辑**：面向服务的架构，关注点清晰分离
- **数据层**：针对不同数据类型的多个专用数据库
- **任务队列**：Celery 工作进程处理长时间运行的操作
- **实时**：WebSocket 和 SSE 用于实时更新

### 技术栈

| 组件 | 技术 | 用途 |
|-----------|-----------|---------|
| API 框架 | FastAPI 0.110+ | 高性能异步 Web 框架 |
| ORM | SQLAlchemy 2.0 | 异步数据库操作 |
| 结构化数据 | MySQL 8.0+ | 用户、工具、部署 |
| 文档存储 | MongoDB 6.0+ | 版本历史、任务结果 |
| 向量数据库 | Qdrant 1.7+ | 语义搜索嵌入 |
| 缓存 | Redis 7.0+ | 会话管理、缓存 |
| 任务队列 | Celery 5.3+ | 异步任务处理 |
| 消息代理 | RabbitMQ 3.12+ | 任务队列代理 |
| AI 集成 | LangChain 0.1+ | LLM 编排 |
| 身份验证 | JWT + OAuth2 | 安全身份验证 |

## 📋 前置要求

开始之前，请确保已安装以下软件：

- **Python**：3.11 或更高版本
- **MySQL**：8.0 或更高版本
- **MongoDB**：6.0 或更高版本
- **Redis**：7.0 或更高版本
- **Qdrant**：1.7 或更高版本
- **RabbitMQ**：3.12 或更高版本
- **Docker**（可选）：用于容器化部署

## 🚀 快速开始

### 选项 1：本地开发环境设置

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd mcp-platform-backend
```

#### 2. 创建并激活虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# Windows 激活
venv\Scripts\activate

# Unix/MacOS 激活
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置环境变量

```bash
# 复制示例环境文件
cp .env.example .env

# 编辑 .env 文件进行配置
# 重要：更新以下内容：
# - 数据库凭据（MySQL、MongoDB、Redis、Qdrant）
# - SECRET_KEY（生成方式：python -c "import secrets; print(secrets.token_urlsafe(32))"）
# - OPENAI_API_KEY（用于 AI 功能）
# - GITHUB_TOKEN（用于 GitHub 集成）
```

#### 5. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head

# 创建 Qdrant 集合（如果未自动创建）
python -c "from app.core.database import init_qdrant; import asyncio; asyncio.run(init_qdrant())"
```

#### 6. 启动服务

```bash
# 终端 1：启动 API 服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端 2：启动 Celery 工作进程
celery -A app.core.celery_app worker --loglevel=info

# 终端 3：启动 Celery beat（用于定时任务）
celery -A app.core.celery_app beat --loglevel=info
```

#### 7. 访问应用程序

- **API**：http://localhost:8000
- **交互式 API 文档**：http://localhost:8000/api/docs
- **ReDoc**：http://localhost:8000/api/redoc
- **指标**：http://localhost:8000/metrics
- **健康检查**：http://localhost:8000/health

### 选项 2：Docker 部署

有关使用 Docker 进行生产部署的信息，请参阅 [Docker 部署指南](docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md)。

```bash
# 使用 Docker Compose 快速启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📚 文档

### 完整文档

有关全面的文档，请参阅 [docs/](docs/) 目录：

- **[API 文档](docs/api/API_EXAMPLES_zh.md)** - 完整的 API 参考和示例
- **[设置指南](docs/setup/SETUP_COMPLETE_zh.md)** - 详细的设置说明
- **[Docker 部署](docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md)** - 生产部署指南
- **[实现指南](docs/implementation/)** - 服务实现详情
- **[测试指南](docs/testing/TESTING_NOTES_zh.md)** - 测试策略和指导原则

### 快速 API 参考

API 使用基于 JWT 的身份验证。首先，获取访问令牌：

```bash
# 注册新用户
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "email": "dev@example.com",
    "password": "SecurePassword123!"
  }'

# 登录获取访问令牌
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "developer",
    "password": "SecurePassword123!"
  }'
```

在后续请求中使用访问令牌：

```bash
curl -X GET http://localhost:8000/api/v1/mcps \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

有关详细的 API 文档和示例，请参阅 [docs/api/API_EXAMPLES_zh.md](docs/api/API_EXAMPLES_zh.md)。

### API 端点

#### 核心端点

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/health` | GET | 所有服务的健康检查 |
| `/metrics` | GET | Prometheus 指标 |
| `/api/docs` | GET | 交互式 API 文档 |

#### 身份验证端点

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | 注册新用户 |
| `/api/v1/auth/login` | POST | 登录并获取 JWT 令牌 |
| `/api/v1/auth/refresh` | POST | 刷新访问令牌 |
| `/api/v1/auth/logout` | POST | 注销并使令牌失效 |
| `/api/v1/auth/api-keys` | POST | 创建 API 密钥 |
| `/api/v1/auth/api-keys` | GET | 列出用户的 API 密钥 |
| `/api/v1/auth/api-keys/{key_id}` | DELETE | 撤销 API 密钥 |

#### MCP 工具管理

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/mcps` | POST | 创建新的 MCP 工具 |
| `/api/v1/mcps` | GET | 列出 MCP 工具（分页） |
| `/api/v1/mcps/{tool_id}` | GET | 获取工具详情 |
| `/api/v1/mcps/{tool_id}` | PUT | 更新工具 |
| `/api/v1/mcps/{tool_id}` | DELETE | 删除工具（软删除） |
| `/api/v1/mcps/{tool_id}/history` | GET | 获取版本历史 |

#### 知识库

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/knowledge/documents` | POST | 上传文档 |
| `/api/v1/knowledge/documents/{doc_id}` | GET | 获取文档 |
| `/api/v1/knowledge/documents/{doc_id}` | DELETE | 删除文档 |
| `/api/v1/knowledge/search` | POST | 语义搜索 |

#### AI 分析

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/analyze/feasibility` | POST | 分析可行性 |
| `/api/v1/analyze/improvements` | POST | 获取改进建议 |
| `/api/v1/analyze/generate-config` | POST | 生成配置 |
| `/api/v1/tasks/{task_id}` | GET | 获取任务状态和结果 |

#### GitHub 集成

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/github/connect` | POST | 连接仓库 |
| `/api/v1/github/sync/{connection_id}` | POST | 触发同步 |
| `/api/v1/github/disconnect/{connection_id}` | DELETE | 断开仓库连接 |
| `/api/v1/github/webhook` | POST | Webhook 接收器 |

#### 部署

| 端点 | 方法 | 描述 |
|----------|--------|-------------|
| `/api/v1/deployments` | POST | 部署 MCP 工具 |
| `/api/v1/deployments` | GET | 列出部署 |
| `/api/v1/deployments/{deployment_id}` | GET | 获取部署状态 |
| `/api/v1/deployments/{deployment_id}` | DELETE | 停止部署 |

#### 实时通信

| 端点 | 协议 | 描述 |
|----------|----------|-------------|
| `/ws` | WebSocket | 实时更新的 WebSocket 连接 |
| `/events` | SSE | 服务器发送事件流 |

## 🧪 开发

### 项目结构

```
mcp-platform-backend/
├── app/
│   ├── api/                    # API 层
│   │   ├── v1/                 # API 版本 1
│   │   │   ├── auth.py         # 身份验证端点
│   │   │   ├── mcps.py         # MCP 工具端点
│   │   │   ├── knowledge.py    # 知识库端点
│   │   │   ├── analyze.py      # AI 分析端点
│   │   │   ├── github.py       # GitHub 集成端点
│   │   │   ├── deployments.py  # 部署端点
│   │   │   ├── tasks.py        # 任务状态端点
│   │   │   ├── websocket.py    # WebSocket 处理器
│   │   │   └── health.py       # 健康检查端点
│   │   ├── dependencies.py     # 依赖注入
│   │   └── middleware.py       # 自定义中间件
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 应用程序设置
│   │   ├── database.py         # 数据库连接
│   │   ├── security.py         # 安全工具
│   │   ├── permissions.py      # RBAC 权限
│   │   ├── celery_app.py       # Celery 配置
│   │   ├── logging_config.py   # 日志设置
│   │   └── monitoring.py       # Prometheus 指标
│   ├── models/                 # SQLAlchemy 模型
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── mcp_tool.py
│   │   ├── deployment.py
│   │   ├── github_connection.py
│   │   └── usage_stat.py
│   ├── schemas/                # Pydantic 模式
│   │   ├── auth.py
│   │   ├── mcp_tool.py
│   │   ├── knowledge.py
│   │   ├── ai_analysis.py
│   │   ├── github.py
│   │   └── deployment.py
│   ├── services/               # 业务逻辑
│   │   ├── auth_service.py
│   │   ├── mcp_manager.py
│   │   ├── knowledge_service.py
│   │   ├── ai_analyzer.py
│   │   ├── github_integration.py
│   │   ├── mcp_server_manager.py
│   │   ├── cache_service.py
│   │   └── task_tracker.py
│   ├── tasks/                  # Celery 任务
│   │   ├── ai_tasks.py
│   │   ├── github_tasks.py
│   │   └── embedding_tasks.py
│   └── main.py                 # 应用程序入口点
├── alembic/                    # 数据库迁移
│   ├── versions/
│   └── env.py
├── tests/                      # 测试套件
│   ├── unit/                   # 单元测试
│   ├── integration/            # 集成测试
│   └── property/               # 基于属性的测试
├── scripts/                    # 实用脚本
├── .env.example                # 环境模板
├── .gitignore
├── alembic.ini                 # Alembic 配置
├── docker-compose.yml          # Docker Compose 设置
├── Dockerfile                  # API 服务 Dockerfile
├── Dockerfile.worker           # Celery 工作进程 Dockerfile
├── pytest.ini                  # Pytest 配置
├── requirements.txt            # Python 依赖
└── README.md
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率报告的测试
pytest --cov=app --cov-report=html --cov-report=term

# 运行特定测试类别
pytest tests/unit/              # 仅单元测试
pytest tests/integration/       # 仅集成测试
pytest tests/property/          # 仅基于属性的测试

# 运行特定测试文件
pytest tests/unit/test_ai_analyzer_unit.py

# 运行详细输出的测试
pytest -v

# 并行运行测试（更快）
pytest -n auto
```

### 代码质量

```bash
# 使用 black 格式化代码
black app/ tests/

# 排序导入
isort app/ tests/

# 使用 flake8 进行代码检查
flake8 app/ tests/

# 使用 mypy 进行类型检查
mypy app/
```

### 数据库迁移

```bash
# 创建新迁移
alembic revision --autogenerate -m "更改描述"

# 应用迁移
alembic upgrade head

# 回滚一个迁移
alembic downgrade -1

# 查看迁移历史
alembic history

# 查看当前版本
alembic current
```

## 🔧 配置

### 环境变量

所有配置都通过环境变量完成。有关可用选项的完整列表，请参阅 [.env.example](.env.example)。

主要配置区域：

- **应用程序**：调试模式、环境、日志
- **数据库**：MySQL、MongoDB、Redis、Qdrant 连接字符串
- **安全**：JWT 密钥、令牌过期、CORS 设置
- **外部服务**：OpenAI API 密钥、GitHub 令牌
- **性能**：速率限制、工作进程并发
- **监控**：日志级别、指标导出

### 安全最佳实践

1. **更改默认凭据**：更新所有密码和密钥
2. **使用强密钥**：为 JWT 签名生成安全的随机密钥
3. **启用 HTTPS**：在生产环境中使用 TLS/SSL
4. **配置 CORS**：将允许的来源限制为您的前端域
5. **速率限制**：启用并配置适当的限制
6. **API 密钥**：使用 API 密钥进行服务间通信
7. **环境隔离**：为开发/测试/生产使用单独的数据库

## 📊 监控

### 健康检查

平台提供全面的健康检查：

```bash
curl http://localhost:8000/health
```

响应包括所有依赖项的状态：

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
    "qdrant": {
      "status": "healthy",
      "response_time_ms": 8
    },
    "rabbitmq": {
      "status": "healthy",
      "response_time_ms": 4
    }
  }
}
```

### Prometheus 指标

指标在 `/metrics` 端点公开：

```bash
curl http://localhost:8000/metrics
```

可用指标：

- `http_requests_total`：按方法、端点、状态的总 HTTP 请求数
- `http_request_duration_seconds`：请求持续时间直方图
- `mcp_tools_total`：MCP 工具总数
- `mcp_deployments_active`：活动部署数量
- `cache_hit_rate`：Redis 缓存命中率
- `celery_tasks_total`：按状态的总 Celery 任务数

### 日志记录

生产环境默认启用结构化 JSON 日志记录：

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

## 🚢 部署

### Docker 部署

有关详细的部署说明，请参阅 [docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md](docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md)。

快速开始：

```bash
# 构建并启动所有服务
docker-compose up -d

# 扩展 API 服务器
docker-compose up -d --scale api=3

# 查看日志
docker-compose logs -f api

# 停止所有服务
docker-compose down
```

### 生产检查清单

- [ ] 更新所有默认密码和密钥
- [ ] 配置 HTTPS/TLS 证书
- [ ] 设置数据库备份
- [ ] 配置监控和告警
- [ ] 设置日志聚合
- [ ] 启用速率限制
- [ ] 为生产域配置 CORS
- [ ] 设置 DEBUG=false
- [ ] 使用生产级数据库实例
- [ ] 设置负载均衡器
- [ ] 配置自动扩展
- [ ] 设置 CI/CD 流水线

## 🤝 贡献

欢迎贡献！请遵循以下指导原则：

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 打开 Pull Request

### 开发指导原则

- 为新功能编写测试
- 遵循 PEP 8 风格指南
- 为函数和类添加文档字符串
- 为 API 更改更新文档
- 提交前运行测试和代码检查

## 📝 许可证

详情请参阅 [LICENSE](LICENSE) 文件。

## 🆘 支持

如有问题、疑问或贡献：

- **问题**：在 GitHub 上开启 issue
- **文档**：查看 [docs/](docs/) 获取全面文档
- **API 文档**：查看 `/api/docs` 获取交互式 API 文档
- **示例**：查看 [docs/api/API_EXAMPLES_zh.md](docs/api/API_EXAMPLES_zh.md) 获取使用示例

## 🙏 致谢

构建工具：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL 工具包和 ORM
- [LangChain](https://python.langchain.com/) - LLM 应用程序框架
- [Celery](https://docs.celeryq.dev/) - 分布式任务队列
- [Qdrant](https://qdrant.tech/) - 向量相似性搜索引擎