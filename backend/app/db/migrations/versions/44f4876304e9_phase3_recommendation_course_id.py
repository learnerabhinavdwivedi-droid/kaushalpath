"""phase3_recommendation_course_id

Revision ID: 44f4876304e9
Revises: 4896b7a906d0
Create Date: 2026-10-03 12:41:16.267327
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '44f4876304e9'
down_revision: Union[str, None] = '4896b7a906d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.add_column(sa.Column('course_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_recommendations_course_id'), ['course_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_recommendations_course_id', 'courses', ['course_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('recommendations', schema=None) as batch_op:
        batch_op.drop_constraint('fk_recommendations_course_id', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_recommendations_course_id'))
        batch_op.drop_column('course_id')
