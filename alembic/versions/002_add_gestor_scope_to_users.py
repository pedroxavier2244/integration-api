"""add gestor scope to users

Revision ID: 002
Revises: 001
Create Date: 2026-03-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "gestor_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_gestor_id", "users", ["gestor_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_gestor_id", table_name="users")
    op.drop_column("users", "gestor_id")
