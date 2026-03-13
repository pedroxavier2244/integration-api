"""
Testes de integração para os endpoints de clientes e empresas.

GET /api/v1/clientes/indicadores
GET /api/v1/clientes/
GET /api/v1/clientes/{cd_cpf_cnpj}
GET /api/v1/empresas/
GET /api/v1/empresas/{cd_cpf_cnpj}
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visao_cliente import VisaoCliente


BASE_CLIENTES = "/api/v1/clientes"
BASE_EMPRESAS = "/api/v1/empresas"


class TestIndicadoresEndpoint:
    async def test_indicadores_success(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/indicadores",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Verifica campos dos 4 KPIs
        assert "contas_abertas" in data
        assert "qualificacao_c6pay" in data
        assert "instalacao_c6pay" in data
        assert "contas_qualificadas" in data
        assert "as_of" in data

    async def test_indicadores_with_as_of_date(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/indicadores?as_of=2025-12-01",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_indicadores_forbidden_for_operador(self, client: AsyncClient, operador_token: str):
        """Operador tem clientes:read, então pode ver indicadores."""
        resp = await client.get(
            f"{BASE_CLIENTES}/indicadores",
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 200

    async def test_indicadores_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_CLIENTES}/indicadores")
        assert resp.status_code == 403

    async def test_indicadores_values_with_data(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        """Com o sample_cliente inserido, pelo menos contas_qualificadas deve ser > 0."""
        resp = await client.get(
            f"{BASE_CLIENTES}/indicadores",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["contas_qualificadas"] >= 1


class TestClientesListEndpoint:
    async def test_list_clientes_empty(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_clientes_with_data(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_CLIENTES}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_search_clientes_by_cnpj(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_CLIENTES}/?q=12345678000195",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "12345678000195"

    async def test_search_clientes_by_name(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_CLIENTES}/?q=EMPRESA TESTE",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_search_clientes_no_results(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/?q=XYZABC_NAO_EXISTE_123",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_list_clientes_pagination(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/?page=1&page_size=10",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 10

    async def test_list_clientes_gestor_allowed(self, client: AsyncClient, gestor_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200

    async def test_list_clientes_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_CLIENTES}/")
        assert resp.status_code == 403


class TestClienteDetailEndpoint:
    async def test_get_cliente_success(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_CLIENTES}/12345678000195",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cd_cpf_cnpj_cliente"] == "12345678000195"
        assert data["nome_cliente"] == "EMPRESA TESTE LTDA"
        # Verifica o campo computado
        assert "nunca_qualificou" in data

    async def test_get_cliente_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/99999999000199",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_get_cliente_without_auth(self, client: AsyncClient, sample_cliente: VisaoCliente):
        resp = await client.get(f"{BASE_CLIENTES}/12345678000195")
        assert resp.status_code == 403


class TestEmpresasEndpoint:
    async def test_list_empresas_success(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_EMPRESAS}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_empresas_with_data(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_EMPRESAS}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_get_empresa_success(self, client: AsyncClient, admin_token: str, sample_cliente: VisaoCliente):
        resp = await client.get(
            f"{BASE_EMPRESAS}/12345678000195",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cd_cpf_cnpj_cliente"] == "12345678000195"

    async def test_get_empresa_not_found(self, client: AsyncClient, admin_token: str):
        resp = await client.get(
            f"{BASE_EMPRESAS}/99999999000199",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 404

    async def test_empresas_forbidden_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_EMPRESAS}/")
        assert resp.status_code == 403

    async def test_empresas_operador_allowed(self, client: AsyncClient, operador_token: str):
        resp = await client.get(
            f"{BASE_EMPRESAS}/",
            headers={"Authorization": f"Bearer {operador_token}"},
        )
        assert resp.status_code == 200
