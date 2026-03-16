from pydantic import BaseModel, computed_field
from typing import Optional, List
from datetime import date, datetime


class IndicadoresResponse(BaseModel):
    """KPIs calculados dinamicamente a partir de final_visao_cliente."""
    contas_abertas: int
    instalacao_c6pay: int
    qualificacao_c6pay: int
    contas_qualificadas: int
    as_of: date


class ClienteResumoResponse(BaseModel):
    """
    Campos operacionais para listagem — usados pelo CRM e pelo front-end.
    Inclui: identificação, comissão, C6Pay, boleto, PIX e indicadores.
    """
    # ── Identificação ─────────────────────────────────────────────────────────
    cd_cpf_cnpj_cliente: str
    nome_cliente: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    data_base: Optional[str] = None
    uf: Optional[str] = None

    # ── Conta ─────────────────────────────────────────────────────────────────
    dt_conta_criada: Optional[str] = None
    status_cc: Optional[str] = None
    nivel_conta: Optional[str] = None

    # ── Comissão ──────────────────────────────────────────────────────────────
    fl_qualificado_comiss: Optional[str] = None
    status_qualificacao: Optional[str] = None
    ja_recebeu_comissao: Optional[str] = None
    criterios_atingidos_comiss: Optional[str] = None
    apuracao_comiss: Optional[str] = None          # comissão esse mês
    comissao_prox_mes: Optional[str] = None        # comissão próximo mês
    previsao_comiss: Optional[str] = None
    criterio_proximo: Optional[str] = None         # marco (próximo critério a atingir)
    mes_ref_comiss: Optional[str] = None

    # ── C6Pay / Maquininha ────────────────────────────────────────────────────
    safra_maquina: Optional[str] = None            # safra de instalação
    dt_install_maq: Optional[str] = None
    dt_cancelamento_maq: Optional[str] = None
    cancelamento_maq: Optional[str] = None         # flag de cancelamento
    tpv_m0: Optional[str] = None
    tpv_m1: Optional[str] = None
    tpv_m2: Optional[str] = None
    m2_dias_faltantes: Optional[str] = None        # dias faltantes para atingir m2

    # ── Boleto ────────────────────────────────────────────────────────────────
    fl_bolcob_cadastrado: Optional[str] = None
    vl_bolcob_emtd_mtd: Optional[str] = None
    qtd_bolcob_emtd_mtd: Optional[str] = None
    vl_bolcob_liq_mtd: Optional[str] = None
    qtd_bolcob_liq_mtd: Optional[str] = None

    # ── PIX / Segurança ───────────────────────────────────────────────────────
    chaves_pix_forte: Optional[str] = None

    @computed_field
    @property
    def nunca_qualificou(self) -> bool:
        """True quando o cliente nunca se qualificou para comissão."""
        ja_recebeu_nao = (self.ja_recebeu_comissao or "").upper().replace("Ã", "A") == "NAO"
        qualificado = (self.fl_qualificado_comiss or "") in ("1", "1.0")
        return ja_recebeu_nao and not qualificado

    model_config = {"from_attributes": True}


