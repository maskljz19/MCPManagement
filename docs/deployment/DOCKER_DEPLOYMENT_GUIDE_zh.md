# Docker 部署指南

## 概览

本指南提供使用 Docker 和 Docker Compose 部署 MCP 平台后端的说明。部署包括所有必要的服务：API、Celery 工作进程、数据库和消息代理。

## 前置条件

- Docker Engine 20.10+
- Docker Compose 2.0+
- 至少 4GB 可用内存
- 至少 10GB 可用磁盘空间

## 快速开始

### 1. 环境配置

为您的部署复制适当的环境文件：

```bash
# 用于 Docker Compose 部署
cp .env.docker .env

# 用于本地开发
cp .env.development .env
```

编辑 `.env` 并更新以下关键值：

```bash
# 安全 - 生产环境中必须更改！
SECRET_KEY=your-secure-secret-key-min-32-characters-long
MYSQL_PASSWORD=your-secure-mysql-password
RABBITMQ_PASSWORD=your-secure-rabbitmq-password

# 外部服务
OPENAI_API_KEY=sk-your-openai-api-key
GITHUB_TOKEN=ghp_your-github-token
```

### 2. 构建并启动服务

```bash
# 构建所有镜像
docker-compose build

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 3. 验证部署

检查所有服务是否健康：

```bash
docker-compose ps
```

所有服务应显示状态为"Up"和"healthy"。

测试 API 健康端点：

```bash
curl http://localhost:8000/health
```

预期响应：
```json
{
  "status": "healthy",
  "checks": {
    "mysql": true,
    "mongodb": true,
    "redis": true,
    "qdrant": true,
    "rabbitmq": true
  }
}
```

### 4. 运行数据库迁移

```bash
docker-compose exec api alembic upgrade head
```

## 架构

### 服务

部署包括以下服务：

1. **api** - FastAPI 应用程序（端口 8000）
   - 处理 HTTP 请求
   - 提供 REST API 端点
   - 服务 WebSocket 连接

2. **worker** - Celery 工作进程（2 个副本）
   - 处理后台任务
   - 处理 AI 分析
   - 管理 GitHub 同步

3. **beat** - Celery beat 调度器
   - 调度定期任务
   - 管理任务调度

4. **mysql** - MySQL 8.0 数据库（端口 3306）
   - 存储结构化数据
   - 管理用户、工具、部署

5. **mongodb** - MongoDB 7.0（端口 27017）
   - 存储文档数据
   - 管理版本历史

6. **redis** - Redis 7.2（端口 6379）
   - 缓存层
   - 会话管理
   - 任务结果存储

7. **qdrant** - Qdrant 向量数据库（端口 6333）
   - 存储文档嵌入
   - 启用语义搜索

8. **rabbitmq** - RabbitMQ 3.12（端口 5672、15672）
   - Celery 的消息代理
   - 管理 UI 在 http://localhost:15672

### 网络

所有服务通过专用 Docker 网络（`mcp-network`）通信。

### 卷

持久数据存储在 Docker 卷中：

- `mysql_data` - MySQL 数据库文件
- `mongodb_data` - MongoDB 数据库文件
- `redis_data` - Redis 持久化文件
- `qdrant_data` - Qdrant 向量存储
- `rabbitmq_data` - RabbitMQ 数据

## 配置

### 环境变量

有关配置选项的完整列表和详细文档，请参阅 `.env.example`。

主要配置类别：

- **应用程序**：基本应用设置
- **数据库**：MySQL、MongoDB、Redis、Qdrant 的连接字符串
- **消息代理**：RabbitMQ 配置
- **安全**：JWT 设置、密钥
- **外部服务**：OpenAI、GitHub API 密钥
- **CORS**：跨域资源共享设置
- **日志**：日志级别和格式

### 端口映射

默认端口映射（可在 `.env` 中更改）：

- `8000` - API 服务器
- `3306` - MySQL
- `27017` - MongoDB
- `6379` - Redis
- `6333` - Qdrant HTTP API
- `6334` - Qdrant gRPC API
- `5672` - RabbitMQ AMQP
- `15672` - RabbitMQ 管理 UI

## 扩展

### 水平扩展

扩展 API 实例：

```bash
docker-compose up -d --scale api=3
```

扩展 Celery 工作进程：

```bash
docker-compose up -d --scale worker=4
```

### 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

## 监控

### 健康检查

所有服务都包含自动运行的健康检查：

- **API**：`/health` 端点的 HTTP 检查
- **MySQL**：`mysqladmin ping`
- **MongoDB**：`mongosh` ping 命令
- **Redis**：`redis-cli ping`
- **Qdrant**：`/health` 端点的 HTTP 检查
- **RabbitMQ**：`rabbitmq-diagnostics ping`
- **Worker**：Celery inspect ping

### 日志

查看所有服务的日志：

```bash
docker-compose logs -f
```

查看特定服务的日志：

```bash
docker-compose logs -f api
docker-compose logs -f worker
```

### RabbitMQ 管理 UI

在 http://localhost:15672 访问 RabbitMQ 管理界面

默认凭据（生产环境中更改）：
- 用户名：`guest`
- 密码：`guest`

## 维护

### 备份

备份所有数据卷：

```bash
# 停止服务
docker-compose stop

