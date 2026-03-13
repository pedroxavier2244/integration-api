from typing import Optional
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_event import CrmInboundEvent, CrmOutboundJob


class CrmRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ─── Inbound ──────────────────────────────────────────────────────────────

    async def create_inbound_event(
        self,
        cd_cpf_cnpj_cliente: str,
        event_type: str,
        event_at: datetime,
        payload: Optional[dict] = None,
        crm_record_id: Optional[str] = None,
    ) -> CrmInboundEvent:
        # Idempotência: retorna existente se crm_record_id já foi processado
        if crm_record_id:
            existing = await self.get_inbound_event_by_crm_id(crm_record_id)
            if existing:
                return existing

        event = CrmInboundEvent(
            cd_cpf_cnpj_cliente=cd_cpf_cnpj_cliente,
            event_type=event_type,
            event_at=event_at,
            payload=payload,
            crm_record_id=crm_record_id,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def get_inbound_event(self, event_id: str) -> Optional[CrmInboundEvent]:
        result = await self.db.execute(
            select(CrmInboundEvent).where(CrmInboundEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_inbound_event_by_crm_id(self, crm_record_id: str) -> Optional[CrmInboundEvent]:
        result = await self.db.execute(
            select(CrmInboundEvent).where(CrmInboundEvent.crm_record_id == crm_record_id)
        )
        return result.scalar_one_or_none()

    async def event_exists_by_crm_id(self, crm_record_id: str) -> bool:
        result = await self.db.execute(
            select(CrmInboundEvent.id).where(CrmInboundEvent.crm_record_id == crm_record_id)
        )
        return result.scalar_one_or_none() is not None

    # ─── Outbound ─────────────────────────────────────────────────────────────

    async def create_outbound_job(
        self, filters: Optional[dict] = None
    ) -> CrmOutboundJob:
        job = CrmOutboundJob(filters=filters)
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_outbound_job(self, job_id: str) -> Optional[CrmOutboundJob]:
        result = await self.db.execute(
            select(CrmOutboundJob).where(CrmOutboundJob.id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_outbound_job(
        self, job_id: str, **fields
    ) -> Optional[CrmOutboundJob]:
        await self.db.execute(
            update(CrmOutboundJob).where(CrmOutboundJob.id == job_id).values(**fields)
        )
        return await self.get_outbound_job(job_id)
