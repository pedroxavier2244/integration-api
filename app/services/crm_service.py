from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.repositories.crm_repository import CrmRepository
from app.api.v1.schemas.crm import (
    CrmInboundEventRequest, CrmInboundEventResponse,
    CrmInboundBatchRequest, CrmInboundBatchResponse,
    CrmOutboundExportRequest, CrmOutboundExportResponse,
    CrmOutboundStatusResponse, CrmSyncStatus,
)


class CrmService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def process_inbound_event(
        self, event: CrmInboundEventRequest
    ) -> CrmInboundEventResponse:
        repo = CrmRepository(self.db)

        if event.crm_record_id:
            exists = await repo.event_exists_by_crm_id(event.crm_record_id)
            if exists:
                raise ConflictException(
                    code="CRM_EVENT_DUPLICATE",
                    message=f"Evento com crm_record_id '{event.crm_record_id}' já registrado.",
                )

        db_event = await repo.create_inbound_event(
            cd_cpf_cnpj_cliente=event.cd_cpf_cnpj_cliente,
            event_type=event.event_type.value,
            event_at=event.event_at,
            payload=event.payload,
            crm_record_id=event.crm_record_id,
        )

        return CrmInboundEventResponse.model_validate(db_event)

    async def process_inbound_batch(
        self, batch: CrmInboundBatchRequest
    ) -> CrmInboundBatchResponse:
        accepted = 0
        rejected = 0
        errors = []

        for i, event in enumerate(batch.events):
            try:
                await self.process_inbound_event(event)
                accepted += 1
            except Exception as exc:
                rejected += 1
                errors.append({
                    "index": i,
                    "crm_record_id": event.crm_record_id,
                    "error": str(exc),
                })

        return CrmInboundBatchResponse(
            total=len(batch.events),
            accepted=accepted,
            rejected=rejected,
            errors=errors,
        )

    async def create_outbound_export(
        self, request: CrmOutboundExportRequest, requested_by_id: str
    ) -> CrmOutboundExportResponse:
        repo = CrmRepository(self.db)
        filters = request.model_dump(exclude_none=True)
        job = await repo.create_outbound_job(filters=filters or None)

        # Enfileira task Celery (importação lazy — não quebra se Redis estiver offline)
        try:
            from app.workers.tasks import export_to_crm
            export_to_crm.delay(job.id)
        except Exception:
            pass  # job fica pending e pode ser reprocessado manualmente

        return CrmOutboundExportResponse(
            job_id=job.id,
            status=CrmSyncStatus.pending,
            total_records=0,
            queued_at=job.queued_at,
        )

    async def get_outbound_status(self, job_id: str) -> CrmOutboundStatusResponse:
        repo = CrmRepository(self.db)
        job = await repo.get_outbound_job(job_id)

        if not job:
            raise NotFoundException(message=f"Job '{job_id}' não encontrado.")

        return CrmOutboundStatusResponse(
            job_id=job.id,
            status=CrmSyncStatus(job.status),
            total_records=job.total_records,
            sent=job.sent,
            failed=job.failed,
            started_at=job.started_at,
            finished_at=job.finished_at,
            errors=job.errors or [],
        )