class ClienteDetailResponse(BaseModel):
    """Todos os campos de final_visao_cliente."""
    cd_cpf_cnpj_cliente: str
    nome_cliente: Optional[str] = None
    tipo_pessoa: Optional[str] = None
    data_base: Optional[str] = None
    uf: Optional[str] = None
    cidade: Optional[str] = None
    bairro: Optional[str] = None
    telefone: Optional[str] = None
    telefone_master: Optional[str] = None
    email: Optional[str] = None
    dt_fundacao_empresa: Optional[str] = None
    ramo_atuacao: Optional[str] = None
    cd_cpf_cnpj_parceiro: Optional[str] = None
    nome_parceiro: Optional[str] = None
    cd_cpf_cnpj_consultor: Optional[str] = None
    nome_consultor: Optional[str] = None
    num_conta: Optional[str] = None
    limite_conta: Optional[str] = None
    dt_conta_criada: Optional[str] = None
    dt_encer_cc: Optional[str] = None
    status_cc: Optional[str] = None
    conta_ativa_90d: Optional[str] = None
    chaves_pix_forte: Optional[str] = None
    dt_conta_criada_global: Optional[str] = None
    vl_cash_in_conta_global_mtd: Optional[str] = None
    nivel_conta: Optional[str] = None
    limite_cartao: Optional[str] = None
    limite_alocado_cartao_cdb: Optional[str] = None
    dt_entrega_cartao: Optional[str] = None
    dt_ativ_cartao_cred: Optional[str] = None
    vl_spending_total_mtd: Optional[str] = None
    status_pagamento_fatura: Optional[str] = None
    nivel_cartao: Optional[str] = None
    fl_propensao_c6pay: Optional[str] = None
    tpv_c6pay_potencial: Optional[str] = None
    fl_elegivel_venda_c6pay: Optional[str] = None
    status_proposta_sf_pay: Optional[str] = None
    dt_aprovacao_pay: Optional[str] = None
    dt_install_maq: Optional[str] = None
    dt_ativacao_pay: Optional[str] = None
    c6pay_ativa_30: Optional[str] = None
    dt_cancelamento_maq: Optional[str] = None
    dt_ult_trans_pay: Optional[str] = None
    recebimento: Optional[str] = None
    banco_domicilio: Optional[str] = None
    tpv_m2: Optional[str] = None
    tpv_m1: Optional[str] = None
    tpv_m0: Optional[str] = None
    faixa_tpv_prometido: Optional[str] = None
    cancelamento_maq: Optional[str] = None
    elegivel_c6: Optional[str] = None
    safra_maquina: Optional[str] = None
    idade_safra_maquina: Optional[str] = None
    metrica_ativacao: Optional[float] = None
    metrica_progresso: Optional[float] = None
    metrica_urgencia: Optional[float] = None
    metrica_financeiro: Optional[float] = None
    metrica_intencao: Optional[float] = None
    score_perfil: Optional[float] = None
    fl_propensao_bolcob: Optional[str] = None
    tpv_bolcob_potencial: Optional[str] = None
    fl_bolcob_cadastrado: Optional[str] = None
    dt_prim_liq_bolcob: Optional[str] = None
    dt_ult_emissao_bolcob: Optional[str] = None
    qtd_bolcob_emtd_mtd: Optional[str] = None
    vl_bolcob_emtd_mtd: Optional[str] = None
    qtd_bolcob_liq_mtd: Optional[str] = None
    vl_bolcob_liq_mtd: Optional[str] = None
    volume_antecipado: Optional[str] = None
    agenda_disponivel: Optional[str] = None
    taxa_antecipacao: Optional[str] = None
    safra_boleto: Optional[str] = None
    idade_safra_boleto: Optional[str] = None
    vl_cash_in_mtd: Optional[str] = None
    fl_cash_in_puro: Optional[str] = None
    fl_cash_in_boleto: Optional[str] = None
    fl_cash_in_setup: Optional[str] = None
    fl_cash_in_setup_pix_cnpj: Optional[str] = None
    fl_cash_in_setup_cdb_cartao: Optional[str] = None
    fl_cash_in_setup_pagamentos: Optional[str] = None
    fl_cash_in_setup_deb_auto: Optional[str] = None
    vl_saldo_medio_mensalizado: Optional[str] = None
    mes_ref_comiss: Optional[str] = None
    fl_qualificado_comiss: Optional[str] = None
    faixa_cash_in: Optional[str] = None
    faixa_domicilio: Optional[str] = None
    faixa_saldo_medio: Optional[str] = None
    faixa_spending: Optional[str] = None
    faixa_cash_in_global: Optional[str] = None
    criterios_atingidos_comiss: Optional[str] = None
    apuracao_comiss: Optional[str] = None
    multiplicador: Optional[str] = None
    ja_pago_comiss: Optional[str] = None
    previsao_comiss: Optional[str] = None
    faixa_max: Optional[str] = None
    faixa_alvo: Optional[str] = None
    threshiold_cash_in: Optional[str] = None
    threshold_spending: Optional[str] = None
    threshold_saldo_medio: Optional[str] = None
    threshold_conta_global: Optional[str] = None
    threshold_domicilio: Optional[str] = None
    gap_cash_in: Optional[str] = None
    gap_spending: Optional[str] = None
    gap_saldo_medio: Optional[str] = None
    gap_conta_global: Optional[str] = None
    gap_domicilio: Optional[str] = None
    pct_cash_in: Optional[str] = None
    pct_spending: Optional[str] = None
    pct_saldo_medio: Optional[str] = None
    pct_conta_global: Optional[str] = None
    maior_progresso_pct: Optional[str] = None
    criterio_proximo: Optional[str] = None
    ja_recebeu_comissao: Optional[str] = None
    comissao_prox_mes: Optional[str] = None
    status_qualificacao: Optional[str] = None
    dias_desde_abertura: Optional[str] = None
    m2_dias_faltantes: Optional[str] = None
    rf_razao_social: Optional[str] = None
    rf_natureza_juridica: Optional[str] = None
    rf_capital_social: Optional[str] = None
    rf_porte_empresa: Optional[str] = None
    rf_nome_fantasia: Optional[str] = None
    rf_situacao_cadastral: Optional[str] = None
    rf_data_inicio_ativ: Optional[str] = None
    rf_cnae_principal: Optional[str] = None
    rf_uf: Optional[str] = None
    rf_municipio: Optional[str] = None
    rf_email: Optional[str] = None

    @computed_field
    @property
    def nunca_qualificou(self) -> bool:
        return (
            self.ja_recebeu_comissao == "NAO"
            and self.fl_qualificado_comiss != "1"
        )

    model_config = {"from_attributes": True}


