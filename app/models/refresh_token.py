"""
Tabela de refresh tokens ativos.
NOVA tabela — criar via Alembic migration.

Propósito: permitir revogação individual de sessões e invalidação
de todos os tokens quando o usuário é desativado ou troca de senha.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = {"schema": "integration"}

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("integration.users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # SHA-256 do token raw — nunca armazenar o token em texto claro
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
