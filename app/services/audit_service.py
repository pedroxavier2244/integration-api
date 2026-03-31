"""
Service de auditoria.

REGRA CRITICA: o metodo log() NUNCA deve lancar excecao.
Audit log e informativo e nao deve interromper o fluxo da aplicacao.
"""
from typing import Optional

import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.v1.schemas.audit import AuditListParams, AuditLogResponse, AuditAction
from app.api.v1.schemas.common import PaginatedResponse

logger = structlog.get_logger()


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def _build_audit_kwargs(
        self,
        action: AuditAction,
        user_id: Optional[str],
        user_email: Optional[str],
        resource: Optional[str],
        resource_id: Optional[str],
        ip_address: Optional[str],
        user_agent: Optional[str],
        payload: Optional[dict],
    ) -> dict:
        return {
            "action": action.value,
            "user_id": user_id,
            "user_email": user_email,
            "resource": resource,
            "resource_id": resource_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "payload": payload,
        }

    async def log(
        self,
        action: AuditAction,
        user_id: Optional[str] = None,
        user_email: Optional[str] = None,
        resource: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        payload: Optional[dict] = None,
        independent_transaction: bool = False,
    ) -> None:
        audit_kwargs = self._build_audit_kwargs(
            action=action,
            user_id=user_id,
            user_email=user_email,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            user_agent=user_agent,
            payload=payload,
        )

        try:
            from app.repositories.audit_repository import AuditRepository

            if independent_transaction and self.db.bind is not None:
                bind = self.db.bind
                session_bind = bind.engine if hasattr(bind, "engine") else bind
                session_factory = async_sessionmaker(
                    bind=session_bind,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=False,
                )
                async with session_factory() as session:
                    await AuditRepository(session).create(**audit_kwargs)
                    await session.commit()
                return

            await AuditRepository(self.db).create(**audit_kwargs)
        except Exception as exc:
            logger.error("audit_log_failed", action=action, error=str(exc))
            # Nao re-raise: audit nunca bloqueia o fluxo principal.

    async def list_logs(
        self, params: AuditListParams, actor_id: Optional[str] = None, actor_role: Optional[str] = None,
    ) -> PaginatedResponse[AuditLogResponse]:
        from app.repositories.audit_repository import AuditRepository
        from app.repositories.user_repository import UserRepository

        # Gestor ve apenas logs da propria equipe (ele + seus operadores)
        user_ids = None
        if actor_role == "gestor" and actor_id:
            team_users, _ = await UserRepository(self.db).list_users(
                page=1, page_size=500, gestor_id=actor_id
            )
            team_ids = [u.id for u in team_users]
            team_ids.append(actor_id)
            # se o filtro user_id foi passado, respeita apenas se estiver na equipe
            if params.user_id:
                user_ids = [params.user_id] if params.user_id in team_ids else []
            else:
                user_ids = team_ids

        logs, total = await AuditRepository(self.db).list_logs(
            page=params.page,
            page_size=params.page_size,
            user_id=params.user_id if user_ids is None else None,
            user_ids=user_ids,
            action=params.action,
            resource=params.resource,
            date_from=params.date_from,
            date_to=params.date_to,
        )
        return PaginatedResponse(
            items=[AuditLogResponse.model_validate(l) for l in logs],
            total=total,
            page=params.page,
            page_size=params.page_size,
        )
