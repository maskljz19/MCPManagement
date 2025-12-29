# 知识库服务实现

## 概览

知识库服务已成功实现，作为 MCP 平台后端规范中任务 9 的一部分。该服务使用双存储架构（MongoDB + Qdrant）提供文档存储、嵌入生成和语义搜索功能。

## 实现摘要

### 实现的组件

#### 1. 知识库服务（`app/services/knowledge_service.py`）

**核心功能：**
- 在 MongoDB 中存储文档和元数据
- 使用 LangChain + OpenAI 生成嵌入
- 在 Qdrant 中存储向量用于语义搜索
- 双存储一致性管理
- 带元数据过滤的语义搜索

**主要方法：**
- `store_document()` - 在 MongoDB 和 Qdrant 中存储文档
- `get_document()` - 从 MongoDB 检索文档
- `delete_document()` - 从两个存储中删除（保持一致性）
- `generate_embeddings()` - 使用 OpenAI 生成嵌入
- `generate_embeddings_batch()` - 批量嵌入生成
- `search_documents()` - 使用向量相似性进行语义搜索

**设计模式：**
- 双存储一致性：确保 MongoDB 和 Qdrant 保持同步
- 失败时回滚：如果任一存储失败，清理部分存储
- 全程异步/等待，用于非阻塞 I/O
- LangChain 抽象，提供嵌入灵活性

#### 2. 基于属性的测试（`tests/property/test_knowledge_properties.py`）

**实现的测试：**

1. **属性 5：双存储文档一致性**
   - 验证：要求 2.1
   - 确保文档在 MongoDB 和 Qdrant 中都存在
   - 验证跨存储的匹配文档 ID

2. **属性 6：搜索结果排序**
   - 验证：要求 2.2
   - 确保结果按相似度分数降序排列
   - 验证分数在有效范围 [0, 1] 内

3. **属性 7：文档删除一致性**
   - 验证：要求 2.4
   - 确保从 MongoDB 和 Qdrant 中删除
   - 验证删除后文档不出现在搜索中

4. **属性 8：嵌入维度一致性**
   - 验证：要求 2.5
   - 确保所有嵌入具有相同维度（1536）
   - 验证批量嵌入生成

**其他测试：**
- 内容片段长度验证
- 元数据过滤正确性

#### 3. 测试基础设施（`tests/conftest.py`）

**添加的夹具：**
- `qdrant_client` - 用于测试的内存 Qdrant 客户端
- `knowledge_service_fixture` - 配置了测试依赖项的服务
- 没有 OpenAI API 密钥时的模拟嵌入生成

## 架构

### 数据流

```
客户端请求
    ↓
知识库服务
    ↓
    ├─→ MongoDB（文档存储）
    │   └─→ 集合：knowledge_base
    │       - document_id（UUID）
    │       - title、content、metadata
    │       - embedding_id（引用）
    │       - 时间戳
    │
    ├─→ LangChain + OpenAI（嵌入生成）
    │   └─→ text-embedding-3-small（1536 维）
    │
    └─→ Qdrant（向量存储）
        └─→ 集合：document_embeddings
            - embedding_id（UUID）
            - vector（1536 个浮点数）
            - payload（document_id、title、metadata）
```

### 双存储一致性

服务在 MongoDB 和 Qdrant 之间保持一致性：

1. **存储时：**
   - 首先插入 MongoDB
   - 生成嵌入
   - 在 Qdrant 中存储向量
   - 如果 Qdrant 失败，回滚 MongoDB 插入

2. **删除时：**
   - 从 MongoDB 获取文档（查找 embedding_id）
   - 从 MongoDB 删除
   - 从 Qdrant 删除向量
   - 两个操作都必须成功

3. **搜索时：**
   - 查询 Qdrant 获取相似向量
   - 从 MongoDB 获取完整文档
   - 合并结果与相似度分数

## 技术栈

- **MongoDB（Motor）**：支持异步的文档存储
- **Qdrant**：用于语义搜索的向量数据库
- **LangChain**：嵌入抽象层
- **OpenAI**：text-embedding-3-small 模型（1536 维）
- **Redis**：缓存层（未来增强）
- **Hypothesis**：基于属性的测试框架

## 配置

### 环境变量

```bash
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=mcp_platform

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=

# OpenAI
OPENAI_API_KEY=sk-your-api-key-here
```

### 集合配置

**MongoDB 集合：`knowledge_base`**
```javascript
{
  document_id: UUID,
  title: String,
  content: String,
  metadata: Object,
  embedding_id: UUID,
  created_at: DateTime,
  updated_at: DateTime
}
```

**Qdrant 集合：`document_embeddings`**
```python
{
  vectors: {
    size: 1536,
    distance: "Cosine"
  },
  payload: {
    document_id: UUID,
    title: String,
    ...metadata
  }
}
```

## API 使用示例

### 存储文档

```python
from app.services.knowledge_service import KnowledgeBaseService
from app.schemas.knowledge import DocumentCreate

# 创建服务实例
kb_service = KnowledgeBaseService(
    mongo_db=mongo_db,
    qdrant_client=qdrant_client,
    redis=redis_client,
    openai_api_key=settings.OPENAI_API_KEY
)

# 存储文档
doc_data = DocumentCreate(
    title="MCP 入门指南",
    content="模型上下文协议（MCP）是...",
    metadata={
        "source": "documentation",
        "author": "张三",
        "tags": ["mcp", "tutorial"]
    }
)

document = await kb_service.store_document(doc_data)
print(f"已存储文档: {document.document_id}")
```