# 备份卷
docker run --rm -v mcp-mysql_data:/data -v $(pwd):/backup alpine tar czf /backup/mysql-backup.tar.gz /data
docker run --rm -v mcp-mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb-backup.tar.gz /data

# 重启服务
docker-compose start
```

### 恢复

从备份恢复：

```bash
# 停止服务
docker-compose stop

# 恢复卷
docker run --rm -v mcp-mysql_data:/data -v $(pwd):/backup alpine tar xzf /backup/mysql-backup.tar.gz -C /

# 重启服务
docker-compose start
```

### 更新

更新到最新版本：

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build

# 重启服务
docker-compose up -d
```

### 数据库迁移

更新后运行迁移：

```bash
docker-compose exec api alembic upgrade head
```

回滚迁移：

```bash
docker-compose exec api alembic downgrade -1
```

## 故障排除

### 服务无法启动

检查服务日志：

```bash
docker-compose logs <service-name>
```

检查服务健康状态：

```bash
docker-compose ps
```

### 数据库连接问题

验证数据库正在运行且健康：

```bash
docker-compose ps mysql
docker-compose logs mysql
```

从 API 容器测试连接：

```bash
docker-compose exec api ping mysql
```

### 内存不足

检查容器内存使用情况：

```bash
docker stats
```

在 Docker Desktop 设置中增加 Docker 内存限制或为服务添加资源限制。

### 端口冲突

如果端口已被使用，在 `.env` 中更改它们：

```bash
MYSQL_PORT=3307
REDIS_PORT=6380
```

## 生产部署

### 安全检查清单

- [ ] 更改所有默认密码
- [ ] 生成安全的 SECRET_KEY（32+ 字符）
- [ ] 使用强数据库密码
- [ ] 将 CORS_ORIGINS 配置为特定域
- [ ] 启用速率限制
- [ ] 为外部访问使用 HTTPS/TLS
- [ ] 限制 RabbitMQ 管理 UI 访问
- [ ] 检查并限制暴露的端口
- [ ] 启用防火墙规则
- [ ] 设置日志聚合
- [ ] 配置监控和告警
- [ ] 禁用调试模式（DEBUG=false）
- [ ] 使用生产级数据库实例
- [ ] 实现数据库连接池
- [ ] 配置适当的备份保留策略
- [ ] 设置 SSL/TLS 证书
- [ ] 启用审计日志
- [ ] 实现入侵检测
- [ ] 配置 DDoS 保护

### 推荐的生产设置

1. **带 SSL/TLS 的反向代理**
   - 使用 nginx 或 Traefik 进行 SSL 终止
   - 配置 HTTP/2 以获得更好的性能
   - 启用 HSTS 头
   - 设置自动证书续期（Let's Encrypt）

2. **日志聚合**
   - ELK Stack（Elasticsearch、Logstash、Kibana）
   - Loki + Grafana
   - CloudWatch Logs（AWS）
   - Stackdriver（GCP）

3. **监控和告警**
   - Prometheus + Grafana 用于指标
   - AlertManager 用于通知
   - 正常运行时间监控（UptimeRobot、Pingdom）
   - APM 工具（New Relic、DataDog）

4. **数据库管理**
   - 使用托管数据库服务（AWS RDS、Azure Database、GCP Cloud SQL）
   - 配置自动备份和时间点恢复
   - 设置读副本进行扩展
   - 启用静态和传输加密

5. **自动备份**
   - 每日数据库备份
   - 每周完整系统备份
   - 异地备份存储
   - 定期备份恢复测试

6. **CI/CD 流水线**
   - 拉取请求的自动测试
   - 自动部署到测试环境
   - 生产环境的手动批准
   - 回滚功能

7. **密钥管理**
   - HashiCorp Vault
   - AWS Secrets Manager
   - Azure Key Vault
   - GCP Secret Manager

