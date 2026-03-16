"""
Model ORM somente leitura para a tabela etl_file.

Esta tabela pertence ao ETL e e usada aqui apenas para enriquecer
o historico de alteracoes com metadados do arquivo de origem.
"""
from datetime import date

from sqlalchemy import Date, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class EtlFile(Base):
    __tablename__ = "etl_file"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_date: Mapped[date | None] = mapped_column(Date, nullable=True)
