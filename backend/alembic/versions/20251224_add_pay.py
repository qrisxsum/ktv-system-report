"""add scan and deposit columns

Revision ID: 20251224_add_pay
Revises: 20251224_add_member_change
Create Date: 2025-12-24 11:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20251224_add_pay'
down_revision = '20251224_add_member_change'
branch_labels = None
depends_on = None


def upgrade():
    # 为 fact_booking 表增加字段
    op.add_column('fact_booking', sa.Column('pay_scan', sa.DECIMAL(precision=12, scale=2), nullable=True, server_default='0', comment='扫码支付'))
    op.add_column('fact_booking', sa.Column('pay_deposit', sa.DECIMAL(precision=12, scale=2), nullable=True, server_default='0', comment='定金消费'))
    
    # 为 fact_room 表增加字段
    op.add_column('fact_room', sa.Column('pay_scan', sa.DECIMAL(precision=12, scale=2), nullable=True, server_default='0', comment='扫码支付'))
    op.add_column('fact_room', sa.Column('pay_deposit', sa.DECIMAL(precision=12, scale=2), nullable=True, server_default='0', comment='定金消费'))


def downgrade():
    # 移除 fact_room 表字段
    op.drop_column('fact_room', 'pay_deposit')
    op.drop_column('fact_room', 'pay_scan')
    
    # 移除 fact_booking 表字段
    op.drop_column('fact_booking', 'pay_deposit')
    op.drop_column('fact_booking', 'pay_scan')

