"""phase11 outcome backbone (provider_outcomes, progression, schemes, market/centres/occupations extensions)

Revision ID: a11c0de42b10
Revises: 7c3f9a2b14e0
Create Date: 2026-10-06 16:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a11c0de42b10'
down_revision: Union[str, None] = '7c3f9a2b14e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. occupations: add is_vocational
    with op.batch_alter_table('occupations', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_vocational', sa.Boolean(), server_default='1', nullable=False)
        )
        batch_op.create_index(
            batch_op.f('ix_occupations_is_vocational'), ['is_vocational'], unique=False
        )

    # 2. market: add district, earnings_p25, earnings_p75
    with op.batch_alter_table('market', schema=None) as batch_op:
        batch_op.add_column(sa.Column('district', sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column('earnings_p25', sa.Numeric(precision=12, scale=2), nullable=True)
        )
        batch_op.add_column(
            sa.Column('earnings_p75', sa.Numeric(precision=12, scale=2), nullable=True)
        )
        batch_op.create_index(batch_op.f('ix_market_district'), ['district'], unique=False)

    # 3. centres: add provider characteristics & safety facts
    with op.batch_alter_table('centres', schema=None) as batch_op:
        batch_op.add_column(sa.Column('provider_type', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('affiliation', sa.String(length=120), nullable=True))
        batch_op.add_column(
            sa.Column('has_female_trainers', sa.Boolean(), server_default='0', nullable=False)
        )
        batch_op.add_column(
            sa.Column('has_hostel', sa.Boolean(), server_default='0', nullable=False)
        )
        batch_op.add_column(sa.Column('transport_note', sa.String(length=255), nullable=True))
        batch_op.add_column(
            sa.Column('safety_certified', sa.Boolean(), server_default='0', nullable=False)
        )

    # 4. provider_outcomes table
    op.create_table(
        'provider_outcomes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider_id', sa.Integer(), nullable=False),
        sa.Column('course_id', sa.Integer(), nullable=False),
        sa.Column('cohort_year', sa.Integer(), nullable=True),
        sa.Column('enrolled', sa.Integer(), nullable=True),
        sa.Column('certified', sa.Integer(), nullable=True),
        sa.Column('placed', sa.Integer(), nullable=True),
        sa.Column('placement_rate', sa.Float(), nullable=True),
        sa.Column('earnings_p25', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('earnings_median', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('earnings_p75', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('self_employed_pct', sa.Float(), nullable=True),
        sa.Column('apprenticeship_stipend_inr', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('source_year', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default='0', nullable=False),
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
        sa.ForeignKeyConstraint(['course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['provider_id'], ['centres.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('provider_outcomes', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_provider_outcomes_course_id'), ['course_id'], unique=False
        )
        batch_op.create_index(
            batch_op.f('ix_provider_outcomes_provider_id'), ['provider_id'], unique=False
        )

    # 5. progression_paths table
    op.create_table(
        'progression_paths',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('from_course_id', sa.Integer(), nullable=False),
        sa.Column('to_label', sa.String(length=200), nullable=False),
        sa.Column('to_course_id', sa.Integer(), nullable=True),
        sa.Column('kind', sa.String(length=32), nullable=False),
        sa.Column('credit_note', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('source_year', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default='0', nullable=False),
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
        sa.ForeignKeyConstraint(['from_course_id'], ['courses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['to_course_id'], ['courses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('progression_paths', schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f('ix_progression_paths_from_course_id'), ['from_course_id'], unique=False
        )

    # 6. schemes table
    op.create_table(
        'schemes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('benefit_text_en', sa.Text(), nullable=False),
        sa.Column('benefit_text_hi', sa.Text(), nullable=False),
        sa.Column('eligibility_text', sa.Text(), nullable=True),
        sa.Column('url', sa.String(length=255), nullable=True),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('source_year', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default='0', nullable=False),
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
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('schemes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_schemes_name'), ['name'], unique=False)


def downgrade() -> None:
    op.drop_table('schemes')
    op.drop_table('progression_paths')
    op.drop_table('provider_outcomes')

    with op.batch_alter_table('centres', schema=None) as batch_op:
        batch_op.drop_column('safety_certified')
        batch_op.drop_column('transport_note')
        batch_op.drop_column('has_hostel')
        batch_op.drop_column('has_female_trainers')
        batch_op.drop_column('affiliation')
        batch_op.drop_column('provider_type')

    with op.batch_alter_table('market', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_market_district'))
        batch_op.drop_column('earnings_p75')
        batch_op.drop_column('earnings_p25')
        batch_op.drop_column('district')

    with op.batch_alter_table('occupations', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_occupations_is_vocational'))
        batch_op.drop_column('is_vocational')