class ClienteConsultaItemResponse(ClienteDetailResponse):
    """Resposta detalhada no formato consumido pela busca operacional."""

    @computed_field
    @property
    def nome_fantasia(self) -> Optional[str]:
        return self.rf_nome_fantasia

    @computed_field
    @property
    def situacao_cadastral(self) -> Optional[str]:
        return self.rf_situacao_cadastral

    @computed_field
    @property
    def descricao_situacao(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def cnae_fiscal(self) -> Optional[str]:
        return self.rf_cnae_principal

    @computed_field
    @property
    def cnae_descricao(self) -> Optional[str]:
        return None

    @computed_field
    @property
    def natureza_juridica(self) -> Optional[str]:
        return self.rf_natureza_juridica

    @computed_field
    @property
    def capital_social(self) -> Optional[str]:
        return self.rf_capital_social

    @computed_field
    @property
    def porte(self) -> Optional[str]:
        return self.rf_porte_empresa

    @computed_field
    @property
    def data_inicio_ativ(self) -> Optional[str]:
        return self.rf_data_inicio_ativ

    @computed_field
    @property
    def data_source(self) -> str:
        return "final_visao_cliente"


class ClienteListResponse(BaseModel):
    items: List[ClienteResumoResponse]
    total: int
    page: int
    page_size: int


class ClienteConsultaResponse(BaseModel):
    documento_consultado: Optional[str] = None
    total: int
    limit: int
    offset: int
    items: List[ClienteConsultaItemResponse]


class ClienteHistoricoAlteracaoItemResponse(BaseModel):
    id: int
    data_base: Optional[str] = None
    changed_at: Optional[datetime] = None
    etl_job_id: Optional[str] = None
    file_id: Optional[str] = None
    file_date: Optional[date] = None
    filename: Optional[str] = None
    change_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None


class ClienteHistoricoAlteracoesResponse(BaseModel):
    documento_consultado: str
    total: int
    limit: int
    offset: int
    items: List[ClienteHistoricoAlteracaoItemResponse]


class EmpresaResponse(BaseModel):
    """Dados da Receita Federal de um cliente PJ."""
    cd_cpf_cnpj_cliente: str
    nome_cliente: Optional[str] = None
    rf_razao_social: Optional[str] = None
    rf_nome_fantasia: Optional[str] = None
    rf_situacao_cadastral: Optional[str] = None
    rf_cnae_principal: Optional[str] = None
    rf_natureza_juridica: Optional[str] = None
    rf_capital_social: Optional[str] = None
    rf_porte_empresa: Optional[str] = None
    rf_data_inicio_ativ: Optional[str] = None
    rf_uf: Optional[str] = None
    rf_municipio: Optional[str] = None
    rf_email: Optional[str] = None
    model_config = {"from_attributes": True}
