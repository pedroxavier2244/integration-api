"""
Alembic env.py — Integration API

Usa engine async (asyncpg) via run_sync.
A tabela final_visao_cliente é de propriedade do ETL e NÃO é gerenciada por estas migrations.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Carrega settings ANTES de qualquer import de model
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

# Importa todos os models para que a metadata os enxergue
from app.models.base import Base
from app.models.user import User  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.crm_event import CrmInboundEvent, CrmOutboundJob  # noqa: F401
# NÃO importar VisaoCliente — a tabela final_visao_cliente é do ETL

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Substitui a URL do alembic.ini pela do .env
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

# Tabelas gerenciadas pelo ETL — ignorar no autogenerate
EXCLUDE_TABLES = {
    "final_visao_cliente",
    "staging_visao_cliente",
    "etl_file",
    "etl_job_run",
    "etl_job_step",
    "etl_bad_rows",
    "visao_cliente_change_history",
    "cnpj_rf_cache",
    "cnpj_divergencia",
}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table="integration_api_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        version_table="integration_api_alembic_version",
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
