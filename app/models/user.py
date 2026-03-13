"""
Model ORM para a tabela de usuários.

PENDENTE — antes de usar em produção:
  1. Rodar no Neon:
       SELECT column_name, data_type, is_nullable, column_default
       FROM information_schema.columns
       WHERE table_name = 'users'
       ORDER BY ordinal_position;
  2. Se a tabela existir: ajustar __tablename__, nomes de colunas e tipos.
  3. Se a tabela não existir: criar migration Alembic com os campos abaixo.
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import String, Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, PyEnum):
    admin    = "admin"
    gestor   = "gestor"
    operador = "operador"


class User(Base):
    __tablename__ = "users"  # PENDENTE: confirmar nome real da tabela no Neon

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(
        String(255), nullable=True  # null até o usuário definir senha via invite
    )
    # PENDENTE: confirmar nome da coluna de role no banco (pode ser 'role', 'perfil', 'nivel', etc.)
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.operador
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
