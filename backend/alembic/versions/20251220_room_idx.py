"""modify_fact_room_unique_index

Revision ID: 20251220_modify_fact_room_unique_index
Revises: 20251217_add_users_table
Create Date: 2025-12-20 11:00:00.000000
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "20251220_room_idx"
down_revision: Union[str, None] = "20251217_add_users_table"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 删除旧的单一订单号唯一索引
    # 注意：某些数据库可能需要显式指定索引名称
    op.drop_index("idx_order_no", table_name="fact_room")

    # 2. 创建基于门店+订单号的联合唯一索引
    # 这样允许不同门店拥有相同的订单号，但同一个门店内部依然保持唯一
    op.create_index("idx_order_no", "fact_room", ["store_id", "order_no"], unique=True)


def downgrade() -> None:
    # 1. 删除联合索引
    op.drop_index("idx_order_no", table_name="fact_room")

    # 2. 恢复旧的单一订单号唯一索引
    op.create_index("idx_order_no", "fact_room", ["order_no"], unique=True)
