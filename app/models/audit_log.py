"""
Tabela de logs de auditoria.
NOVA tabela — criar via Alembic migration.

Todos os eventos relevantes (login, criação de usuário, leitura de cliente, etc.)
são registrados aqui para rastreabilidade e compliance.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Nullable: ações de sistema ou de usuário não autenticado (ex: login_failed)
    user_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True  # desnormalizado para consulta rápida sem JOIN
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource: Mapped[str | None] = mapped_column(
        String(64), nullable=True  # ex: "cliente", "user", "crm_job"
    )
    resource_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(
        String(45), nullable=True  # suporta IPv6
    )
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[Any | None] = mapped_column(
        JSON, nullable=True  # dados sanitizados (sem senhas, tokens, etc.)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
