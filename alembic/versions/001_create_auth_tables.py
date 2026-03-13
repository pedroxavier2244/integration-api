"""create auth tables

Revision ID: 001
Revises:
Create Date: 2026-03-10

Cria as tabelas da Integration API:
  - users
  - refresh_tokens
  - password_reset_tokens
  - audit_logs
  - crm_inbound_events
  - crm_outbound_jobs

NÃO cria final_visao_cliente — essa tabela pertence ao ETL (implementation).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column(
            "role",
            sa.Enum("admin", "gestor", "operador", name="userrole"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── refresh_tokens ────────────────────────────────────────────────────────
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("is_revoked", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    # ── password_reset_tokens ─────────────────────────────────────────────────
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("used", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_prt_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_prt_token_hash", "password_reset_tokens", ["token_hash"], unique=True)

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("user_email", sa.String(255), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource", sa.String(64), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    # ── crm_inbound_events ────────────────────────────────────────────────────
    op.create_table(
        "crm_inbound_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("cd_cpf_cnpj_cliente", sa.String(20), nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("crm_record_id", sa.String(255), nullable=True),
        sa.Column("payload", sa.JSON, nullable=True),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_crm_inbound_cnpj", "crm_inbound_events", ["cd_cpf_cnpj_cliente"]
    )
    op.create_index(
        "ix_crm_inbound_crm_id", "crm_inbound_events", ["crm_record_id"], unique=True
    )

    # ── crm_outbound_jobs ─────────────────────────────────────────────────────
    op.create_table(
        "crm_outbound_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("filters", sa.JSON, nullable=True),
        sa.Column("total_records", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("errors", sa.JSON, nullable=True),
        sa.Column(
            "queued_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("crm_outbound_jobs")
    op.drop_table("crm_inbound_events")
    op.drop_table("audit_logs")
    op.drop_table("password_reset_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS userrole")
