# MCP 平台后端基于属性的测试

此目录包含使用 Hypothesis 的基于属性的测试，用于验证设计文档中定义的正确性属性。

## 概览

基于属性的测试验证应该对所有有效输入都成立的通用属性，而不是测试特定示例。每个测试使用随机生成的输入运行 100 次迭代，以确保全面覆盖。

## 测试文件

- `test_mcp_properties.py` - MCP 管理器测试（工具 CRUD、版本控制、缓存）
- `test_auth_properties.py` - 身份验证服务测试（JWT、API 密钥、权限）
- `test_cache_properties.py` - 缓存服务测试（Redis 操作、TTL、失效）
- `test_database_properties.py` - 数据库操作测试（连接、事务）
- `test_migration_properties.py` - Alembic 迁移测试（执行、回滚）
- `test_validation_properties.py` - 输入验证测试（Pydantic 模式）
- `test_knowledge_properties.py` - 知识库服务测试（文档、嵌入、搜索）

## 前置条件

### 所需服务

属性测试需要以下服务运行：

1. **MongoDB**（localhost:27017）
   - 用于文档存储和版本历史
   - 如果 MongoDB 不可用，测试将被跳过

2. **Redis**（localhost:6379）
   - 用于缓存和会话管理
   - 如果 Redis 不可用，测试将被跳过

3. **Qdrant**（可选，测试使用内存模式）
   - 用于向量存储和语义搜索
   - 测试使用内存中的 Qdrant 客户端

### 使用 Docker 启动服务

```bash
# 启动 MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:latest

# 启动 Redis
docker run -d --name redis -p 6379:6379 redis:latest

# 可选：启动 Qdrant（如果不使用内存模式）
docker run -d --name qdrant -p 6333:6333 qdrant/qdrant:latest
```

### 环境变量

对于使用真实 OpenAI 嵌入的知识库测试：

```bash
export OPENAI_API_KEY=sk-your-api-key-here
```

如果未设置 `OPENAI_API_KEY`，测试将使用确定性模拟嵌入。

## 运行测试

### 运行所有属性测试

```bash
pytest tests/property/ -v
```

### 运行特定测试文件

```bash
pytest tests/property/test_knowledge_properties.py -v
```

### 运行特定测试

```bash
pytest tests/property/test_knowledge_properties.py::test_dual_store_document_consistency -v
```

### 运行带覆盖率的测试

```bash
pytest tests/property/ --cov=app --cov-report=html
```

### 运行带 Hypothesis 统计的测试

```bash
pytest tests/property/ -v --hypothesis-show-statistics
```

## 测试配置

属性测试在 `pytest.ini` 中配置：

```ini
[pytest]
markers =
    property: 使用 Hypothesis 的基于属性的测试
    asyncio: 异步测试

# Hypothesis 设置
hypothesis_profile = default
```

每个测试使用这些 Hypothesis 设置：
- `max_examples=100` - 每个测试运行 100 次迭代
- `deadline=None` - 每个示例无时间限制
- `suppress_health_check=[HealthCheck.function_scoped_fixture]` - 允许函数作用域夹具

## 属性测试结构

每个属性测试遵循此结构：

```python
# 功能：mcp-platform-backend，属性 N：属性名称
@given(input_data=strategy())
@settings(max_examples=100, deadline=None)
@pytest.mark.asyncio
async def test_property_name(input_data, fixture):
    """
    属性 N：属性名称
    
    对于任何 <输入>，<属性应该成立>。
    
    验证：要求 X.Y
    """
    # 准备
    # 执行
    # 断言
```

## 知识库服务测试

### 属性 5：双存储文档一致性
验证文档在 MongoDB 和 Qdrant 中都存储，且 ID 匹配。

### 属性 6：搜索结果排序
验证搜索结果按相似度分数降序排列。

### 属性 7：文档删除一致性
验证删除时文档从 MongoDB 和 Qdrant 中都被移除。

### 属性 8：嵌入维度一致性
验证所有嵌入具有相同维度（text-embedding-3-small 为 1536）。

## 故障排除

### 测试被跳过

如果测试被跳过，显示"MongoDB 不可用"或"Redis 不可用"等消息：

1. 确保所需服务正在运行
2. 检查 `tests/conftest.py` 中的连接设置
3. 验证到 localhost 的网络连接

### Hypothesis 发现失败

当 Hypothesis 发现失败示例时：

1. 测试输出将显示最小失败案例
2. Hypothesis 将在 `.hypothesis/examples/` 中保存示例
3. 在未来运行中，相同示例将首先被测试
4. 修复实现或调整属性
5. 重新运行测试以验证修复

### 测试缓慢

属性测试可能很慢，因为它们运行 100 次迭代。在开发期间加速：

```python
@settings(max_examples=10)  # 临时减少迭代
```

### 内存问题

如果测试消耗过多内存：

1. 在测试设置中减少 `max_examples`
2. 确保夹具中的适当清理
3. 检查实现中的资源泄漏

## 持续集成

在 CI 环境中：

1. 在运行测试之前启动所需服务（MongoDB、Redis）
2. 使用 Docker Compose 进行服务编排
3. 为服务启动设置适当的超时
4. 每晚运行扩展属性测试（1000 次迭代）

示例 CI 配置：

```yaml
# .github/workflows/test.yml
- name: 启动服务
  run: docker-compose up -d mongodb redis

- name: 等待服务
  run: |
    timeout 30 bash -c 'until docker exec mongodb mongosh --eval "db.adminCommand(\"ping\")"; do sleep 1; done'
    timeout 30 bash -c 'until docker exec redis redis-cli ping; do sleep 1; done'

- name: 运行属性测试
  run: pytest tests/property/ -v --hypothesis-profile=ci
```

## 参考

- [Hypothesis 文档](https://hypothesis.readthedocs.io/)
- [基于属性的测试指南](https://hypothesis.works/articles/what-is-property-based-testing/)
- [设计文档](../../.kiro/specs/mcp-platform-backend/design.md) - 查看正确性属性部分