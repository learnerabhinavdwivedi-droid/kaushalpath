"""phase14 human escalation (lifecycle, contact, routing, case pack)

Revision ID: d14e0fa75f33
Revises: c13e0fa64e22
Create Date: 2026-10-06 19:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd14e0fa75f33'
down_revision: Union[str, None] = 'c13e0fa64e22'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Phase 14 columns added to the escalations table.
_NEW_COLUMNS = [
    ('contact_phone', sa.String(length=24), True),
    ('preferred_language', sa.String(length=8), True),
    ('preferred_slot', sa.String(length=40), True),
    ('channel', sa.String(length=10), False),
    ('priority', sa.String(length=8), False),
    ('case_pack_json', sa.JSON(), True),
    ('notes', sa.Text(), True),
    ('claimed_at', sa.DateTime(timezone=True), True),
    ('contacted_at', sa.DateTime(timezone=True), True),
    ('resolved_at', sa.DateTime(timezone=True), True),
]


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'escalations' not in set(inspector.get_table_names()):
        return

    columns = {c['name'] for c in inspector.get_columns('escalations')}

    with op.batch_alter_table('escalations', schema=None) as batch_op:
        # 1. Drop the old uniqueness so a resolved case never blocks a fresh one
        #    (open-case de-duplication now lives in escalation_svc).
        existing_uq = {u['name'] for u in inspector.get_unique_constraints('escalations')}
        if 'uq_escalation' in existing_uq:
            batch_op.drop_constraint('uq_escalation', type_='unique')

        # 2. room_id becomes nullable (conversation-originated cases have no room).
        batch_op.alter_column(
            'room_id', existing_type=sa.Integer(), nullable=True
        )
        # 3. widen status for the new lifecycle values (assigned/contacted/unreachable).
        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=12),
            type_=sa.String(length=16),
            existing_nullable=False,
        )

        # 4. conversation_id FK + index.
        if 'conversation_id' not in columns:
            batch_op.add_column(sa.Column('conversation_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                'fk_escalations_conversation_id',
                'conversations',
                ['conversation_id'],
                ['id'],
                ondelete='CASCADE',
            )
            batch_op.create_index(
                batch_op.f('ix_escalations_conversation_id'), ['conversation_id'], unique=False
            )

        # 5. the hand-off columns.
        for name, coltype, nullable in _NEW_COLUMNS:
            if name not in columns:
                if name == 'channel':
                    batch_op.add_column(
                        sa.Column(name, coltype, server_default='callback', nullable=nullable)
                    )
                elif name == 'priority':
                    batch_op.add_column(
                        sa.Column(name, coltype, server_default='normal', nullable=nullable)
                    )
                else:
                    batch_op.add_column(sa.Column(name, coltype, nullable=nullable))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if 'escalations' not in set(inspector.get_table_names()):
        return

    columns = {c['name'] for c in inspector.get_columns('escalations')}

    with op.batch_alter_table('escalations', schema=None) as batch_op:
        for name, _coltype, _nullable in _NEW_COLUMNS:
            if name in columns:
                batch_op.drop_column(name)

        if 'conversation_id' in columns:
            try:
                batch_op.drop_index(batch_op.f('ix_escalations_conversation_id'))
            except Exception:
                pass
            batch_op.drop_constraint('fk_escalations_conversation_id', type_='foreignkey')
            batch_op.drop_column('conversation_id')

        batch_op.alter_column(
            'status',
            existing_type=sa.String(length=16),
            type_=sa.String(length=12),
            existing_nullable=False,
        )
        batch_op.alter_column(
            'room_id', existing_type=sa.Integer(), nullable=False
        )
        batch_op.create_unique_constraint(
            'uq_escalation', ['room_id', 'raised_by_user_id', 'reason']
        )
