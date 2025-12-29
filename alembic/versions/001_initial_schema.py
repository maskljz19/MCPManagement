"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2024-12-29 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('admin', 'developer', 'viewer', name='userrole'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index('idx_username', 'users', ['username'])
    op.create_index('idx_email', 'users', ['email'])
    
    # Create mcp_tools table
    op.create_table(
        'mcp_tools',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('version', sa.String(50), nullable=False),
        sa.Column('author_id', mysql.CHAR(36), nullable=False),
        sa.Column('status', sa.Enum('draft', 'active', 'deprecated', name='toolstatus'), nullable=False),
        sa.Column('deleted_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index('idx_slug', 'mcp_tools', ['slug'])
    op.create_index('idx_author', 'mcp_tools', ['author_id'])
    op.create_index('idx_status', 'mcp_tools', ['status'])
    
    # Create mcp_deployments table
    op.create_table(
        'mcp_deployments',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=False),
        sa.Column('endpoint_url', sa.String(512), nullable=False),
        sa.Column('status', sa.Enum('starting', 'running', 'stopped', 'failed', name='deploymentstatus'), nullable=False),
        sa.Column('health_status', sa.Enum('healthy', 'unhealthy', 'unknown', name='healthstatus'), nullable=False),
        sa.Column('last_health_check', sa.TIMESTAMP(), nullable=True),
        sa.Column('deployed_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('stopped_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE')
    )
    op.create_index('idx_tool', 'mcp_deployments', ['tool_id'])
    op.create_index('idx_status', 'mcp_deployments', ['status'])
    
    # Create mcp_usage_stats table
    op.create_table(
        'mcp_usage_stats',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=False),
        sa.Column('deployment_id', mysql.CHAR(36), nullable=True),
        sa.Column('endpoint', sa.String(255), nullable=False),
        sa.Column('method', sa.String(10), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('response_time_ms', sa.Integer(), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=True),
        sa.Column('timestamp', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE')
    )
    op.create_index('idx_tool_timestamp', 'mcp_usage_stats', ['tool_id', 'timestamp'])
    op.create_index('idx_deployment', 'mcp_usage_stats', ['deployment_id'])
    
    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('last_used_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('revoked_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    op.create_index('idx_user', 'api_keys', ['user_id'])
    
    # Create github_connections table
    op.create_table(
        'github_connections',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=True),
        sa.Column('repository_url', sa.String(512), nullable=False),
        sa.Column('last_sync_sha', sa.String(40), nullable=True),
        sa.Column('last_sync_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='SET NULL')
    )
    op.create_index('idx_tool', 'github_connections', ['tool_id'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('github_connections')
    op.drop_table('api_keys')
    op.drop_table('mcp_usage_stats')
    op.drop_table('mcp_deployments')
    op.drop_table('mcp_tools')
    op.drop_table('users')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS userrole')
    op.execute('DROP TYPE IF EXISTS toolstatus')
    op.execute('DROP TYPE IF EXISTS deploymentstatus')
    op.execute('DROP TYPE IF EXISTS healthstatus')