8. **自动扩展**
   - Kubernetes 用于容器编排
   - AWS ECS/EKS 与自动扩展组
   - Azure Container Instances
   - GCP Cloud Run
### 特定环境配置

使用不同的环境文件：

- `.env.development` - 本地开发
- `.env.staging` - 测试环境
- `.env.production` - 生产环境

### 生产 Nginx 配置

生产环境的 nginx 配置示例：

```nginx
upstream mcp_api {
    least_conn;
    server api1:8000;
    server api2:8000;
    server api3:8000;
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # 安全头
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 速率限制
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    location / {
        proxy_pass http://mcp_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://mcp_api/health;
        access_log off;
    }
}
```

### Kubernetes 部署

对于 Kubernetes 部署，请参阅 `k8s/` 目录中的清单：

```bash
# 应用配置
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/mongodb.yaml
kubectl apply -f k8s/redis.yaml
kubectl apply -f k8s/qdrant.yaml
kubectl apply -f k8s/rabbitmq.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# 检查状态
kubectl get pods -n mcp-platform
kubectl get services -n mcp-platform

# 查看日志
kubectl logs -f deployment/mcp-api -n mcp-platform
```

### 云提供商部署

#### AWS 部署

1. **ECS with Fargate**
   - 使用 AWS ECS 进行容器编排
   - 将 API 和工作进程部署为单独的服务
   - 使用应用程序负载均衡器进行流量分发
   - 使用 RDS for MySQL、DocumentDB for MongoDB
   - 使用 ElastiCache for Redis
   - 使用 Amazon MQ for RabbitMQ

2. **基础设施即代码**
   ```bash
   # 使用 Terraform
   cd terraform/aws
   terraform init
   terraform plan
   terraform apply
   ```

#### Azure 部署

1. **Azure Container Instances**
   - 将容器部署到 ACI
   - 使用 Azure Database for MySQL
   - 使用 Cosmos DB for MongoDB
   - 使用 Azure Cache for Redis
   - 使用 Azure Service Bus 进行消息传递

2. **基础设施即代码**
   ```bash
   # 使用 Terraform
   cd terraform/azure
   terraform init
   terraform plan
   terraform apply
   ```

#### GCP 部署

1. **Cloud Run**
   - 将 API 部署为 Cloud Run 服务
   - 使用 Cloud SQL for MySQL
   - 使用 Firestore 进行文档存储
   - 使用 Memorystore for Redis
   - 使用 Cloud Tasks 进行异步处理

2. **基础设施即代码**
   ```bash
   # 使用 Terraform
   cd terraform/gcp
   terraform init
   terraform plan
   terraform apply
   ```

### 性能优化

1. **数据库优化**
   - 为频繁查询的字段添加索引
   - 使用连接池（SQLAlchemy pool_size=20）
   - 启用查询缓存
   - 优化慢查询

2. **缓存策略**
   - 缓存频繁访问的数据
   - 设置适当的 TTL 值
   - 为关键数据使用缓存预热
   - 实现缓存失效策略

3. **API 性能**
   - 启用 gzip 压缩
   - 为静态资源使用 CDN
   - 实现请求批处理
   - 为 I/O 操作使用 async/await

4. **工作进程优化**
   - 根据负载调整工作进程并发
   - 为关键操作使用任务优先级
   - 实现任务结果过期
   - 监控任务队列长度

### 灾难恢复

1. **备份策略**
   - 自动每日备份
   - 备份保留：30 天
   - 异地备份存储
   - 加密备份

2. **恢复程序**
   ```bash
   # 从备份恢复
   docker-compose down
   ./scripts/restore-backup.sh backup-2024-01-15.tar.gz
   docker-compose up -d
   docker-compose exec api alembic upgrade head
   ```

3. **高可用性**
   - 多区域部署
   - 数据库复制
   - 负载均衡器健康检查
   - 自动故障转移

### 合规性和安全

1. **数据保护**
   - 静态数据加密
   - 传输数据加密（TLS 1.2+）
   - 实现数据保留策略
   - 定期安全审计

2. **访问控制**
   - 基于角色的访问控制（RBAC）
   - 多因素身份验证（MFA）
   - API 密钥轮换策略
   - 所有访问的审计日志

3. **合规性**
   - 欧盟用户的 GDPR 合规
   - SOC 2 合规
   - HIPAA 合规（如果处理健康数据）
   - 定期渗透测试

## 支持

如有问题和疑问：

1. 检查日志：`docker-compose logs -f`
2. 验证健康检查：`docker-compose ps`
3. 查看配置：检查 `.env` 文件
4. 查阅文档：参见 README_zh.md

## 许可证

详情请参阅 LICENSE 文件。