"""
Testes de integração para filtros de carteira no endpoint GET /empresas.

GET /api/v1/empresas/                          (sem filtros)
GET /api/v1/empresas/?uf=SP                    (filtro UF)
GET /api/v1/empresas/?status_cc=LIBERADA       (filtro status)
GET /api/v1/empresas/?ramo_atuacao=varejo      (filtro ramo)
GET /api/v1/empresas/?consultor=joao           (filtro consultor parcial)
GET /api/v1/empresas/?uf=SP&status_cc=LIBERADA (filtros combinados AND)
GET /api/v1/empresas/?page_size=500            (page_size aumentado)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visao_cliente import VisaoCliente

BASE_EMPRESAS = "/api/v1/empresas"


@pytest_asyncio.fixture
async def empresas_carteira(db: AsyncSession):
    """Cria 3 empresas com UF, status_cc e consultores distintos."""
    e1 = VisaoCliente(
        cd_cpf_cnpj_cliente="11111111000111",
        nome_cliente="EMPRESA SP LIBERADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="LIBERADA",
        ramo_atuacao="VAREJO",
        nome_consultor="Joao Silva",
        cd_cpf_cnpj_consultor="99999999000199",
    )
    e2 = VisaoCliente(
        cd_cpf_cnpj_cliente="22222222000122",
        nome_cliente="EMPRESA RJ BLOQUEADA",
        tipo_pessoa="PJ",
        uf="RJ",
        status_cc="BLOQUEADA",
        ramo_atuacao="SERVICOS",
        nome_consultor="Maria Souza",
        cd_cpf_cnpj_consultor="88888888000188",
    )
    e3 = VisaoCliente(
        cd_cpf_cnpj_cliente="33333333000133",
        nome_cliente="EMPRESA SP BLOQUEADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="BLOQUEADA",
        ramo_atuacao="INDUSTRIA",
        nome_consultor="Carlos Joao",
        cd_cpf_cnpj_consultor="77777777000177",
    )
    db.add_all([e1, e2, e3])
    await db.flush()
    return [e1, e2, e3]


class TestEmpresasFiltros:
    async def test_empresas_sem_filtro(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Sem filtros retorna todas as empresas inseridas."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    async def test_empresas_filtro_uf(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Filtro por UF retorna apenas empresas daquele estado."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?uf=SP",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert all(item["uf"] == "SP" for item in data["items"])

    async def test_empresas_filtro_status_cc(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Filtro por status_cc retorna apenas empresas com aquele status."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?status_cc=LIBERADA",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["status_cc"] == "LIBERADA"

    async def test_empresas_filtro_ramo_atuacao(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Filtro por ramo_atuacao faz busca parcial case-insensitive."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?ramo_atuacao=varejo",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["ramo_atuacao"] == "VAREJO"

    async def test_empresas_filtro_consultor(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Filtro por consultor faz busca parcial case-insensitive no nome."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?consultor=joao",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # "Joao Silva" e "Carlos Joao" ambos contêm "joao"
        assert data["total"] == 2

    async def test_empresas_filtros_combinados(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """Combinação de uf + status_cc aplica AND — retorna intersecção."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?uf=SP&status_cc=LIBERADA",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["uf"] == "SP"
        assert data["items"][0]["status_cc"] == "LIBERADA"

    async def test_empresas_page_size_500(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """page_size=500 é aceito e retorna 200 OK."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?page_size=500",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200

    async def test_empresa_response_tem_consultor(
        self, client: AsyncClient, admin_token: str, empresas_carteira
    ):
        """EmpresaResponse inclui nome_consultor e cd_cpf_cnpj_consultor."""
        resp = await client.get(
            f"{BASE_EMPRESAS}/?uf=SP&status_cc=LIBERADA",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert "nome_consultor" in item
        assert "cd_cpf_cnpj_consultor" in item
        assert item["nome_consultor"] == "Joao Silva"
        assert item["cd_cpf_cnpj_consultor"] == "99999999000199"
