# MCP 工具管理平台 - 后端服务

一个全面的、生产就绪的后端服务，用于管理模型上下文协议（MCP）工具，集成AI分析、知识库服务、GitHub集成和动态服务器部署功能。

## 🚀 核心功能

### 基础功能
- **MCP工具管理**：完整的CRUD操作，支持版本历史追踪
- **工具执行**：同步/异步执行、批量执行、定时执行
- **知识库**：文档存储和文本搜索（MongoDB）
- **AI分析**：可行性分析、改进建议和自动配置生成
- **GitHub集成**：仓库同步和Webhook处理
- **动态部署**：按需MCP服务器实例，支持健康监控
- **实时通信**：WebSocket和Server-Sent Events支持

### 企业级功能
- **认证授权**：基于JWT的认证和基于角色的访问控制（RBAC）
- **API密钥管理**：安全的API密钥生成和验证
- **异步任务处理**：基于Celery的后台任务处理
- **缓存层**：基于Redis的缓存提升性能
- **速率限制**：可配置的端点速率限制
- **监控**：Prometheus指标和结构化日志
- **数据库迁移**：基于Alembic的模式版本控制
- **执行队列**：优先级队列和资源配额管理
- **成本追踪**：执行成本统计和分析
- **审计日志**：完整的操作审计追踪

## 🏗️ 技术架构

平台采用现代化的异步优先架构，使用多语言持久化：

- **API层**：FastAPI，支持async/await
- **业务逻辑**：面向服务的架构，清晰的关注点分离
- **数据层**：针对不同数据类型的专用数据库
- **任务队列**：Celery工作进程处理长时间运行的操作
- **实时通信**：WebSocket和SSE实现实时更新

### 技术栈

| 组件 | 技术 | 用途 |
|------|------|------|
| API框架 | FastAPI 0.100+ | 高性能异步Web框架 |
| ORM | SQLAlchemy 2.0 | 异步数据库操作 |
| 结构化数据 | MySQL 8.0+ | 用户、工具、部署 |
| 文档存储 | MongoDB 6.0+ | 版本历史、任务结果、文档 |
| 缓存 | Redis 7.0+ | 会话管理、缓存 |
| 日志存储 | Elasticsearch 8.0+ | 执行日志、全文搜索 |
| 任务队列 | Celery 5.3+ | 异步任务处理 |
| 消息代理 | RabbitMQ 3.12+ | 任务队列代理 |
| AI集成 | LangChain 0.1+ | LLM编排 |
| 认证 | JWT + OAuth2 | 安全认证 |
| 监控 | Prometheus + Grafana | 指标收集和可视化 |

## 📋 前置要求

开始之前，请确保已安装以下软件：

- **Python**：3.11或更高版本
- **MySQL**：8.0或更高版本
- **MongoDB**：6.0或更高版本
- **Redis**：7.0或更高版本
- **Elasticsearch**：8.0或更高版本（可选，用于日志存储）
- **RabbitMQ**：3.12或更高版本
- **Docker**（可选）：用于容器化部署

## 🚀 快速开始

### 方式1：本地开发环境

#### 1. 克隆仓库

```bash
git clone <repository-url>
cd mcp-platform-backend
```

#### 2. 创建并激活虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# Windows激活
venv\Scripts\activate

# Unix/MacOS激活
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

# 编辑.env文件，更新以下配置：
# - 数据库凭据（MySQL、MongoDB、Redis、Elasticsearch）
# - SECRET_KEY（生成方式：python -c "import secrets; print(secrets.token_urlsafe(32))"）
# - OPENAI_API_KEY（用于AI功能）
# - GITHUB_TOKEN（用于GitHub集成）
```

#### 5. 初始化数据库

```bash
# 运行数据库迁移
alembic upgrade head
```

#### 6. 启动服务

```bash
# 终端1：启动API服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 终端2：启动Celery工作进程
celery -A app.core.celery_app worker --loglevel=info

# 终端3：启动Celery定时任务调度器
celery -A app.core.celery_app beat --loglevel=info
```

#### 7. 访问应用

- **API**：http://localhost:8000
- **交互式API文档**：http://localhost:8000/api/docs
- **ReDoc文档**：http://localhost:8000/api/redoc
- **监控指标**：http://localhost:8000/metrics
- **健康检查**：http://localhost:8000/health

### 方式2：Docker部署

使用Docker Compose快速启动所有服务：

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 📚 文档导航

本项目提供完整的中文文档：

- **[开发者文档](docs/开发者文档.md)** - 代码结构、开发指南
- **[部署运维文档](docs/部署运维文档.md)** - 部署、优化、日志管理
- **[工具使用文档](docs/工具使用文档.md)** - MySQL、Redis、MongoDB、Elasticsearch使用指南
- **[用户指南](docs/用户指南.md)** - 系统功能使用和权限说明
- **[接口文档](docs/接口文档.md)** - 完整的API接口参考和示例

## 🔑 快速API示例

### 用户注册和登录

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

### 使用访问令牌

```bash
# 在后续请求中使用访问令牌
curl -X GET http://localhost:8000/api/v1/mcps \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

详细的API使用示例请参考[接口文档](docs/接口文档.md)。

## 🧪 测试

```bash
# 运行所有测试
pytest

# 运行测试并生成覆盖率报告
pytest --cov=app --cov-report=html --cov-report=term

# 运行特定类别的测试
pytest tests/unit/              # 仅单元测试
pytest tests/integration/       # 仅集成测试
pytest tests/property/          # 仅属性测试

# 并行运行测试（更快）
pytest -n auto
```

## 📊 监控

### 健康检查

```bash
curl http://localhost:8000/health
```

### Prometheus指标

```bash
curl http://localhost:8000/metrics
```

### Grafana仪表板

访问 http://localhost:3000 查看预配置的监控仪表板：
- 系统概览仪表板
- MCP执行仪表板

默认登录凭据：
- 用户名：admin
- 密码：admin（首次登录后请修改）

## 🔧 配置

所有配置通过环境变量完成。详细配置说明请参考：
- [.env.example](.env.example) - 环境变量模板
- [部署运维文档](docs/部署运维文档.md) - 配置详解

## 🤝 贡献

欢迎贡献！请遵循以下指南：

1. Fork本仓库
2. 创建特性分支（`git checkout -b feature/amazing-feature`）
3. 提交更改（`git commit -m 'Add amazing feature'`）
4. 推送到分支（`git push origin feature/amazing-feature`）
5. 开启Pull Request

### 开发指南

- 为新功能编写测试
- 遵循PEP 8代码风格
- 为函数和类添加文档字符串
- 更新API变更的文档
- 提交前运行测试和代码检查

## 📝 许可证

详见[LICENSE](LICENSE)文件。

## 🆘 支持

如有问题、疑问或贡献：

- **问题反馈**：在GitHub上开启Issue
- **文档**：查看[docs/](docs/)目录获取完整文档
- **API文档**：访问`/api/docs`查看交互式API文档

## 🙏 致谢

本项目使用以下优秀的开源项目构建：
- [FastAPI](https://fastapi.tiangolo.com/) - 现代Web框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL工具包和ORM
- [LangChain](https://python.langchain.com/) - LLM应用框架
- [Celery](https://docs.celeryq.dev/) - 分布式任务队列
- [Prometheus](https://prometheus.io/) - 监控和告警
- [Grafana](https://grafana.com/) - 可视化和分析
