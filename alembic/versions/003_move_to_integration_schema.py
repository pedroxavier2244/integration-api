"""move integration tables to integration schema

Revision ID: 003
Revises: 002
Create Date: 2026-03-18
"""

from typing import Sequence, Union
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create schema
    op.execute("CREATE SCHEMA IF NOT EXISTS integration")

    # 2. Grant permissions (tables + sequences) — only if etl_user role exists
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'etl_user') THEN
                GRANT USAGE ON SCHEMA integration TO etl_user;
                GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA integration TO etl_user;
                GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA integration TO etl_user;
                ALTER DEFAULT PRIVILEGES IN SCHEMA integration GRANT ALL ON TABLES TO etl_user;
                ALTER DEFAULT PRIVILEGES IN SCHEMA integration GRANT USAGE, SELECT ON SEQUENCES TO etl_user;
            END IF;
        END $$
    """)

    # 3. Move integration tables
    op.execute("ALTER TABLE public.users                  SET SCHEMA integration")
    op.execute("ALTER TABLE public.refresh_tokens         SET SCHEMA integration")
    op.execute("ALTER TABLE public.password_reset_tokens  SET SCHEMA integration")
    op.execute("ALTER TABLE public.audit_logs             SET SCHEMA integration")
    op.execute("ALTER TABLE public.crm_inbound_events     SET SCHEMA integration")
    op.execute("ALTER TABLE public.crm_outbound_jobs      SET SCHEMA integration")

    # 4. Drop old version table only after confirming integration schema has the record
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM integration.integration_api_alembic_version) THEN
                DROP TABLE IF EXISTS public.integration_api_alembic_version;
            ELSE
                RAISE EXCEPTION 'integration.integration_api_alembic_version is empty — deploy alembic.ini and env.py changes before running this migration';
            END IF;
        END $$
    """)


def downgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS public.integration_api_alembic_version (
            version_num VARCHAR(32) NOT NULL PRIMARY KEY
        )
    """)
    op.execute("INSERT INTO public.integration_api_alembic_version SELECT version_num FROM integration.integration_api_alembic_version")

    op.execute("ALTER TABLE integration.crm_outbound_jobs     SET SCHEMA public")
    op.execute("ALTER TABLE integration.crm_inbound_events    SET SCHEMA public")
    op.execute("ALTER TABLE integration.audit_logs            SET SCHEMA public")
    op.execute("ALTER TABLE integration.password_reset_tokens SET SCHEMA public")
    op.execute("ALTER TABLE integration.refresh_tokens        SET SCHEMA public")
    op.execute("ALTER TABLE integration.users                 SET SCHEMA public")

    op.execute("REVOKE USAGE, SELECT ON ALL SEQUENCES IN SCHEMA integration FROM etl_user")
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA integration FROM etl_user")
    op.execute("REVOKE USAGE ON SCHEMA integration FROM etl_user")
    op.execute("DROP SCHEMA IF EXISTS integration")
