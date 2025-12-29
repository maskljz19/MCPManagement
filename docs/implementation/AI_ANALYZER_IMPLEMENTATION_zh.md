# AI 分析器实现

## 概览

AI 分析器组件已成功实现，集成了 LangChain 和 OpenAI。本文档提供实现详情和测试方法。

## 实现详情

### 创建的文件

1. **`app/services/ai_analyzer.py`** - 主要的 AI 分析器服务
   - LangChain ChatOpenAI 集成
   - 带结构化输出解析的可行性分析
   - 改进建议生成
   - 自动配置生成
   - 在 MongoDB 中持久化结果，支持 TTL

2. **`tests/property/test_ai_analysis_properties.py`** - 基于属性的测试
   - 属性 9：AI 分析响应完整性
   - 属性 10：改进建议非空
   - 属性 11：生成配置有效性
   - 属性 12：分析结果持久性

### 主要功能

#### 1. LangChain 集成
- 使用 `ChatOpenAI` 与 GPT-4 模型
- 温度设置为 0.2，确保一致、专注的响应
- 使用 Pydantic 模型进行结构化输出解析
- 不同分析任务的提示模板

#### 2. 可行性分析
- 分析 MCP 配置的可行性
- 返回结构化报告，包含：
  - 可行性分数（0.0 到 1.0）
  - 布尔可行性标志
  - 详细推理
  - 识别的风险
  - 建议

#### 3. 改进建议
- 生成可操作的改进建议
- 每个建议包括：
  - 类别（性能、安全、可用性等）
  - 标题和描述
  - 优先级（低、中、高、关键）
  - 工作量估计（低、中、高）
  - 影响评估（低、中、高）

#### 4. 配置生成
- 从需求生成有效的 MCP 配置
- 根据 MCP 规范结构进行验证
- 包括服务器、工具和可选提示

#### 5. 结果持久化
- 在 MongoDB 中存储分析结果
- 自动 TTL（生存时间）进行清理
- 支持通过 task_id 检索
- TTL 索引用于自动过期

## 测试

### 前置条件

属性测试需要 MongoDB 运行。您有两个选择：

#### 选项 1：Docker（推荐）

使用 Docker 启动 MongoDB：

```bash
# 启动 MongoDB
docker run -d --name mongodb -p 27017:27017 mongo:latest

# 验证运行状态
docker ps | grep mongodb
```

#### 选项 2：本地安装

本地安装 MongoDB 并确保在 `localhost:27017` 上运行。

### 运行测试

一旦 MongoDB 运行：

```bash
# 运行所有 AI 分析器属性测试
pytest tests/property/test_ai_analysis_properties.py -v

# 运行特定测试
pytest tests/property/test_ai_analysis_properties.py::test_analysis_response_completeness -v

# 运行带 Hypothesis 统计的测试
pytest tests/property/test_ai_analysis_properties.py -v --hypothesis-show-statistics
```

### 测试配置

每个属性测试：
- 使用随机生成的输入运行 100 次迭代
- 使用模拟的 LLM 响应以避免 API 成本
- 测试所有有效输入的通用属性
- 根据设计文档的要求进行验证

### 属性测试

#### 属性 9：AI 分析响应完整性
**验证：要求 3.1**

对于提交进行可行性分析的任何 MCP 配置，响应应包含：
- 0.0 到 1.0 之间的分数
- 非空推理文本
- 布尔可行性标志
- 风险和建议列表

#### 属性 10：改进建议非空
**验证：要求 3.2**

对于提交进行改进分析的任何工具，响应应包含：
- 至少一个改进建议
- 每个建议都有所有必需字段
- 有效的优先级、工作量和影响值

#### 属性 11：生成配置有效性
**验证：要求 3.3**

对于任何配置要求，自动生成的 MCP 配置应该：
- 是有效的字典
- 包含服务器或工具
- 每个组件都有适当的结构

#### 属性 12：分析结果持久性
**验证：要求 3.5**

对于任何完成的 AI 分析任务：
- MongoDB 应包含结果文档
- 文档应有匹配的 task_id
- TTL 应正确设置
- 所有必需字段应存在

