from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireCrmInbound, get_current_user
from app.api.v1.schemas.crm import (
    CrmInboundEventRequest, CrmInboundEventResponse,
    CrmInboundBatchRequest, CrmInboundBatchResponse,
)
from app.api.v1.schemas.audit import AuditAction
from app.db.session import get_db
from app.services.crm_service import CrmService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post(
    "/events",
    response_model=CrmInboundEventResponse,
    status_code=201,
    summary="Registrar evento do CRM (single)",
)
async def inbound_event(
    body: CrmInboundEventRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireCrmInbound,
):
    result = await CrmService(db).process_inbound_event(body)
    await AuditService(db).log(
        action=AuditAction.crm_inbound,
        user_id=current_user.sub,
        resource="cliente",
        resource_id=body.cd_cpf_cnpj_cliente,
        payload={"event_type": body.event_type, "crm_record_id": body.crm_record_id},
    )
    return result


@router.post(
    "/events/batch",
    response_model=CrmInboundBatchResponse,
    status_code=207,
    summary="Registrar lote de eventos do CRM (máx. 500)",
)
async def inbound_event_batch(
    body: CrmInboundBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireCrmInbound,
):
    result = await CrmService(db).process_inbound_batch(body)
    await AuditService(db).log(
        action=AuditAction.crm_inbound,
        user_id=current_user.sub,
        payload={
            "total": result.total,
            "accepted": result.accepted,
            "rejected": result.rejected,
        },
    )
    return result
