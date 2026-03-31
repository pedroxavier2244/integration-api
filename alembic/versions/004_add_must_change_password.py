"""add must_change_password to users

Revision ID: 004
Revises: 003
Create Date: 2026-03-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        schema="integration",
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password", schema="integration")
