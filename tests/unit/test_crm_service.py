"""
Testes unitários para CrmService.
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.crm_service import CrmService
from app.core.exceptions import ConflictException, NotFoundException
from app.api.v1.schemas.crm import (
    CrmInboundEventRequest,
    CrmInboundBatchRequest,
    CrmOutboundExportRequest,
    CrmEventType,
)
from app.models.user import User


class TestCrmServiceInboundEvent:
    async def test_create_event_success(self, db: AsyncSession, admin_user: User):
        svc = CrmService(db)
        request = CrmInboundEventRequest(
            cd_cpf_cnpj_cliente="12345678000195",
            event_type=CrmEventType.contato_realizado,
            event_at=datetime.now(timezone.utc),
            crm_record_id="CRM-001",
        )
        result = await svc.process_inbound_event(request)
        assert result.id
        assert result.cd_cpf_cnpj_cliente == "12345678000195"
        assert result.event_type == CrmEventType.contato_realizado

    async def test_duplicate_crm_record_id_raises(self, db: AsyncSession, admin_user: User):
        svc = CrmService(db)
        request = CrmInboundEventRequest(
            cd_cpf_cnpj_cliente="12345678000195",
            event_type=CrmEventType.contato_realizado,
            event_at=datetime.now(timezone.utc),
            crm_record_id="CRM-DUP-001",
        )
        # Primeira criação: ok
        await svc.process_inbound_event(request)

        # Segunda com mesmo crm_record_id: deve falhar
        with pytest.raises(ConflictException) as exc_info:
            await svc.process_inbound_event(request)
        assert "CRM_EVENT_DUPLICATE" in exc_info.value.code

    async def test_event_without_crm_record_id(self, db: AsyncSession, admin_user: User):
        """Eventos sem crm_record_id são sempre aceitos (sem idempotência)."""
        svc = CrmService(db)
        request = CrmInboundEventRequest(
            cd_cpf_cnpj_cliente="98765432000100",
            event_type=CrmEventType.proposta_enviada,
            event_at=datetime.now(timezone.utc),
            crm_record_id=None,
        )
        r1 = await svc.process_inbound_event(request)
        r2 = await svc.process_inbound_event(request)
        assert r1.id != r2.id

    async def test_event_with_payload(self, db: AsyncSession, admin_user: User):
        svc = CrmService(db)
        request = CrmInboundEventRequest(
            cd_cpf_cnpj_cliente="11111111000111",
            event_type=CrmEventType.churn,
            event_at=datetime.now(timezone.utc),
            payload={"motivo": "preco", "valor": 1500.0},
        )
        result = await svc.process_inbound_event(request)
        assert result.id


class TestCrmServiceInboundBatch:
    async def test_batch_all_accepted(self, db: AsyncSession):
        svc = CrmService(db)
        batch = CrmInboundBatchRequest(
            events=[
                CrmInboundEventRequest(
                    cd_cpf_cnpj_cliente=f"1234567800019{i}",
                    event_type=CrmEventType.contato_realizado,
                    event_at=datetime.now(timezone.utc),
                    crm_record_id=f"BATCH-{i}",
                )
                for i in range(3)
            ]
        )
        result = await svc.process_inbound_batch(batch)
        assert result.total == 3
        assert result.accepted == 3
        assert result.rejected == 0
        assert result.errors == []

    async def test_batch_partial_reject(self, db: AsyncSession):
        """Segundo evento com mesmo crm_record_id deve ser rejeitado."""
        svc = CrmService(db)

        # Cria o primeiro evento para gerar duplicata
        first = CrmInboundEventRequest(
            cd_cpf_cnpj_cliente="11111111000111",
            event_type=CrmEventType.contato_realizado,
            event_at=datetime.now(timezone.utc),
            crm_record_id="BATCH-DUP",
        )
        await svc.process_inbound_event(first)

        batch = CrmInboundBatchRequest(
            events=[
                CrmInboundEventRequest(
                    cd_cpf_cnpj_cliente="22222222000122",
                    event_type=CrmEventType.contato_realizado,
                    event_at=datetime.now(timezone.utc),
                    crm_record_id="BATCH-NEW",
                ),
                # Esse vai duplicar
                CrmInboundEventRequest(
                    cd_cpf_cnpj_cliente="11111111000111",
                    event_type=CrmEventType.contato_realizado,
                    event_at=datetime.now(timezone.utc),
                    crm_record_id="BATCH-DUP",
                ),
            ]
        )
        result = await svc.process_inbound_batch(batch)
        assert result.total == 2
        assert result.accepted == 1
        assert result.rejected == 1
        assert len(result.errors) == 1
        assert result.errors[0]["index"] == 1


class TestCrmServiceOutbound:
    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_success(self, mock_task, db: AsyncSession, admin_user: User):
        mock_task.delay = MagicMock()
        svc = CrmService(db)
        request = CrmOutboundExportRequest()
        result = await svc.create_outbound_export(request, requested_by_id=admin_user.id)
        assert result.job_id
        assert result.status.value == "pending"

    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_with_filters(self, mock_task, db: AsyncSession, admin_user: User):
        mock_task.delay = MagicMock()
        svc = CrmService(db)
        request = CrmOutboundExportRequest(uf="SP", segmento="VAREJO")
        result = await svc.create_outbound_export(request, requested_by_id=admin_user.id)
        assert result.job_id

    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_celery_offline(self, mock_task, db: AsyncSession, admin_user: User):
        """Se Celery estiver offline, job fica pending sem lançar exceção."""
        mock_task.delay = MagicMock(side_effect=Exception("Redis offline"))
        svc = CrmService(db)
        request = CrmOutboundExportRequest()
        # Não deve lançar
        result = await svc.create_outbound_export(request, requested_by_id=admin_user.id)
        assert result.job_id

    async def test_get_outbound_status_found(self, db: AsyncSession, admin_user: User):
        # Cria job manualmente
        with patch("app.workers.tasks.export_to_crm") as mock_task:
            mock_task.delay = MagicMock()
            svc = CrmService(db)
            request = CrmOutboundExportRequest()
            created = await svc.create_outbound_export(request, requested_by_id=admin_user.id)

        result = await svc.get_outbound_status(created.job_id)
        assert result.job_id == created.job_id
        assert result.status.value == "pending"

    async def test_get_outbound_status_not_found(self, db: AsyncSession):
        svc = CrmService(db)
        with pytest.raises(NotFoundException):
            await svc.get_outbound_status("nonexistent-job-id")
