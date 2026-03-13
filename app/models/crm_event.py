"""
Tabelas de eventos CRM.
NOVAS tabelas — criar via Alembic migration.

CrmInboundEvent: eventos recebidos do CRM (operador registra atendimento, etc.)
CrmOutboundJob: jobs de exportação de clientes para o CRM (executados via Celery)
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class CrmInboundEvent(Base):
    __tablename__ = "crm_inbound_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    cd_cpf_cnpj_cliente: Mapped[str] = mapped_column(
        String(20), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Chave de idempotência: rejeitar duplicatas com mesmo crm_record_id
    crm_record_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    payload: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


class CrmOutboundJob(Base):
    __tablename__ = "crm_outbound_jobs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    filters: Mapped[Any | None] = mapped_column(
        JSON, nullable=True  # filtros usados para selecionar registros
    )
    total_records: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
