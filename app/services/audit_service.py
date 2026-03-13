"""
Service de auditoria.

REGRA CRÍTICA: o método log() NUNCA deve lançar exceção.
Audit log é informativo — não deve interromper o fluxo da aplicação.
"""
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.api.v1.schemas.audit import AuditListParams, AuditLogResponse, AuditAction
from app.api.v1.schemas.common import PaginatedResponse

logger = structlog.get_logger()


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

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
    ) -> None:
        try:
            from app.repositories.audit_repository import AuditRepository
            await AuditRepository(self.db).create(
                action=action.value,
                user_id=user_id,
                user_email=user_email,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                payload=payload,
            )
        except Exception as exc:
            logger.error("audit_log_failed", action=action, error=str(exc))
            # Não re-raise — audit nunca bloqueia o fluxo principal

    async def list_logs(
        self, params: AuditListParams
    ) -> PaginatedResponse[AuditLogResponse]:
        from app.repositories.audit_repository import AuditRepository
        logs, total = await AuditRepository(self.db).list_logs(
            page=params.page,
            page_size=params.page_size,
            user_id=params.user_id,
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
