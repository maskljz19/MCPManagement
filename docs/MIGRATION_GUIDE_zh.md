# 文档迁移指南

## 📋 概览

本指南帮助您找到已移动到新组织结构的文档。

## 🔄 文件位置更改

### 之前 → 之后

#### API 文档
```
API_EXAMPLES.md → docs/api/API_EXAMPLES_zh.md
```

#### 实现指南
```
AI_ANALYZER_IMPLEMENTATION.md              → docs/implementation/AI_ANALYZER_IMPLEMENTATION_zh.md
AI_ANALYSIS_ENDPOINTS_IMPLEMENTATION.md    → docs/implementation/AI_ANALYSIS_ENDPOINTS_IMPLEMENTATION_zh.md
CACHE_IMPLEMENTATION.md                    → docs/implementation/CACHE_IMPLEMENTATION_zh.md
DEPLOYMENT_ENDPOINTS_IMPLEMENTATION.md     → docs/implementation/DEPLOYMENT_ENDPOINTS_IMPLEMENTATION_zh.md
KNOWLEDGE_BASE_IMPLEMENTATION.md           → docs/implementation/KNOWLEDGE_BASE_IMPLEMENTATION_zh.md
KNOWLEDGE_ENDPOINTS_IMPLEMENTATION.md      → docs/implementation/KNOWLEDGE_ENDPOINTS_IMPLEMENTATION_zh.md
MCP_SERVER_MANAGER_IMPLEMENTATION.md       → docs/implementation/MCP_SERVER_MANAGER_IMPLEMENTATION_zh.md
MONITORING_IMPLEMENTATION.md               → docs/implementation/MONITORING_IMPLEMENTATION_zh.md
WEBSOCKET_SSE_IMPLEMENTATION.md            → docs/implementation/WEBSOCKET_SSE_IMPLEMENTATION_zh.md
```

#### 设置和部署
```
SETUP_COMPLETE.md          → docs/setup/SETUP_COMPLETE_zh.md
DOCKER_DEPLOYMENT_GUIDE.md → docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md
```

#### 测试
```
TESTING_NOTES.md → docs/testing/TESTING_NOTES_zh.md
```

#### 开发资源
```
START_MONGODB.md                → docs/development/START_MONGODB_zh.md
CHECKPOINT_15_RESULTS.md        → docs/development/checkpoints/CHECKPOINT_15_RESULTS.md
CHECKPOINT_23_TEST_FAILURES.md  → docs/development/checkpoints/CHECKPOINT_23_TEST_FAILURES.md
TASK_28_1_COMPLETE_SUMMARY.md   → docs/development/checkpoints/TASK_28_1_COMPLETE_SUMMARY.md
TASK_28_1_STATUS.md             → docs/development/checkpoints/TASK_28_1_STATUS.md
```

## 🗂️ 新文档结构

```
docs/
├── README_zh.md                  # 从这里开始 - 文档索引
│
├── api/                          # API 文档
│   └── API_EXAMPLES_zh.md       # 完整的 API 参考和示例
│
├── implementation/               # 实现指南
│   ├── README_zh.md             # 实现文档索引
│   ├── AI_ANALYZER_IMPLEMENTATION_zh.md
│   ├── AI_ANALYSIS_ENDPOINTS_IMPLEMENTATION_zh.md
│   ├── CACHE_IMPLEMENTATION_zh.md
│   ├── DEPLOYMENT_ENDPOINTS_IMPLEMENTATION_zh.md
│   ├── KNOWLEDGE_BASE_IMPLEMENTATION_zh.md
│   ├── KNOWLEDGE_ENDPOINTS_IMPLEMENTATION_zh.md
│   ├── MCP_SERVER_MANAGER_IMPLEMENTATION_zh.md
│   ├── MONITORING_IMPLEMENTATION_zh.md
│   └── WEBSOCKET_SSE_IMPLEMENTATION_zh.md
│
├── setup/                        # 设置指南
│   └── SETUP_COMPLETE_zh.md     # 完整的设置说明
│
├── deployment/                   # 部署指南
│   └── DOCKER_DEPLOYMENT_GUIDE_zh.md  # Docker 部署指南
│
├── testing/                      # 测试文档
│   └── TESTING_NOTES_zh.md      # 测试策略和指导原则
│
└── development/                  # 开发资源
    ├── START_MONGODB_zh.md      # 数据库初始化
    └── checkpoints/             # 开发检查点
        ├── CHECKPOINT_15_RESULTS.md
        ├── CHECKPOINT_23_TEST_FAILURES.md
        ├── TASK_28_1_COMPLETE_SUMMARY.md
        └── TASK_28_1_STATUS.md
```

## 🔍 快速参考

### 我想要...

**了解 API**
→ 转到 [`docs/api/API_EXAMPLES_zh.md`](api/API_EXAMPLES_zh.md)

**设置开发环境**
→ 转到 [`docs/setup/SETUP_COMPLETE_zh.md`](setup/SETUP_COMPLETE_zh.md)

**部署到生产环境**
→ 转到 [`docs/deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md`](deployment/DOCKER_DEPLOYMENT_GUIDE_zh.md)

**了解服务如何工作**
→ 转到 [`docs/implementation/`](implementation/) 并找到相关指南

**编写测试**
→ 转到 [`docs/testing/TESTING_NOTES_zh.md`](testing/TESTING_NOTES_zh.md)

**启动 MongoDB**
→ 转到 [`docs/development/START_MONGODB_zh.md`](development/START_MONGODB_zh.md)

**检查开发历史**
→ 转到 [`docs/development/checkpoints/`](development/checkpoints/)

## 📚 文档类别

### 1. API 文档（`docs/api/`）
所有端点的完整 API 参考，包含请求/响应示例。

### 2. 实现指南（`docs/implementation/`）
每个服务和组件的详细技术文档：
- 服务架构
- 实现详情
- 代码示例
- 最佳实践

### 3. 设置指南（`docs/setup/`）
设置开发环境的分步说明。

### 4. 部署指南（`docs/deployment/`）
生产部署说明，包括 Docker 设置。

### 5. 测试文档（`docs/testing/`）
测试策略、指导原则和最佳实践。

### 6. 开发资源（`docs/development/`）
开发工具、脚本和检查点记录。

## 🔗 更新的链接

主 `README_zh.md` 中的所有链接都已更新为指向新位置。如果您发现任何损坏的链接，请报告。

## 💡 提示

1. **收藏文档 README**：[`docs/README_zh.md`](README_zh.md) 是您的起点
2. **使用搜索**：大多数编辑器支持项目范围搜索（Ctrl+Shift+F）
3. **检查索引**：每个主要部分都有一个带链接的 README_zh.md
4. **遵循结构**：添加新文档时，遵循现有组织

## 🤝 贡献

添加新文档时：
1. 将其放在适当的 `docs/` 子目录中
2. 更新相关的 README_zh.md 索引
3. 如果需要，更新此迁移指南
4. 遵循现有格式和风格

## ❓ 问题？

如果您找不到所需内容：
1. 检查 [`docs/README_zh.md`](README_zh.md) 获取完整索引
2. 使用编辑器的搜索功能
3. 检查 git 历史：`git log --follow -- <old-filename>`