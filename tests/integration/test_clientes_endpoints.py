"""
Testes de integração para os endpoints de clientes e empresas.

GET /api/v1/clientes/indicadores
GET /api/v1/clientes/
GET /api/v1/clientes/historico-alteracoes
GET /api/v1/clientes/{cd_cpf_cnpj}
GET /api/v1/empresas/
GET /api/v1/empresas/{cd_cpf_cnpj}
"""
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.etl_file import EtlFile
from app.models.visao_cliente import VisaoCliente
from app.models.visao_cliente_change_history import VisaoClienteChangeHistory


BASE_CLIENTES = "/api/v1/clientes"
BASE_EMPRESAS = "/api/v1/empresas"


async def _create_cliente(
    db: AsyncSession,
    *,
    cd_cpf_cnpj_cliente: str,
    nome_cliente: str,
    **extra_fields,
) -> VisaoCliente:
    cliente = VisaoCliente(
        cd_cpf_cnpj_cliente=cd_cpf_cnpj_cliente,
        nome_cliente=nome_cliente,
        **extra_fields,
    )
    db.add(cliente)
    await db.flush()
    return cliente


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

    async def test_filter_clientes_by_safra_maquina(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="11111111000111",
            nome_cliente="CLIENTE SAFRA A",
            safra_maquina="2025-02",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="22222222000122",
            nome_cliente="CLIENTE SAFRA B",
            safra_maquina="2024-11",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/?safra_maquina=2025-02",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "11111111000111"

    async def test_filter_clientes_by_nunca_qualificou(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="33333333000133",
            nome_cliente="CLIENTE NUNCA QUALIFICOU",
            ja_recebeu_comissao="NAO",
            fl_qualificado_comiss="0",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="44444444000144",
            nome_cliente="CLIENTE QUALIFICADO",
            ja_recebeu_comissao="SIM",
            fl_qualificado_comiss="1",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/?nunca_qualificou=true",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "33333333000133"
        assert data["items"][0]["nunca_qualificou"] is True

    async def test_filter_clientes_by_comissao_boletos_e_marco(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="55555555000155",
            nome_cliente="CLIENTE OPERACIONAL",
            comissao_prox_mes="SIM",
            apuracao_comiss="R$ 1200",
            criterios_atingidos_comiss="CASH IN",
            fl_bolcob_cadastrado="SIM",
            criterio_proximo="SPENDING",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="66666666000166",
            nome_cliente="CLIENTE FORA DO FILTRO",
            comissao_prox_mes="NAO",
            apuracao_comiss="R$ 0",
            criterios_atingidos_comiss="PIX",
            fl_bolcob_cadastrado="NAO",
            criterio_proximo="CASH IN",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/?comissao_prox_mes=SIM&apuracao_comiss=1200&criterios_atingidos_comiss=CASH&fl_bolcob_cadastrado=SIM&criterio_proximo=SPEND",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "55555555000155"

    async def test_filter_clientes_by_pix_cancelamento_e_m2(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="77777777000177",
            nome_cliente="CLIENTE MAQUINA",
            chaves_pix_forte="SIM",
            cancelamento_maq="NAO",
            m2_dias_faltantes="12",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="88888888000188",
            nome_cliente="CLIENTE MAQUINA 2",
            chaves_pix_forte="NAO",
            cancelamento_maq="SIM",
            m2_dias_faltantes="45",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/?chaves_pix_forte=SIM&cancelamento_maq=NAO&m2_dias_faltantes=12",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "77777777000177"

    async def test_list_clientes_gestor_allowed(self, client: AsyncClient, gestor_token: str):
        resp = await client.get(
            f"{BASE_CLIENTES}/",
            headers={"Authorization": f"Bearer {gestor_token}"},
        )
        assert resp.status_code == 200

    async def test_list_clientes_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_CLIENTES}/")
        assert resp.status_code == 403


class TestClientesCompleteEndpoint:
    async def test_list_clientes_completo_by_documento_returns_consulta_payload(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="99999999000199",
            nome_cliente="CLIENTE DETALHADO",
            tipo_pessoa="PJ",
            ramo_atuacao="SERVICOS",
            criterios_atingidos_comiss="CASH IN",
            comissao_prox_mes="SIM",
            chaves_pix_forte="SIM",
            rf_nome_fantasia="CLIENTE FANTASIA",
            rf_situacao_cadastral="02",
            rf_cnae_principal="6201500",
            rf_natureza_juridica="2062",
            rf_capital_social="1000,00",
            rf_porte_empresa="01",
            rf_data_inicio_ativ="20240101",
            metrica_ativacao=0.15,
            metrica_progresso=0.35,
            metrica_urgencia=0.20,
            metrica_financeiro=0.05,
            metrica_intencao=0.10,
            score_perfil=0.85,
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/completo?documento=99999999000199",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["documento_consultado"] == "99999999000199"
        assert data["total"] == 1
        assert data["limit"] == 20
        assert data["offset"] == 0
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "99999999000199"
        assert data["items"][0]["ramo_atuacao"] == "SERVICOS"
        assert data["items"][0]["criterios_atingidos_comiss"] == "CASH IN"
        assert data["items"][0]["comissao_prox_mes"] == "SIM"
        assert data["items"][0]["chaves_pix_forte"] == "SIM"
        assert data["items"][0]["nome_fantasia"] == "CLIENTE FANTASIA"
        assert data["items"][0]["situacao_cadastral"] == "02"
        assert data["items"][0]["cnae_fiscal"] == "6201500"
        assert data["items"][0]["natureza_juridica"] == "2062"
        assert data["items"][0]["capital_social"] == "1000,00"
        assert data["items"][0]["porte"] == "01"
        assert data["items"][0]["data_inicio_ativ"] == "20240101"
        assert data["items"][0]["metrica_ativacao"] == 0.15
        assert data["items"][0]["metrica_progresso"] == 0.35
        assert data["items"][0]["metrica_urgencia"] == 0.2
        assert data["items"][0]["metrica_financeiro"] == 0.05
        assert data["items"][0]["metrica_intencao"] == 0.1
        assert data["items"][0]["score_perfil"] == 0.85
        assert data["items"][0]["data_source"] == "final_visao_cliente"

    async def test_list_clientes_completo_by_nome(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="12121212000112",
            nome_cliente="MARIA CONSULTORIA LTDA",
            tipo_pessoa="PJ",
            cidade="Sao Paulo",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="34343434000134",
            nome_cliente="JOSE COMERCIO LTDA",
            tipo_pessoa="PJ",
            cidade="Rio de Janeiro",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/completo?nome=MARIA",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["documento_consultado"] is None
        assert data["total"] == 1
        assert data["limit"] == 20
        assert data["offset"] == 0
        assert data["items"][0]["nome_cliente"] == "MARIA CONSULTORIA LTDA"
        assert data["items"][0]["cidade"] == "Sao Paulo"

    async def test_list_clientes_completo_accepts_business_filters_and_aliases(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="56565656000156",
            nome_cliente="CLIENTE CONSULTA COMPLETA",
            safra_maquina="2025-02",
            ja_recebeu_comissao="NAO",
            fl_qualificado_comiss="0",
            comissao_prox_mes="SIM",
            apuracao_comiss="R$ 1200",
            criterios_atingidos_comiss="CASH IN",
            chaves_pix_forte="SIM",
            cancelamento_maq="NAO",
            m2_dias_faltantes="12",
            fl_bolcob_cadastrado="SIM",
            criterio_proximo="SPENDING",
        )
        await _create_cliente(
            db,
            cd_cpf_cnpj_cliente="57575757000157",
            nome_cliente="CLIENTE FORA DA CONSULTA",
            safra_maquina="2024-01",
            ja_recebeu_comissao="SIM",
            fl_qualificado_comiss="1",
            comissao_prox_mes="NAO",
            apuracao_comiss="R$ 0",
            criterios_atingidos_comiss="PIX",
            chaves_pix_forte="NAO",
            cancelamento_maq="SIM",
            m2_dias_faltantes="45",
            fl_bolcob_cadastrado="NAO",
            criterio_proximo="CASH IN",
        )

        resp = await client.get(
            f"{BASE_CLIENTES}/completo?safra=2025-02&nunca_qualificou=true&comissao_prox_mes=SIM&comissao_este_mes=1200&criterios_atingidos_comissao=CASH&pix_forte=SIM&cancelamento_maquina=NAO&m2_faltantes=12&boletos=SIM&marco=SPEND&limit=1&offset=0",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["documento_consultado"] is None
        assert data["total"] == 1
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert data["items"][0]["cd_cpf_cnpj_cliente"] == "56565656000156"
        assert data["items"][0]["nunca_qualificou"] is True
        assert data["items"][0]["criterio_proximo"] == "SPENDING"

    async def test_list_clientes_completo_without_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_CLIENTES}/completo?nome=MARIA")
        assert resp.status_code == 403


class TestClientesHistoricoAlteracoesEndpoint:
    async def test_get_historico_alteracoes_success(
        self,
        client: AsyncClient,
        db: AsyncSession,
        admin_token: str,
    ):
        db.add(
            EtlFile(
                id="file-1",
                filename="Relatorio de Producao 19.02.26.xlsx",
                file_date=date(2026, 2, 19),
            )
        )
        db.add_all(
            [
                VisaoClienteChangeHistory(
                    id=1,
                    documento="12345678000195",
                    etl_job_id="job-1",
                    file_id="file-1",
                    data_base="2026-02-19",
                    change_type="INSERT",
                    field_name=None,
                    old_value=None,
                    new_value=None,
                    changed_at=datetime(2026, 2, 19, 12, 0, tzinfo=timezone.utc),
                ),
                VisaoClienteChangeHistory(
                    id=2,
                    documento="12345678000195",
                    etl_job_id="job-2",
                    file_id="file-1",
                    data_base="2026-03-04",
                    change_type="UPDATE",
                    field_name="criterio_proximo",
                    old_value="CASH IN",
                    new_value="SPENDING",
                    changed_at=datetime(2026, 3, 4, 14, 30, tzinfo=timezone.utc),
                ),
            ]
        )
        await db.flush()

        resp = await client.get(
            f"{BASE_CLIENTES}/historico-alteracoes?documento=12.345.678/0001-95",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["documento_consultado"] == "12345678000195"
        assert data["total"] == 2
        assert data["limit"] == 100
        assert data["offset"] == 0
        assert len(data["items"]) == 2
        assert data["items"][0]["change_type"] == "INSERT"
        assert data["items"][0]["filename"] == "Relatorio de Producao 19.02.26.xlsx"
        assert data["items"][1]["change_type"] == "UPDATE"
        assert data["items"][1]["field_name"] == "criterio_proximo"
        assert data["items"][1]["old_value"] == "CASH IN"
        assert data["items"][1]["new_value"] == "SPENDING"

    async def test_get_historico_alteracoes_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{BASE_CLIENTES}/historico-alteracoes?documento=12345678000195")
        assert resp.status_code == 403

    async def test_get_historico_alteracoes_rejects_invalid_documento(
        self,
        client: AsyncClient,
        admin_token: str,
    ):
        resp = await client.get(
            f"{BASE_CLIENTES}/historico-alteracoes?documento=abc",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 400


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
