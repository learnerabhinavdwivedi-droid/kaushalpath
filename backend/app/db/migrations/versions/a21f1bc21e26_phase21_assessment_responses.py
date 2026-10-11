"""Phase 21: assessment_responses table for IRT calibration telemetry.

Revision ID: a21f1bc21e26
Revises: f16a1bc20e25
Create Date: 2026-10-11 12:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a21f1bc21e26'
down_revision: Union[str, None] = 'f16a1bc20e25'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'assessment_responses',
        sa.Column('id', sa.Integer(), nullable=False, primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('session_hash', sa.String(length=64), nullable=False),
        sa.Column('item_id', sa.String(length=64), nullable=False),
        sa.Column('response', sa.String(length=255), nullable=False),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('lang', sa.String(length=10), server_default='en', nullable=False),
        sa.Column('device_class', sa.String(length=30), server_default='mobile', nullable=False),
        sa.Column('guardian_consent', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('completed_at', sa.String(length=32), nullable=True),
    )
    op.create_index('ix_assessment_responses_session_hash', 'assessment_responses', ['session_hash'])
    op.create_index('ix_assessment_responses_item_id', 'assessment_responses', ['item_id'])


def downgrade() -> None:
    op.drop_index('ix_assessment_responses_item_id', table_name='assessment_responses')
    op.drop_index('ix_assessment_responses_session_hash', table_name='assessment_responses')
    op.drop_table('assessment_responses')