## 使用示例

```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.services.ai_analyzer import AIAnalyzer
from app.schemas.ai_analysis import ConfigRequirements

# 初始化
mongo_client = AsyncIOMotorClient("mongodb://localhost:27017")
analyzer = AIAnalyzer(
    mongo_client=mongo_client,
    openai_api_key="your-api-key"
)

# 确保 TTL 索引存在（启动时调用一次）
await analyzer.ensure_ttl_index()

# 分析可行性
config = {
    "servers": [{"name": "main", "url": "http://localhost:8000"}],
    "tools": [{"name": "example", "description": "示例工具"}]
}
report = await analyzer.analyze_feasibility(config)
print(f"可行性: {report.is_feasible}, 分数: {report.score}")

# 获取改进建议
improvements = await analyzer.suggest_improvements(
    tool_name="我的工具",
    description="用于测试的工具",
    config=config
)
for improvement in improvements:
    print(f"{improvement.title}: {improvement.description}")

# 生成配置
requirements = ConfigRequirements(
    tool_name="新工具",
    description="一个新的 MCP 工具",
    capabilities=["数据处理", "API 集成"],
    constraints={}
)
generated_config = await analyzer.generate_config(requirements)

# 存储结果
from uuid import uuid4
task_id = uuid4()
await analyzer.store_analysis_result(
    task_id=task_id,
    task_type="feasibility",
    result=report,
    ttl_hours=24
)

# 稍后检索结果
stored_result = await analyzer.get_analysis_result(task_id)
```

## 配置

AI 分析器需要以下环境变量：

```bash
# 必需
OPENAI_API_KEY=sk-your-api-key-here

# MongoDB 连接
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=mcp_platform
```

## 错误处理

服务包括强大的错误处理：

1. **缺少 API 密钥**：如果未提供 OpenAI API 密钥，抛出 `ValueError`
2. **JSON 解析**：回退到从 markdown 代码块提取 JSON
3. **LLM 失败**：传播异常以进行适当的重试处理
4. **MongoDB 错误**：允许数据库错误传播以进行适当处理

## 性能考虑

1. **LLM 调用**：每次分析进行一次 LLM API 调用
   - 可行性分析：约 2-5 秒
   - 改进建议：约 3-7 秒
   - 配置生成：约 2-5 秒

2. **MongoDB 操作**：快速（通常 < 100ms）
   - 带 TTL 的文档插入
   - 通过 task_id 检索文档

3. **异步操作**：所有方法都是异步的，用于非阻塞 I/O

## 未来增强

未来迭代的潜在改进：

1. **缓存**：为相同配置缓存分析结果
2. **批处理**：支持多个工具的批量分析
3. **流式传输**：流式传输 LLM 响应以获得实时反馈
4. **模型选择**：允许可配置的 LLM 模型（GPT-3.5、GPT-4 等）
5. **提示优化**：基于反馈微调提示
6. **验证**：添加更复杂的配置验证
7. **指标**：跟踪分析质量和性能指标

## 故障排除

### 测试被跳过

如果测试显示"MongoDB 不可用"：
1. 确保 MongoDB 在 `localhost:27017` 上运行
2. 使用以下命令检查连接：`mongosh --eval "db.adminCommand('ping')"`
3. 验证没有防火墙阻止端口 27017

### LLM API 错误

如果遇到 OpenAI API 错误：
1. 验证 `OPENAI_API_KEY` 设置正确
2. 检查 API 密钥有足够的额度
3. 验证到 OpenAI API 的网络连接
4. 检查是否超出速率限制

### JSON 解析错误

如果 LLM 响应解析失败：
1. 服务包括 markdown 代码块的回退解析
2. 检查 LLM 温度（较低 = 更一致）
3. 查看提示模板的清晰度
4. 考虑在提示中添加更多示例

## 参考

- [LangChain 文档](https://python.langchain.com/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [Hypothesis 测试指南](https://hypothesis.readthedocs.io/)
- 设计文档：`.kiro/specs/mcp-platform-backend/design.md`
- 需求文档：`.kiro/specs/mcp-platform-backend/requirements.md`