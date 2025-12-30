"""add receivable_amount to fact_booking

Revision ID: 20251224_add_receivable_amount
Revises: 20251224_add_pay
Create Date: 2025-12-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251224_add_receivable_amount'
down_revision = '20251224_add_pay'
branch_labels = None
depends_on = None


def upgrade():
    # 为 fact_booking 表增加应收金额字段
    op.add_column('fact_booking', sa.Column('receivable_amount', sa.DECIMAL(precision=12, scale=2), nullable=True, server_default='0', comment='应收金额'))


def downgrade():
    # 移除 fact_booking 表字段
    op.drop_column('fact_booking', 'receivable_amount')

