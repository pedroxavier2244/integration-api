"""
Model ORM somente leitura para a tabela visao_cliente_change_history.

Quem grava esta trilha de alteracoes e o ETL. A Integration API
apenas consulta os eventos persistidos para o front.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VisaoClienteChangeHistory(Base):
    __tablename__ = "visao_cliente_change_history"
    __table_args__ = {"schema": "etl"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    documento: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    etl_job_id: Mapped[str] = mapped_column(Text, nullable=False)
    file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_base: Mapped[str | None] = mapped_column(Text, nullable=True)
    change_type: Mapped[str] = mapped_column(Text, nullable=False)
    field_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
