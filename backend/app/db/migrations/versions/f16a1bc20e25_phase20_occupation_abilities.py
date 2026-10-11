"""Phase 20 Grounded Aptitude: occupation_abilities requirement table.

Revision ID: f16a1bc20e25
Revises: e15f0ab19e24
Create Date: 2026-10-11 10:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f16a1bc20e25'
down_revision: Union[str, None] = 'e15f0ab19e24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('occupations') as batch_op:
        batch_op.add_column(sa.Column('work_flags', sa.JSON(), nullable=True))

    op.create_table(
        'occupation_abilities',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('source_year', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('evidence_grade', sa.String(length=1), server_default='D', nullable=False),
        sa.Column('n', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('retrieved_on', sa.String(length=32), nullable=True),
        sa.Column('metric_definition', sa.Text(), nullable=True),
        sa.Column('occupation_id', sa.Integer(), sa.ForeignKey('occupations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('required_num', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('required_verbal', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('required_spatial', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('required_mech', sa.Float(), server_default='0.0', nullable=False),
        sa.Column('primary_ability', sa.String(length=32), nullable=True),
        sa.CheckConstraint("evidence_grade IN ('A', 'B', 'C', 'D')", name='ck_occ_ability_grade'),
        sa.UniqueConstraint('occupation_id', name='uq_occupation_abilities_occupation_id'),
    )
    op.create_index(
        'ix_occupation_abilities_occupation_id',
        'occupation_abilities',
        ['occupation_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index('ix_occupation_abilities_occupation_id', table_name='occupation_abilities')
    op.drop_table('occupation_abilities')
    with op.batch_alter_table('occupations') as batch_op:
        batch_op.drop_column('work_flags')
