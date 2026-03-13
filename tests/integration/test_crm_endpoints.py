"""
Testes de integração para os endpoints de CRM.

POST /api/v1/crm/inbound/events
POST /api/v1/crm/inbound/events/batch
POST /api/v1/crm/outbound/export
GET  /api/v1/crm/outbound/export/{job_id}
"""
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


BASE_INBOUND = "/api/v1/crm/inbound"
BASE_OUTBOUND = "/api/v1/crm/outbound"

# Payload mínimo válido para um evento inbound
VALID_EVENT = {
    "cd_cpf_cnpj_cliente": "12345678000195",
    "event_type": "contato_realizado",
    "event_at": "2025-06-01T10:00:00Z",
    "crm_record_id": "CRM-TEST-001",
}


class TestInboundEventEndpoint:
    async def test_create_event_success(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={**VALID_EVENT, "crm_record_id": "CRM-EP-001"},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["cd_cpf_cnpj_cliente"] == "12345678000195"
        assert data["event_type"] == "contato_realizado"
        assert "id" in data
        assert "received_at" in data

    async def test_create_event_admin_allowed(self, client: AsyncClient, admin_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={**VALID_EVENT, "crm_record_id": "CRM-ADMIN-001"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 201

    async def test_create_event_duplicate_crm_record_id(self, client: AsyncClient, operador_token: str):
        payload = {**VALID_EVENT, "crm_record_id": "CRM-DUP-EP"}
        await client.post(
            f"{BASE_INBOUND}/events",
            json=payload,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json=payload,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 409

    async def test_create_event_gestor_forbidden(self, client: AsyncClient, gestor_token: str):
        """Gestor não tem crm:inbound."""
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={**VALID_EVENT, "crm_record_id": "CRM-GESTOR"},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 403

    async def test_create_event_without_auth(self, client: AsyncClient):
        resp = await client.post(f"{BASE_INBOUND}/events", json=VALID_EVENT)
        assert resp.status_code == 403

    async def test_create_event_missing_required_field(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={"event_type": "contato_realizado"},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 422

    async def test_create_event_invalid_event_type(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={**VALID_EVENT, "event_type": "tipo_invalido"},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 422

    async def test_create_event_with_payload(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events",
            json={
                **VALID_EVENT,
                "crm_record_id": "CRM-PAYLOAD-001",
                "payload": {"campo": "valor", "numero": 42},
            },
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 201

    async def test_create_event_without_crm_record_id(self, client: AsyncClient, operador_token: str):
        """Sem crm_record_id, não há idempotência — aceita duplicatas."""
        payload = {
            "cd_cpf_cnpj_cliente": "99999999000199",
            "event_type": "proposta_enviada",
            "event_at": "2025-06-01T10:00:00Z",
        }
        r1 = await client.post(
            f"{BASE_INBOUND}/events",
            json=payload,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        r2 = await client.post(
            f"{BASE_INBOUND}/events",
            json=payload,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r1.json()["id"] != r2.json()["id"]


class TestInboundBatchEndpoint:
    async def test_batch_all_accepted(self, client: AsyncClient, operador_token: str):
        batch = {
            "events": [
                {
                    "cd_cpf_cnpj_cliente": f"1234567800019{i}",
                    "event_type": "contato_realizado",
                    "event_at": "2025-06-01T10:00:00Z",
                    "crm_record_id": f"BATCH-EP-{i}",
                }
                for i in range(3)
            ]
        }
        resp = await client.post(
            f"{BASE_INBOUND}/events/batch",
            json=batch,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 207
        data = resp.json()
        assert data["total"] == 3
        assert data["accepted"] == 3
        assert data["rejected"] == 0

    async def test_batch_partial_reject(self, client: AsyncClient, operador_token: str):
        # Cria primeiro evento para gerar duplicata
        first_payload = {
            "cd_cpf_cnpj_cliente": "11111111000111",
            "event_type": "churn",
            "event_at": "2025-06-01T10:00:00Z",
            "crm_record_id": "BATCH-PREEXIST",
        }
        await client.post(
            f"{BASE_INBOUND}/events",
            json=first_payload,
            headers={"Authorization": f"Bearer {operador_token}"},
        )

        batch = {
            "events": [
                {
                    "cd_cpf_cnpj_cliente": "22222222000122",
                    "event_type": "proposta_enviada",
                    "event_at": "2025-06-01T10:00:00Z",
                    "crm_record_id": "BATCH-NEW-OK",
                },
                # Este vai duplicar
                first_payload,
            ]
        }
        resp = await client.post(
            f"{BASE_INBOUND}/events/batch",
            json=batch,
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 207
        data = resp.json()
        assert data["total"] == 2
        assert data["accepted"] == 1
        assert data["rejected"] == 1

    async def test_batch_empty_events_rejected(self, client: AsyncClient, operador_token: str):
        resp = await client.post(
            f"{BASE_INBOUND}/events/batch",
            json={"events": []},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 422

    async def test_batch_without_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{BASE_INBOUND}/events/batch",
            json={"events": [VALID_EVENT]},
        )
        assert resp.status_code == 403


class TestOutboundExportEndpoint:
    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_success(self, mock_task, client: AsyncClient, admin_token: str):
        mock_task.delay = MagicMock()
        resp = await client.post(
            f"{BASE_OUTBOUND}/export",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "queued_at" in data

    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_with_filters(self, mock_task, client: AsyncClient, admin_token: str):
        mock_task.delay = MagicMock()
        resp = await client.post(
            f"{BASE_OUTBOUND}/export",
            json={"uf": "SP", "segmento": "VAREJO"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["job_id"]

    @patch("app.workers.tasks.export_to_crm")
    async def test_create_export_gestor_allowed(self, mock_task, client: AsyncClient, gestor_token: str):
        """Gestor tem crm:outbound."""
        mock_task.delay = MagicMock()
        resp = await client.post(
            f"{BASE_OUTBOUND}/export",
            json={},
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 202

    async def test_create_export_operador_forbidden(self, client: AsyncClient, operador_token: str):
        """Operador não tem crm:outbound."""
        resp = await client.post(
            f"{BASE_OUTBOUND}/export",
            json={},
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 403

    async def test_create_export_without_auth(self, client: AsyncClient):
        resp = await client.post(f"{BASE_OUTBOUND}/export", json={})
        assert resp.status_code == 403


class TestOutboundStatusEndpoint:
    @patch("app.workers.tasks.export_to_crm")
    async def test_get_status_success(self, mock_task, client: AsyncClient, admin_token: str):
        mock_task.delay = MagicMock()
        # Cria o job
        create_resp = await client.post(
            f"{BASE_OUTBOUND}/export",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        job_id = create_resp.json()["job_id"]

        # Consulta o status
        resp = await client.get(
            f"{BASE_OUTBOUND}/export/{job_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job_id
        assert data["status"] == "pending"
        assert "sent" in data
        assert "failed" in data
        assert "total_records" in data

    async def test_get_status_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_OUTBOUND}/export/nonexistent-job-id",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_get_status_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_OUTBOUND}/export/some-job-id")
        assert resp.status_code == 403

    async def test_get_status_gestor_allowed(self, client: AsyncClient, gestor_token: str, admin_token: str):
        with patch("app.workers.tasks.export_to_crm") as mock_task:
            mock_task.delay = MagicMock()
            create_resp = await client.post(
                f"{BASE_OUTBOUND}/export",
                json={},
                headers={"Authorization": f"Bearer {admin_token}"},
            )
        job_id = create_resp.json()["job_id"]

        resp = await client.get(
            f"{BASE_OUTBOUND}/export/{job_id}",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200
