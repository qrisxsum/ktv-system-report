"""
Add fact_member_change table

Revision ID: 20251224_add_member_change
Revises: 20251220_room_idx
Create Date: 2025-12-24 00:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251224_add_member_change"
down_revision: Union[str, None] = "20251220_room_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fact_member_change",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="自增主键"),
        sa.Column("batch_id", sa.BigInteger(), nullable=False, comment="关联批次"),
        sa.Column("biz_date", sa.Date(), nullable=False, comment="营业日期"),
        sa.Column("store_id", sa.Integer(), nullable=False, comment="关联门店"),
        sa.Column("member_name", sa.String(length=50), nullable=True, comment="会员名称"),
        sa.Column("card_no", sa.String(length=50), nullable=True, comment="会员卡号"),
        sa.Column("member_level", sa.String(length=50), nullable=True, comment="会员等级"),
        sa.Column("phone", sa.String(length=20), nullable=True, comment="联系电话"),
        sa.Column("card_store_name", sa.String(length=100), nullable=True, comment="建卡门店"),
        sa.Column("biz_store_name", sa.String(length=100), nullable=True, comment="业务发生门店"),
        sa.Column("change_type", sa.String(length=20), nullable=True, comment="变动类型 (充值/消费/退费等)"),
        sa.Column("recharge_type", sa.String(length=20), nullable=True, comment="充值类型 (首充/非首充等)"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="状态 (已确认/作废等)"),
        sa.Column("operator", sa.String(length=50), nullable=True, comment="操作人"),
        sa.Column("room_amount_principal", sa.DECIMAL(precision=12, scale=2), nullable=True, comment="房费变动金额_本金"),
        sa.Column("room_amount_gift", sa.DECIMAL(precision=12, scale=2), nullable=True, comment="房费变动金额_赠送"),
        sa.Column("drink_amount_principal", sa.DECIMAL(precision=12, scale=2), nullable=True, comment="酒水变动金额_本金"),
        sa.Column("drink_amount_gift", sa.DECIMAL(precision=12, scale=2), nullable=True, comment="酒水变动金额_赠送"),
        sa.Column("balance_total", sa.DECIMAL(precision=14, scale=2), nullable=True, comment="余额_合计"),
        sa.Column("balance_principal", sa.DECIMAL(precision=14, scale=2), nullable=True, comment="余额_本金"),
        sa.Column("balance_gift", sa.DECIMAL(precision=14, scale=2), nullable=True, comment="余额_赠送"),
        sa.Column(
            "recharge_real_income",
            sa.DECIMAL(precision=12, scale=2),
            nullable=True,
            comment="充值实收(房费本金+酒水本金，仅在变动类型=充值时有值)",
        ),
        sa.Column("growth_delta", sa.Integer(), nullable=True, comment="成长值_变动"),
        sa.Column("growth_balance", sa.Integer(), nullable=True, comment="成长值_余额"),
        sa.Column("points_delta", sa.Integer(), nullable=True, comment="变动积分"),
        sa.Column("points_balance", sa.Integer(), nullable=True, comment="积分余额"),
        sa.Column("pay_info", sa.String(length=255), nullable=True, comment="支付信息原文"),
        sa.Column("salesperson_recharge", sa.String(length=50), nullable=True, comment="充值销售人"),
        sa.Column("free_by", sa.String(length=50), nullable=True, comment="免单人"),
        sa.Column("free_amount", sa.DECIMAL(precision=12, scale=2), nullable=True, comment="免单金额"),
        sa.Column("remark", sa.String(length=255), nullable=True, comment="备注"),
        sa.Column("change_time", sa.DateTime(), nullable=True, comment="变动时间"),
        sa.Column("extra_info", sa.JSON(), nullable=True, comment="其他扩展信息(JSON)"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True, comment="入库时间"),
        sa.PrimaryKeyConstraint("id"),
        comment="连锁会员变动明细事实表",
    )
    op.create_index("idx_batch", "fact_member_change", ["batch_id"], unique=False)
    op.create_index("idx_date_store", "fact_member_change", ["biz_date", "store_id"], unique=False)
    op.create_index("idx_card_no", "fact_member_change", ["card_no"], unique=False)
    op.create_index("idx_change_type", "fact_member_change", ["change_type"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_change_type", table_name="fact_member_change")
    op.drop_index("idx_card_no", table_name="fact_member_change")
    op.drop_index("idx_date_store", table_name="fact_member_change")
    op.drop_index("idx_batch", table_name="fact_member_change")
    op.drop_table("fact_member_change")

