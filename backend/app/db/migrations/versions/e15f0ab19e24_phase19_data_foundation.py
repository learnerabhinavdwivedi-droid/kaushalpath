"""Phase 19 Data Foundation: evidence grades, trades, crosswalk, geo.

Revision ID: e15f0ab19e24
Revises: cdbe195361f9
Create Date: 2026-10-11 00:40:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e15f0ab19e24'
down_revision: Union[str, None] = 'cdbe195361f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter existing reference tables to add evidence policy fields
    target_tables = ['occupations', 'courses', 'centres', 'market', 'provider_outcomes']
    for table_name in target_tables:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.add_column(sa.Column('evidence_grade', sa.String(length=1), server_default='D', nullable=False))
            batch_op.add_column(sa.Column('n', sa.Integer(), nullable=True))
            batch_op.add_column(sa.Column('source_url', sa.String(length=500), nullable=True))
            batch_op.add_column(sa.Column('retrieved_on', sa.String(length=32), nullable=True))
            batch_op.add_column(sa.Column('metric_definition', sa.Text(), nullable=True))

    # 2. Create trades table
    op.create_table(
        'trades',
        sa.Column('trade_id', sa.String(length=64), primary_key=True, nullable=False),
        sa.Column('name_en', sa.String(length=200), nullable=False),
        sa.Column('name_hi', sa.String(length=200), nullable=True),
        sa.Column('nco_code', sa.String(length=32), nullable=True),
        sa.Column('nsqf_level', sa.Integer(), nullable=True),
        sa.Column('qp_code', sa.String(length=64), nullable=True),
        sa.Column('ncvt_trade_code', sa.String(length=64), nullable=True),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('source_year', sa.Integer(), nullable=True),
        sa.Column('is_demo', sa.Boolean(), server_default=sa.text('1'), nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('evidence_grade', sa.String(length=1), server_default='D', nullable=False),
        sa.Column('n', sa.Integer(), nullable=True),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('retrieved_on', sa.String(length=32), nullable=True),
        sa.Column('metric_definition', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('trade_id'),
    )
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_trades_name_en'), ['name_en'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_nco_code'), ['nco_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_qp_code'), ['qp_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_trades_ncvt_trade_code'), ['ncvt_trade_code'], unique=False)

    # 3. Create trade_aliases table
    op.create_table(
        'trade_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('trade_id', sa.String(length=64), nullable=False),
        sa.Column('alias', sa.String(length=200), nullable=False),
        sa.Column('source', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(['trade_id'], ['trades.trade_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('trade_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_trade_aliases_trade_id'), ['trade_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_trade_aliases_alias'), ['alias'], unique=False)

    # 4. Create crosswalk table
    op.create_table(
        'crosswalk',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('from_system', sa.String(length=32), nullable=False),
        sa.Column('from_code', sa.String(length=64), nullable=False),
        sa.Column('to_system', sa.String(length=32), nullable=False),
        sa.Column('to_code', sa.String(length=64), nullable=False),
        sa.Column('relation', sa.String(length=16), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=32), nullable=False),
        sa.Column('needs_review', sa.Boolean(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('crosswalk', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_crosswalk_from_system'), ['from_system'], unique=False)
        batch_op.create_index(batch_op.f('ix_crosswalk_from_code'), ['from_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_crosswalk_to_system'), ['to_system'], unique=False)
        batch_op.create_index(batch_op.f('ix_crosswalk_to_code'), ['to_code'], unique=False)

    # 5. Create geo table
    op.create_table(
        'geo',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('lgd_state_code', sa.Integer(), nullable=False),
        sa.Column('lgd_district_code', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=120), nullable=False),
        sa.Column('district', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('lgd_state_code', 'lgd_district_code', name='uq_geo_state_district'),
    )
    with op.batch_alter_table('geo', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_geo_lgd_state_code'), ['lgd_state_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_geo_lgd_district_code'), ['lgd_district_code'], unique=False)
        batch_op.create_index(batch_op.f('ix_geo_state'), ['state'], unique=False)
        batch_op.create_index(batch_op.f('ix_geo_district'), ['district'], unique=False)

    # 6. Create geo_aliases table
    op.create_table(
        'geo_aliases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('alias', sa.String(length=120), nullable=False),
        sa.Column('code', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=16), server_default='district', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('geo_aliases', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_geo_aliases_alias'), ['alias'], unique=False)
        batch_op.create_index(batch_op.f('ix_geo_aliases_code'), ['code'], unique=False)


def downgrade() -> None:
    # 1. Drop geo_aliases
    with op.batch_alter_table('geo_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_geo_aliases_code'))
        batch_op.drop_index(batch_op.f('ix_geo_aliases_alias'))
    op.drop_table('geo_aliases')

    # 2. Drop geo
    with op.batch_alter_table('geo', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_geo_district'))
        batch_op.drop_index(batch_op.f('ix_geo_state'))
        batch_op.drop_index(batch_op.f('ix_geo_lgd_district_code'))
        batch_op.drop_index(batch_op.f('ix_geo_lgd_state_code'))
    op.drop_table('geo')

    # 3. Drop crosswalk
    with op.batch_alter_table('crosswalk', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_crosswalk_to_code'))
        batch_op.drop_index(batch_op.f('ix_crosswalk_to_system'))
        batch_op.drop_index(batch_op.f('ix_crosswalk_from_code'))
        batch_op.drop_index(batch_op.f('ix_crosswalk_from_system'))
    op.drop_table('crosswalk')

    # 4. Drop trade_aliases
    with op.batch_alter_table('trade_aliases', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trade_aliases_alias'))
        batch_op.drop_index(batch_op.f('ix_trade_aliases_trade_id'))
    op.drop_table('trade_aliases')

    # 5. Drop trades
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trades_ncvt_trade_code'))
        batch_op.drop_index(batch_op.f('ix_trades_qp_code'))
        batch_op.drop_index(batch_op.f('ix_trades_nco_code'))
        batch_op.drop_index(batch_op.f('ix_trades_name_en'))
    op.drop_table('trades')

    # 6. Drop added columns from existing tables
    target_tables = ['provider_outcomes', 'market', 'centres', 'courses', 'occupations']
    for table_name in target_tables:
        with op.batch_alter_table(table_name, schema=None) as batch_op:
            batch_op.drop_column('metric_definition')
            batch_op.drop_column('retrieved_on')
            batch_op.drop_column('source_url')
            batch_op.drop_column('n')
            batch_op.drop_column('evidence_grade')
