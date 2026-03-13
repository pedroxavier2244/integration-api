from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireAuditRead
from app.api.v1.schemas.audit import AuditListParams, AuditLogResponse, AuditAction
from app.api.v1.schemas.common import PaginatedResponse
from app.db.session import get_db
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[AuditLogResponse], summary="Listar logs de auditoria")
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[str] = Query(None),
    action: Optional[AuditAction] = Query(None),
    resource: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user=RequireAuditRead,
):
    params = AuditListParams(
        page=page,
        page_size=page_size,
        user_id=user_id,
        action=action,
        resource=resource,
        date_from=date_from,
        date_to=date_to,
    )
    return await AuditService(db).list_logs(params)
