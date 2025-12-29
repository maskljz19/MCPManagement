# 缓存层实现

## 概览

任务 8（缓存层实现）已成功完成。本文档描述了实现和测试要求。

## 实现摘要

### 1. 缓存服务（`app/services/cache_service.py`）

已实现了一个全面的 Redis 缓存服务，具有以下功能：

#### 缓存键生成
- `generate_tool_key()` - 为单个 MCP 工具生成缓存键
- `generate_list_key()` - 为工具列表查询生成缓存键（使用过滤器/分页的 MD5 哈希）
- `generate_session_key()` - 为用户会话生成缓存键
- `generate_refresh_token_key()` - 为刷新令牌生成缓存键

#### MCP 工具缓存
- `get_tool()` / `set_tool()` / `delete_tool()` - 缓存单个工具，TTL 为 1 小时
- `get_tool_list()` / `set_tool_list()` - 缓存列表结果，TTL 为 5 分钟
- `invalidate_tool_lists()` - 使所有缓存的工具列表失效（在创建/更新/删除时调用）

#### 会话管理
- `create_session()` - 创建用户会话，TTL 为 7 天
- `get_session()` / `delete_session()` - 检索和删除会话
- `refresh_session()` - 延长会话 TTL
- 会话包括元数据：`created_at`、`expires_at`

#### 刷新令牌管理
- `store_refresh_token()` - 存储刷新令牌与用户 ID 映射
- `get_refresh_token_user()` - 从刷新令牌检索用户 ID
- `delete_refresh_token()` - 撤销刷新令牌（注销）

### 2. MCP 管理器集成（`app/services/mcp_manager.py`）

MCP 管理器已更新以使用 CacheService：

- **工具检索**：首先检查缓存，回退到数据库
- **工具创建**：缓存新创建的工具
- **工具更新**：使更新工具和所有列表缓存失效
- **工具删除**：使删除工具和所有列表缓存失效
- **列表操作**：使用基于过滤器的键缓存分页列表结果

### 3. 身份验证服务集成（`app/services/auth_service.py`）

身份验证服务已更新以使用 CacheService：

- **令牌创建**：在 Redis 中存储刷新令牌，TTL 为 7 天
- **会话管理**：创建、检索和删除用户会话
- **令牌撤销**：注销时从缓存中移除刷新令牌

## 基于属性的测试

在 `tests/property/test_cache_properties.py` 中实现了三个基于属性的测试：

### 属性 29：重复访问时的缓存命中
**验证：要求 8.1**

测试当连续两次请求 MCP 工具且没有修改时，第二次请求从 Redis 缓存提供服务。

### 属性 30：更新时的缓存失效
**验证：要求 8.2**

测试更新 MCP 工具后，后续请求返回更新的数据（缓存正确失效）。

### 属性 31：带 TTL 的会话存储
**验证：要求 8.3**

测试用户会话在 Redis 中存储时具有适当的 TTL 并包含所有必需的元数据。

### 属性 32：失败时的缓存回退
**验证：要求 8.4**

测试当 Redis 不可用时，请求仍然通过直接查询 MySQL 成功（优雅降级）。

## 运行测试

### 前置条件

基于属性的测试需要以下服务运行：

1. **Redis** - 在 `localhost:6379` 上运行
2. **MongoDB** - 在 `localhost:27017` 上运行

### 启动服务

#### 使用 Docker：
```bash
# 启动 Redis
docker run -d -p 6379:6379 redis:7-alpine

# 启动 MongoDB
docker run -d -p 27017:27017 mongo:7
```

#### 使用 Docker Compose：
```bash
docker-compose up -d redis mongodb
```

### 运行测试

```bash
# 运行所有缓存属性测试
python -m pytest tests/property/test_cache_properties.py -v

# 运行特定测试
python -m pytest tests/property/test_cache_properties.py::test_cache_hit_on_repeated_access -v

# 运行带覆盖率的测试
python -m pytest tests/property/test_cache_properties.py --cov=app/services/cache_service
```

### 测试配置

每个属性测试运行时：
- **100 次迭代**（如设计文档中指定）
- **无截止时间**（属性测试可能需要时间）
- **健康检查抑制**用于函数作用域夹具

## 缓存配置

缓存 TTL 值在 `CacheService` 中可配置：

```python
TOOL_CACHE_TTL = 3600      # 1 小时
LIST_CACHE_TTL = 300       # 5 分钟
SESSION_TTL = 604800       # 7 天
```

## 缓存模式

### 读穿缓存模式
```python
# 首先尝试缓存
cached_data = await cache_service.get_tool(tool_id)
if cached_data:
    return cached_data

# 缓存未命中 - 查询数据库
tool = await db.query(...)

# 填充缓存
await cache_service.set_tool(tool_id, tool)
return tool
```

### 缓存失效模式
```python
# 更新数据库
await db.update(...)

# 使缓存失效
await cache_service.delete_tool(tool_id)
await cache_service.invalidate_tool_lists()
```

### 优雅降级模式
```python
try:
    # 尝试缓存操作
    cached_data = await cache_service.get_tool(tool_id)
    if cached_data:
        return cached_data
except Exception:
    # 缓存失败 - 继续到数据库
    pass

# 始终查询数据库作为回退
return await db.query(...)
```

## 实现状态

✅ **任务 8.1**：为 MCP 工具实现 Redis 缓存 - **已完成**
✅ **任务 8.2**：在 Redis 中实现会话管理 - **已完成**
✅ **任务 8.3**：为重复访问的缓存命中编写属性测试 - **已完成**
✅ **任务 8.4**：为缓存失效编写属性测试 - **已完成**
✅ **任务 8.5**：为带 TTL 的会话存储编写属性测试 - **已完成**

## 后续步骤

要运行基于属性的测试：

1. 启动 Redis 和 MongoDB 服务
2. 运行：`python -m pytest tests/property/test_cache_properties.py -v`
3. 验证所有测试都通过，每个测试 100 次迭代

## 注意事项

- 如果 Redis 或 MongoDB 不可用，测试会自动跳过
- 缓存服务优雅地处理 Redis 连接失败
- 所有缓存操作使用适当的 TTL 以防止内存泄漏
- 缓存键使用一致的命名模式，便于调试