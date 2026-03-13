from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireCrmOutbound
from app.api.v1.schemas.crm import (
    CrmOutboundExportRequest, CrmOutboundExportResponse,
    CrmOutboundStatusResponse,
)
from app.api.v1.schemas.audit import AuditAction
from app.db.session import get_db
from app.services.crm_service import CrmService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post(
    "/export",
    response_model=CrmOutboundExportResponse,
    status_code=202,
    summary="Iniciar exportação assíncrona de clientes para o CRM",
)
async def create_export(
    body: CrmOutboundExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireCrmOutbound,
):
    result = await CrmService(db).create_outbound_export(body, requested_by_id=current_user.sub)
    await AuditService(db).log(
        action=AuditAction.crm_outbound,
        user_id=current_user.sub,
        resource="crm_job",
        resource_id=result.job_id,
        payload=body.model_dump(exclude_none=True),
    )
    return result


@router.get(
    "/export/{job_id}",
    response_model=CrmOutboundStatusResponse,
    summary="Status de um job de exportação",
)
async def get_export_status(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireCrmOutbound,
):
    return await CrmService(db).get_outbound_status(job_id)
