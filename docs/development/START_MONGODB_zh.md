# 为属性测试启动 MongoDB

## 当前状态

Docker 已安装在您的系统上（版本 29.0.1），但 Docker Desktop 当前未运行。

## 运行属性测试的步骤

### 1. 启动 Docker Desktop

1. 打开 Docker Desktop 应用程序
2. 等待 Docker 完全启动（系统托盘中的鲸鱼图标应该稳定）
3. 验证 Docker 正在运行：
   ```bash
   docker ps
   ```

### 2. 启动 MongoDB 容器

一旦 Docker 运行，启动 MongoDB：

```bash
# 启动 MongoDB 容器
docker run -d --name mongodb -p 27017:27017 mongo:latest

# 验证 MongoDB 正在运行
docker ps | grep mongodb

# 检查 MongoDB 日志（可选）
docker logs mongodb
```

### 3. 运行属性测试

现在您可以运行属性测试：

```bash
# 运行所有 AI 分析器属性测试
pytest tests/property/test_ai_analysis_properties.py -v

# 或运行带 Hypothesis 统计的测试
pytest tests/property/test_ai_analysis_properties.py -v --hypothesis-show-statistics
```

### 4. 停止 MongoDB（完成后）

测试完成后，您可以停止并移除 MongoDB 容器：

```bash
# 停止 MongoDB
docker stop mongodb

# 移除容器（可选）
docker rm mongodb
```

## 替代方案：使用 Docker Compose

如果您愿意，可以使用 Docker Compose 管理所有服务：

```bash
# 启动所有服务（如果存在 docker-compose.yml）
docker-compose up -d mongodb

# 停止所有服务
docker-compose down
```

## 故障排除

### Docker Desktop 无法启动

1. 检查是否启用了 Hyper-V 或 WSL2（Windows）
2. 重启计算机
3. 如有必要，重新安装 Docker Desktop

### MongoDB 连接问题

如果启动 MongoDB 后测试仍然失败：

1. 检查端口 27017 是否可用：
   ```bash
   netstat -an | findstr 27017
   ```

2. 测试 MongoDB 连接：
   ```bash
   docker exec -it mongodb mongosh --eval "db.adminCommand('ping')"
   ```

3. 检查防火墙设置（确保端口 27017 未被阻止）

### 属性测试仍然跳过

如果测试仍然被跳过：

1. 验证 MongoDB 可访问：
   ```bash
   # 如需要安装 mongosh
   mongosh --eval "db.adminCommand('ping')"
   ```

2. 检查测试输出中的特定错误消息

3. 确保没有其他服务使用端口 27017

## 属性测试验证的内容

一旦 MongoDB 运行，属性测试将验证：

- **属性 9**：AI 分析响应包含有效分数（0.0-1.0）和非空推理
- **属性 10**：改进建议总是返回至少一个推荐
- **属性 11**：生成的配置是具有适当结构的有效字典
- **属性 12**：分析结果正确持久化到 MongoDB，带有 TTL

每个测试使用随机生成的输入运行 100 次迭代，以确保全面覆盖。

## 当前测试结果

✅ **单元测试**：11/11 通过（无需外部依赖）
⏸️ **属性测试**：4/4 已编写但未运行（需要 MongoDB）

单元测试提供了核心功能的良好覆盖。属性测试通过使用广泛的随机输入进行测试来增加额外的信心。