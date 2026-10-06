"""phase12 conversation engine (conversations, turns, and objections migration)

Revision ID: b12e0fa53d21
Revises: a11c0de42b10
Create Date: 2026-10-06 17:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b12e0fa53d21'
down_revision: Union[str, None] = 'a11c0de42b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. conversations table
    if 'conversations' not in existing_tables:
        op.create_table(
            'conversations',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=True),
            sa.Column('student_id', sa.Integer(), nullable=False),
            sa.Column('lang', sa.String(length=10), server_default='hi', nullable=False),
            sa.Column('status', sa.String(length=20), server_default='active', nullable=False),
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
            sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['student_id'], ['students.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('conversations', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_conversations_room_id'), ['room_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_conversations_student_id'), ['student_id'], unique=False)

    # 2. turns table
    if 'turns' not in existing_tables:
        op.create_table(
            'turns',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('conversation_id', sa.Integer(), nullable=False),
            sa.Column('speaker', sa.String(length=16), nullable=False),
            sa.Column('text', sa.Text(), nullable=False),
            sa.Column('lang', sa.String(length=10), server_default='hi', nullable=False),
            sa.Column('intent', sa.String(length=32), nullable=True),
            sa.Column('topic', sa.String(length=32), nullable=True),
            sa.Column('sentiment', sa.String(length=16), nullable=True),
            sa.Column('facts_json', sa.JSON(), nullable=True),
            sa.Column('fallback_used', sa.Boolean(), server_default='0', nullable=False),
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
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('turns', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_turns_conversation_id'), ['conversation_id'], unique=False)

    # 3. objections table (migrate Objection model if not already created)
    if 'objections' not in existing_tables:
        op.create_table(
            'objections',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('room_id', sa.Integer(), nullable=False),
            sa.Column('raised_by_user_id', sa.Integer(), nullable=False),
            sa.Column('occupation_id', sa.Integer(), nullable=True),
            sa.Column('topic', sa.String(length=16), nullable=False),
            sa.Column('sentiment', sa.String(length=12), nullable=False),
            sa.Column('note', sa.Text(), nullable=True),
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
            sa.ForeignKeyConstraint(['occupation_id'], ['occupations.id'], ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['raised_by_user_id'], ['users.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('objections', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_objections_room_id'), ['room_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_objections_raised_by_user_id'), ['raised_by_user_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_objections_occupation_id'), ['occupation_id'], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if 'turns' in existing_tables:
        with op.batch_alter_table('turns', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_turns_conversation_id'))
        op.drop_table('turns')

    if 'conversations' in existing_tables:
        with op.batch_alter_table('conversations', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_conversations_student_id'))
            batch_op.drop_index(batch_op.f('ix_conversations_room_id'))
        op.drop_table('conversations')

    if 'objections' in existing_tables:
        with op.batch_alter_table('objections', schema=None) as batch_op:
            batch_op.drop_index(batch_op.f('ix_objections_occupation_id'))
            batch_op.drop_index(batch_op.f('ix_objections_raised_by_user_id'))
            batch_op.drop_index(batch_op.f('ix_objections_room_id'))
        op.drop_table('objections')