### 搜索文档

```python
from app.schemas.knowledge import SearchQuery

# 执行语义搜索
query = SearchQuery(
    query="如何开始使用 MCP？",
    limit=10,
    filters={"source": "documentation"},
    min_similarity=0.7
)

results = await kb_service.search_documents(query)

for result in results:
    print(f"标题: {result.title}")
    print(f"分数: {result.similarity_score}")
    print(f"片段: {result.content_snippet}")
    print("---")
```

### 删除文档

```python
# 删除文档（从两个存储中移除）
success = await kb_service.delete_document(document_id)
if success:
    print("文档删除成功")
```

## 测试

### 运行属性测试

```bash
# 确保 MongoDB 和 Redis 正在运行
docker run -d -p 27017:27017 mongo:latest
docker run -d -p 6379:6379 redis:latest

# 运行所有知识库属性测试
pytest tests/property/test_knowledge_properties.py -v

# 运行特定属性测试
pytest tests/property/test_knowledge_properties.py::test_dual_store_document_consistency -v

# 运行带 Hypothesis 统计的测试
pytest tests/property/test_knowledge_properties.py -v --hypothesis-show-statistics
```

### 测试配置

- **迭代次数**：每个属性测试 100 次
- **截止时间**：无（无时间限制）
- **模拟嵌入**：未设置 OPENAI_API_KEY 时使用
- **内存 Qdrant**：测试使用内存模式

## 性能考虑

### 嵌入生成

- **单个文档**：每个嵌入约 100-200ms
- **批处理**：对多个文档更高效
- **缓存**：考虑为频繁访问的内容缓存嵌入

### 搜索性能

- **向量搜索**：Qdrant 中 HNSW 索引的 O(log n)
- **元数据过滤**：在向量搜索期间应用
- **结果获取**：并行 MongoDB 查询文档

### 优化策略

1. **批量嵌入生成**
   ```python
   texts = [doc.content for doc in documents]
   embeddings = await kb_service.generate_embeddings_batch(texts)
   ```

2. **异步文档存储**
   ```python
   tasks = [kb_service.store_document(doc) for doc in documents]
   results = await asyncio.gather(*tasks)
   ```

3. **搜索结果缓存**
   - 在 Redis 中缓存频繁查询
   - 文档更新时失效
   - TTL：5-10 分钟

## 错误处理

### 存储失败

```python
try:
    document = await kb_service.store_document(doc_data)
except RuntimeError as e:
    # 发生回滚，两个存储都是一致的
    logger.error(f"存储文档失败: {e}")
```

### 搜索失败

```python
try:
    results = await kb_service.search_documents(query)
except Exception as e:
    # 返回空结果或缓存结果
    logger.error(f"搜索失败: {e}")
    results = []
```

### 嵌入生成失败

```python
try:
    embedding = await kb_service.generate_embeddings(text)
except Exception as e:
    # 使用指数退避重试
    # 或排队异步处理
    logger.error(f"嵌入生成失败: {e}")
```

## 未来增强

### 计划功能

1. **文档更新**
   - 更新内容并重新生成嵌入
   - 维护版本历史

2. **高级搜索**
   - 混合搜索（关键词 + 语义）
   - 重新排序算法
   - 查询扩展

3. **缓存层**
   - 在 Redis 中缓存搜索结果
   - 缓存常见查询的嵌入
   - 实现缓存预热

4. **批量操作**
   - 批量文档上传
   - 批量删除
   - 后台重新索引

5. **监控**
   - 搜索质量指标
   - 嵌入生成延迟
   - 存储一致性检查

### 集成点

1. **API 端点**（任务 18）
   - POST /api/v1/knowledge/documents
   - GET /api/v1/knowledge/documents/{doc_id}
   - DELETE /api/v1/knowledge/documents/{doc_id}
   - POST /api/v1/knowledge/search

2. **AI 分析器**（任务 11）
   - 使用知识库进行上下文检索
   - 使用相关文档增强分析

3. **Celery 任务**（任务 12）
   - 异步嵌入生成
   - 后台文档索引
   - 定期一致性检查

## 要求验证

### 已完成的要求

✅ **要求 2.1**：在 MongoDB 和 Qdrant 中存储文档
- 实现了双存储架构
- 由属性 5 验证

✅ **要求 2.2**：带相似性排序的语义搜索
- 使用 Qdrant 实现向量搜索
- 由属性 6 验证

✅ **要求 2.3**：从 MongoDB 检索文档
- 实现了 get_document 方法
- 在属性测试中测试

✅ **要求 2.4**：从两个存储中删除文档
- 实现了一致删除
- 由属性 7 验证

✅ **要求 2.5**：一致的嵌入生成
- 使用 LangChain + OpenAI 实现
- 由属性 8 验证

## 结论

知识库服务实现已完成，准备与 MCP 平台后端的其余部分集成。所有核心功能都已实现，并具有全面的基于属性的测试，以确保在广泛的输入范围内的正确性。

### 后续步骤

1. **任务 10**：检查点 - 验证核心服务
2. **任务 11**：AI 分析器组件（将使用知识库）
3. **任务 18**：API 端点 - 知识库（通过 REST API 公开服务）

### 创建的文件

- `app/services/knowledge_service.py` - 服务实现
- `tests/property/test_knowledge_properties.py` - 属性测试
- `tests/property/README_zh.md` - 测试文档
- `KNOWLEDGE_BASE_IMPLEMENTATION_zh.md` - 本文档

### 修改的文件

- `tests/conftest.py` - 为知识服务测试添加了夹具