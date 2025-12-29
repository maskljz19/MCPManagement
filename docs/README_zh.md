# MCP 平台后端文档

此目录包含 MCP 平台后端项目的全面文档。

## 🗺️ 快速导航

- **[结构概览](STRUCTURE_OVERVIEW_zh.md)** - 所有文档的可视化地图
- **[迁移指南](MIGRATION_GUIDE_zh.md)** - 查找已移动的文件

## 📚 文档结构

### 入门指南
- [主 README](../README_zh.md) - 项目概览和快速开始指南
- [设置指南](setup/SETUP_COMPLETE_zh.md) - 完整的设置说明
- [Docker 部署](deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md) - Docker 部署指南

### API 文档
- [API 示例](api/API_EXAMPLES_zh.md) - 全面的 API 使用示例
- [身份验证](api/auth_zh.md) - 身份验证和授权
- [MCP 工具](api/mcp-tools_zh.md) - MCP 工具管理端点
- [知识库](api/knowledge_zh.md) - 知识库和搜索端点
- [AI 分析](api/ai-analysis_zh.md) - AI 驱动的分析端点
- [GitHub 集成](api/github_zh.md) - GitHub 集成端点
- [部署](api/deployments_zh.md) - 部署管理端点
- [WebSocket/SSE](api/websocket-sse_zh.md) - 实时通信

### 实现指南
- [AI 分析器](implementation/AI_ANALYZER_IMPLEMENTATION_zh.md) - AI 分析服务实现
- [缓存服务](implementation/CACHE_IMPLEMENTATION_zh.md) - Redis 缓存实现
- [知识库](implementation/KNOWLEDGE_BASE_IMPLEMENTATION_zh.md) - 向量数据库和嵌入
- [MCP 服务器管理器](implementation/MCP_SERVER_MANAGER_IMPLEMENTATION_zh.md) - 动态服务器部署
- [监控](implementation/MONITORING_IMPLEMENTATION_zh.md) - 指标和日志
- [WebSocket/SSE](implementation/WEBSOCKET_SSE_IMPLEMENTATION_zh.md) - 实时通信

### 测试
- [测试指南](testing/TESTING_NOTES_zh.md) - 测试策略和指导原则
- [基于属性的测试](../tests/property/README_zh.md) - 基于属性的测试文档

### 开发
- [检查点](development/checkpoints/) - 开发检查点记录
- [数据库设置](development/START_MONGODB_zh.md) - 数据库初始化

## 🔍 快速链接

### 新开发者
1. 阅读 [主 README](../README_zh.md)
2. 遵循 [设置指南](setup/SETUP_COMPLETE_zh.md)
3. 查看 [API 示例](api/API_EXAMPLES_zh.md)
4. 检查 [测试指南](testing/TESTING_NOTES_zh.md)

### API 用户
1. [API 示例](api/API_EXAMPLES_zh.md) - 完整的 API 参考和示例
2. [身份验证](api/auth_zh.md) - 如何进行身份验证
3. `api/` 文件夹中的特定端点文档

### 贡献者
1. [测试指南](testing/TESTING_NOTES_zh.md)
2. `implementation/` 文件夹中的实现指南
3. [开发检查点](development/checkpoints/)

## 📝 文档标准

所有文档都遵循以下标准：
- 清晰、简洁的语言
- 带有解释的代码示例
- 适当的分步说明
- 相关文档的链接
- 随代码更改而更新

## 🤝 贡献文档

添加或更新文档时：
1. 将文件放在适当的子目录中
2. 使用新文档的链接更新此 README
3. 遵循现有格式和风格
4. 在有帮助的地方包含代码示例
5. 保持文档与代码更改同步