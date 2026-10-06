"""phase13 sentiment, resistance snapshots, and scheme_admin role

Revision ID: c13e0fa64e22
Revises: b12e0fa53d21
Create Date: 2026-10-06 18:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c13e0fa64e22'
down_revision: Union[str, None] = 'b12e0fa53d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Add intensity column to turns table
    if 'turns' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('turns')]
        if 'intensity' not in columns:
            with op.batch_alter_table('turns', schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column('intensity', sa.Float(), server_default='0.0', nullable=False)
                )

    # 2. Create rs_snapshots table
    if 'rs_snapshots' not in existing_tables:
        op.create_table(
            'rs_snapshots',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('turn_id', sa.Integer(), nullable=False),
            sa.Column('rs', sa.Float(), nullable=False),
            sa.Column(
                'created_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
                nullable=False,
            ),
            sa.Column(
                'updated_at',
                sa.DateTime(timezone=True),
                server_default=sa.text('(CURRENT_TIMESTAMP)'),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['turn_id'], ['turns.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('rs_snapshots', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_rs_snapshots_conversation_id'), ['conversation_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_rs_snapshots_turn_id'), ['turn_id'], unique=False)

    # 3. Update users table check constraint for role to include scheme_admin
    # In SQLite batch mode, recreating table preserves existing data with new check constraint
    if 'users' in existing_tables:
        with op.batch_alter_table('users', schema=None) as batch_op:
            # Drop existing check constraint if supported/named
            try:
                batch_op.drop_constraint('ck_user_role', type_='check')
            except Exception:
                pass
            batch_op.create_check_constraint(
                'ck_user_role',
                "role IN ('student', 'parent', 'counsellor', 'admin', 'scheme_admin')",
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'rs_snapshots' in existing_tables:
        with op.batch_alter_table('rs_snapshots', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_rs_snapshots_turn_id'))
            batch_op.drop_index(batch_op.f('ix_rs_snapshots_conversation_id'))
        op.drop_table('rs_snapshots')

    if 'turns' in existing_tables:
        columns = [c['name'] for c in inspector.get_columns('turns')]
        if 'intensity' in columns:
            with op.batch_alter_table('turns', schema=None) as batch_op:
                batch_op.drop_column('intensity')

    if 'users' in existing_tables:
        with op.batch_alter_table('users', schema=None) as batch_op:
            try:
                batch_op.drop_constraint('ck_user_role', type_='check')
            except Exception:
                pass
            batch_op.create_check_constraint(
                'ck_user_role',
                "role IN ('student', 'parent', 'counsellor', 'admin')",
            )
