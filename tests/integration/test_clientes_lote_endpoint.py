"""
Testes de integração para POST /api/v1/clientes/lote.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visao_cliente import VisaoCliente

BASE = "/api/v1/clientes/lote"


@pytest_asyncio.fixture
async def clientes_lote(db: AsyncSession):
    """3 clientes com UF, status_cc e consultores distintos para testes de lote."""
    c1 = VisaoCliente(
        cd_cpf_cnpj_cliente="10000000000100",
        nome_cliente="CLIENTE SP LIBERADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="LIBERADA",
        ramo_atuacao="VAREJO",
        nome_consultor="Joao Silva",
        cd_cpf_cnpj_consultor="99999999000199",
    )
    c2 = VisaoCliente(
        cd_cpf_cnpj_cliente="20000000000200",
        nome_cliente="CLIENTE RJ BLOQUEADA",
        tipo_pessoa="PJ",
        uf="RJ",
        status_cc="BLOQUEADA",
        ramo_atuacao="SERVICOS",
        nome_consultor="Maria Souza",
        cd_cpf_cnpj_consultor="88888888000188",
    )
    c3 = VisaoCliente(
        cd_cpf_cnpj_cliente="30000000000300",
        nome_cliente="CLIENTE SP BLOQUEADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="BLOQUEADA",
        ramo_atuacao="INDUSTRIA",
        nome_consultor="Carlos Joao",
        cd_cpf_cnpj_consultor="77777777000177",
    )
    db.add_all([c1, c2, c3])
    await db.flush()
    return [c1, c2, c3]


class TestClientesLote:
    async def test_lote_todos_encontrados(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Todos os CNPJs existem → not_found vazio."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "20000000000200", "30000000000300"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 3
        assert data["total_not_found"] == 0
        assert data["not_found"] == []

    async def test_lote_parcialmente_encontrado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Alguns CNPJs existem, outros não → ambas as listas preenchidas."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "99999999999999"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1
        assert data["total_not_found"] == 1
        assert "99999999999999" in data["not_found"]

    async def test_lote_nenhum_encontrado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Nenhum CNPJ existe → found vazio, todos em not_found."""
        resp = await client.post(
            BASE,
            json={"documentos": ["99999999999991", "99999999999992"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 0
        assert data["total_not_found"] == 2
        assert data["found"] == []

    async def test_lote_filtro_uf_exclui_outro_estado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """CNPJ existe mas é de outro estado → vai para not_found."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "20000000000200"], "uf": "SP"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1
        assert data["found"][0]["cd_cpf_cnpj_cliente"] == "10000000000100"
        assert "20000000000200" in data["not_found"]

    async def test_lote_filtro_consultor_parcial(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Filtro consultor faz busca parcial — 'joao' bate em 'Joao Silva' e 'Carlos Joao'."""
        resp = await client.post(
            BASE,
            json={
                "documentos": ["10000000000100", "20000000000200", "30000000000300"],
                "consultor": "joao",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 2

    async def test_lote_response_tem_campos_completos(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """found retorna ClienteDetailResponse com campos completos."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        item = resp.json()["found"][0]
        assert "cd_cpf_cnpj_cliente" in item
        assert "nome_cliente" in item
        assert "uf" in item
        assert "status_cc" in item
        assert item["cd_cpf_cnpj_cliente"] == "10000000000100"

    async def test_lote_documentos_vazio_retorna_422(
        self, client: AsyncClient, admin_token: str
    ):
        """Lista vazia de documentos → 422."""
        resp = await client.post(
            BASE,
            json={"documentos": []},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_lote_mais_de_100_documentos_retorna_422(
        self, client: AsyncClient, admin_token: str
    ):
        """Mais de 100 documentos → 422."""
        docs = [f"{i:014d}" for i in range(101)]
        resp = await client.post(
            BASE,
            json={"documentos": docs},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_lote_sem_autenticacao_retorna_403(self, client: AsyncClient):
        """Sem token → 403."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100"]},
        )
        assert resp.status_code in (401, 403)
