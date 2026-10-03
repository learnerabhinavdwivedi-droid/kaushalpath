"""phase8 audit_logs + feedback sentiment/model_version columns

Adds the Phase 8 persistence the counsellor dashboard and feedback loop need:
- a new append-only ``audit_logs`` table (overrides + data deletions), and
- ``feedback`` columns: ``user_id``, ``topic``, ``sentiment``, ``model_version``
  (the retraining + resistance loop reuses the Phase 7 objection taxonomy).

The dev SQLite DB was patched in-place during the phase; this migration keeps a
fresh ``alembic upgrade head`` in sync with the ORM models.

Revision ID: 7c3f9a2b14e0
Revises: 44f4876304e9
Create Date: 2026-10-03 15:20:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c3f9a2b14e0'
down_revision: Union[str, None] = '44f4876304e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=24), nullable=False),
        sa.Column('entity_type', sa.String(length=24), nullable=False),
        sa.Column('entity_id', sa.String(length=64), nullable=True),
        sa.Column('detail', sa.JSON(), nullable=True),
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
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_audit_logs_actor_user_id'), ['actor_user_id'], unique=False
        )

    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        # Existing rows predate the taxonomy; default them to the neutral tag.
        batch_op.add_column(
            sa.Column('topic', sa.String(length=16), server_default='none', nullable=False)
        )
        batch_op.add_column(
            sa.Column('sentiment', sa.String(length=12), server_default='none', nullable=False)
        )
        batch_op.add_column(sa.Column('model_version', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_feedback_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_feedback_user_id', 'users', ['user_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('feedback', schema=None) as batch_op:
        batch_op.drop_constraint('fk_feedback_user_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_feedback_user_id'))
        batch_op.drop_column('model_version')
        batch_op.drop_column('sentiment')
        batch_op.drop_column('topic')
        batch_op.drop_column('user_id')

    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_audit_logs_actor_user_id'))

    op.drop_table('audit_logs')
