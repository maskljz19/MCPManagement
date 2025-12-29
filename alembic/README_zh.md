# 数据库迁移

此目录包含 MCP 平台的 Alembic 数据库迁移。

## 设置

1. 确保在 `.env` 中配置了数据库连接：
   ```
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=mcp_platform
   ```

2. 安装依赖项：
   ```bash
   pip install -r requirements.txt
   ```

## 使用

### 应用所有迁移
```bash
alembic upgrade head
```

### 创建新迁移
```bash
alembic revision --autogenerate -m "更改描述"
```

### 回滚一个迁移
```bash
alembic downgrade -1
```

### 显示当前版本
```bash
alembic current
```

### 显示迁移历史
```bash
alembic history
```

### 使用辅助脚本
```bash
# 创建新迁移
python scripts/migrate.py create "添加新列"

# 应用迁移
python scripts/migrate.py upgrade

# 回滚
python scripts/migrate.py downgrade -1

# 显示当前版本
python scripts/migrate.py current

# 显示历史
python scripts/migrate.py history
```

## 迁移文件

- `env.py`：Alembic 环境配置
- `script.py.mako`：新迁移文件的模板
- `versions/`：包含迁移脚本的目录

## 注意事项

- 应用前始终检查自动生成的迁移
- 在生产环境之前在开发环境中测试迁移
- 迁移根据版本 ID 按顺序执行
- 每个迁移都有 `upgrade()` 和 `downgrade()` 函数