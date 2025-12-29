# Database Migrations

This directory contains Alembic database migrations for the MCP Platform.

## Setup

1. Ensure your database connection is configured in `.env`:
   ```
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=mcp_platform
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Apply all migrations
```bash
alembic upgrade head
```

### Create a new migration
```bash
alembic revision --autogenerate -m "description of changes"
```

### Rollback one migration
```bash
alembic downgrade -1
```

### Show current revision
```bash
alembic current
```

### Show migration history
```bash
alembic history
```

### Using the helper script
```bash
# Create new migration
python scripts/migrate.py create "add new column"

# Apply migrations
python scripts/migrate.py upgrade

# Rollback
python scripts/migrate.py downgrade -1

# Show current
python scripts/migrate.py current

# Show history
python scripts/migrate.py history
```

## Migration Files

- `env.py`: Alembic environment configuration
- `script.py.mako`: Template for new migration files
- `versions/`: Directory containing migration scripts

## Notes

- Always review auto-generated migrations before applying
- Test migrations in development before production
- Migrations are executed in order based on revision IDs
- Each migration has an `upgrade()` and `downgrade()` function
