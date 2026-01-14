"""MCP execution enhancements

Revision ID: 002
Revises: 001
Create Date: 2026-01-03 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create execution_queue table
    op.create_table(
        'execution_queue',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_name', sa.String(255), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('options', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('queued', 'processing', 'completed', 'failed', 'cancelled', name='queue_status'),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('queue_position', sa.Integer(), nullable=True),
        sa.Column('estimated_wait_seconds', sa.Integer(), nullable=True),
        sa.Column('queued_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # Indexes for performance optimization
    op.create_index('idx_status_priority', 'execution_queue', ['status', 'priority'], mysql_length={'priority': None})
    op.create_index('idx_user_status', 'execution_queue', ['user_id', 'status'])
    op.create_index('idx_tool_status', 'execution_queue', ['tool_id', 'status'])
    op.create_index('idx_queued_at', 'execution_queue', ['queued_at'])
    
    # Create batch_executions table
    op.create_table(
        'batch_executions',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('total_tools', sa.Integer(), nullable=False),
        sa.Column('completed_tools', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_tools', sa.Integer(), nullable=False, server_default='0'),
        sa.Column(
            'status',
            sa.Enum('queued', 'running', 'completed', 'failed', 'cancelled', name='batch_status'),
            nullable=False,
            server_default='queued'
        ),
        sa.Column('stop_on_error', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('started_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('completed_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # Indexes for performance optimization
    op.create_index('idx_user_status', 'batch_executions', ['user_id', 'status'])
    op.create_index('idx_created_at', 'batch_executions', ['created_at'])
    
    # Create scheduled_executions table
    op.create_table(
        'scheduled_executions',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_name', sa.String(255), nullable=False),
        sa.Column('arguments', sa.JSON(), nullable=False),
        sa.Column('schedule_expression', sa.String(255), nullable=False),
        sa.Column('next_execution_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('last_execution_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('last_execution_status', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    # Indexes for performance optimization
    op.create_index('idx_next_execution', 'scheduled_executions', ['next_execution_at', 'is_active'])
    op.create_index('idx_user_active', 'scheduled_executions', ['user_id', 'is_active'])
    op.create_index('idx_tool_active', 'scheduled_executions', ['tool_id', 'is_active'])
    
    # Create execution_costs table
    op.create_table(
        'execution_costs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('execution_id', mysql.CHAR(36), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('tool_id', mysql.CHAR(36), nullable=False),
        sa.Column('cost_amount', sa.DECIMAL(10, 4), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='USD'),
        sa.Column('duration_seconds', sa.Float(), nullable=False),
        sa.Column('cpu_cores', sa.Float(), nullable=False),
        sa.Column('memory_mb', sa.Integer(), nullable=False),
        sa.Column('calculated_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tool_id'], ['mcp_tools.id'], ondelete='CASCADE')
    )
    # Indexes for performance optimization
    op.create_index('idx_execution_id', 'execution_costs', ['execution_id'])
    op.create_index('idx_user_date', 'execution_costs', ['user_id', 'calculated_at'])
    op.create_index('idx_tool_date', 'execution_costs', ['tool_id', 'calculated_at'])
    
    # Create resource_quotas table
    op.create_table(
        'resource_quotas',
        sa.Column('id', mysql.CHAR(36), nullable=False),
        sa.Column('user_id', mysql.CHAR(36), nullable=False),
        sa.Column('max_cpu_cores', sa.Float(), nullable=False, server_default='4.0'),
        sa.Column('max_memory_mb', sa.Integer(), nullable=False, server_default='4096'),
        sa.Column('max_concurrent_executions', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_daily_executions', sa.Integer(), nullable=False, server_default='1000'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column(
            'updated_at',
            sa.TIMESTAMP(),
            nullable=False,
            server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP')
        ),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', name='uk_user')
    )
    # Index for performance optimization
    op.create_index('idx_user_id', 'resource_quotas', ['user_id'])


def downgrade() -> None:
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table('resource_quotas')
    op.drop_table('execution_costs')
    op.drop_table('scheduled_executions')
    op.drop_table('batch_executions')
    op.drop_table('execution_queue')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS queue_status')
    op.execute('DROP TYPE IF EXISTS batch_status')
