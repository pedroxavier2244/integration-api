import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserRole(str, PyEnum):
    admin = "admin"
    gestor = "gestor"
    operador = "operador"


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "integration"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(
        SAEnum(UserRole, name="userrole"), nullable=False, default=UserRole.operador
    )
    gestor_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("integration.users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
