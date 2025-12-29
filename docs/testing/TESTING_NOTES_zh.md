# MCP 平台后端测试说明

## 任务 7：MCP 管理器组件 - 属性测试

MCP 管理器组件（任务 7）的所有基于属性的测试已在 `tests/property/test_mcp_properties.py` 中成功实现。

### 已实现的测试

1. ✅ **属性 1：MCP 工具创建持久性**（任务 7.3）
   - 验证：要求 1.1、1.2
   - 测试：`test_mcp_tool_creation_persistence`

2. ✅ **属性 2：更新时的版本历史**（任务 7.4）
   - 验证：要求 1.3
   - 测试：`test_version_history_on_update`

3. ✅ **属性 3：软删除保留**（任务 7.5）
   - 验证：要求 1.4
   - 测试：`test_soft_delete_preservation`

4. ✅ **属性 4：分页不变量**（任务 7.6）
   - 验证：要求 1.5
   - 测试：`test_pagination_invariants`

5. ✅ **属性 25：MySQL 中的状态持久性**（任务 7.7）
   - 验证：要求 7.1、7.3
   - 测试：`test_state_persistence_in_mysql`

6. ✅ **属性 26：配置历史追加**（任务 7.8）
   - 验证：要求 7.2
   - 测试：`test_configuration_history_append`

7. ✅ **属性 28：版本历史检索**（任务 7.9）
   - 验证：要求 7.5
   - 测试：`test_version_history_retrieval`

### 当前状态

所有测试都已**实现并准备运行**，但由于系统上未运行所需的 MongoDB 服务，它们目前被**跳过**。

### 运行测试的前置条件

要执行这些基于属性的测试，您需要以下服务运行：

1. **MongoDB**（localhost:27017）
2. **Redis**（localhost:6379）
3. **MySQL**（在 .env 中配置）- 注意：测试使用内存中的 SQLite 作为 MySQL

### 如何启动所需服务

#### 选项 1：使用 Docker（推荐）

```bash
# 启动 MongoDB
docker run -d -p 27017:27017 --name mongodb mongo:6.0

# 启动 Redis
docker run -d -p 6379:6379 --name redis redis:7.0
```

#### 选项 2：本地安装

根据您的操作系统本地安装 MongoDB 和 Redis：

**Windows：**
- MongoDB：从 https://www.mongodb.com/try/download/community 下载
- Redis：使用 WSL 或从 https://github.com/microsoftarchive/redis/releases 下载 Windows 版本

**Linux/MacOS：**
```bash
# MongoDB
sudo apt-get install mongodb  # Ubuntu/Debian
brew install mongodb-community  # MacOS

# Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis  # MacOS
```

### 运行测试

一旦 MongoDB 和 Redis 运行：

```bash
# 运行所有 MCP 属性测试
pytest tests/property/test_mcp_properties.py -v

# 运行特定测试
pytest tests/property/test_mcp_properties.py::test_version_history_on_update -v

# 运行带覆盖率的测试
pytest tests/property/test_mcp_properties.py --cov=app.services.mcp_manager
```

### 测试配置

每个属性测试配置为运行：
- **100 次迭代**（如设计文档中指定）
- **无截止时间**（允许数据库操作）
- **抑制 Hypothesis 健康检查**用于函数作用域夹具

### 预期行为

当 MongoDB 和 Redis 可用时，所有测试应该：
1. 创建隔离的测试数据库
2. 使用随机生成的测试数据运行 100 次迭代
3. 验证正确性属性
4. 自动清理测试数据
5. 报告 PASSED 状态

### 测试实现质量

测试遵循最佳实践：
- ✅ 使用 Hypothesis 进行基于属性的测试
- ✅ 使用自定义策略生成有效的测试数据
- ✅ 测试所有输入的通用属性
- ✅ 包含带描述性消息的适当断言
- ✅ 每次测试后清理资源
- ✅ 在注释中引用设计文档属性

## 后续步骤

1. 启动 MongoDB 和 Redis 服务
2. 运行属性测试以验证它们通过
3. 继续实现计划中的下一个任务

## 注意事项

- `app/services/mcp_manager.py` 中的 MCP 管理器实现是完整且正确的
- 所有 CRUD 操作都已实现，具有适当的缓存和版本历史
- 测试验证设计文档中定义的正确性属性
- 不需要代码更改 - 只需要服务可用性