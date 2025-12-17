"""Add unique index for file hash

Revision ID: 20251217_add_unique_file_hash
Revises: 628a6c05dd81
Create Date: 2025-12-17 10:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20251217_add_unique_file_hash"
down_revision: Union[str, None] = "628a6c05dd81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("idx_file_hash", table_name="meta_file_batch")
    op.create_index(
        "uq_meta_file_batch_file_hash",
        "meta_file_batch",
        ["file_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_meta_file_batch_file_hash", table_name="meta_file_batch")
    op.create_index("idx_file_hash", "meta_file_batch", ["file_hash"], unique=False)
