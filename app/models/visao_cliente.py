"""
Model ORM para a tabela final_visao_cliente.

Tabela READ-ONLY para a Integration API — quem escreve nela é o ETL (implementation).
Todas as colunas são TEXT, espelhando exatamente o schema do banco na VPS.
"""
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VisaoCliente(Base):
    __tablename__ = "final_visao_cliente"

    # ─── Identificação do cliente ─────────────────────────────────────────────
    cd_cpf_cnpj_cliente: Mapped[str] = mapped_column(Text, primary_key=True)
    nome_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_pessoa: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_base: Mapped[str | None] = mapped_column(Text, nullable=True)
    uf: Mapped[str | None] = mapped_column(Text, nullable=True)
    cidade: Mapped[str | None] = mapped_column(Text, nullable=True)
    bairro: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefone: Mapped[str | None] = mapped_column(Text, nullable=True)
    telefone_master: Mapped[str | None] = mapped_column(Text, nullable=True)
    email: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_fundacao_empresa: Mapped[str | None] = mapped_column(Text, nullable=True)
    ramo_atuacao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Parceiro / Consultor ─────────────────────────────────────────────────
    cd_cpf_cnpj_parceiro: Mapped[str | None] = mapped_column(Text, nullable=True)
    nome_parceiro: Mapped[str | None] = mapped_column(Text, nullable=True)
    cd_cpf_cnpj_consultor: Mapped[str | None] = mapped_column(Text, nullable=True)
    nome_consultor: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Conta ────────────────────────────────────────────────────────────────
    num_conta: Mapped[str | None] = mapped_column(Text, nullable=True)
    limite_conta: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_conta_criada: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_encer_cc: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_cc: Mapped[str | None] = mapped_column(Text, nullable=True)
    conta_ativa_90d: Mapped[str | None] = mapped_column(Text, nullable=True)
    chaves_pix_forte: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_conta_criada_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    vl_cash_in_conta_global_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivel_conta: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Cartão ───────────────────────────────────────────────────────────────
    limite_cartao: Mapped[str | None] = mapped_column(Text, nullable=True)
    limite_alocado_cartao_cdb: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_entrega_cartao: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_ativ_cartao_cred: Mapped[str | None] = mapped_column(Text, nullable=True)
    vl_spending_total_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_pagamento_fatura: Mapped[str | None] = mapped_column(Text, nullable=True)
    nivel_cartao: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── C6Pay (maquininha) ───────────────────────────────────────────────────
    fl_propensao_c6pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpv_c6pay_potencial: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_elegivel_venda_c6pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_proposta_sf_pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_aprovacao_pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_install_maq: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_ativacao_pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    c6pay_ativa_30: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_cancelamento_maq: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_ult_trans_pay: Mapped[str | None] = mapped_column(Text, nullable=True)
    recebimento: Mapped[str | None] = mapped_column(Text, nullable=True)
    banco_domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpv_m2: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpv_m1: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpv_m0: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_tpv_prometido: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelamento_maq: Mapped[str | None] = mapped_column(Text, nullable=True)
    elegivel_c6: Mapped[str | None] = mapped_column(Text, nullable=True)
    safra_maquina: Mapped[str | None] = mapped_column(Text, nullable=True)
    idade_safra_maquina: Mapped[str | None] = mapped_column(Text, nullable=True)
    metrica_ativacao: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrica_progresso: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrica_urgencia: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrica_financeiro: Mapped[float | None] = mapped_column(Float, nullable=True)
    metrica_intencao: Mapped[float | None] = mapped_column(Float, nullable=True)
    score_perfil: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ─── Boleto / Cobrança ────────────────────────────────────────────────────
    fl_propensao_bolcob: Mapped[str | None] = mapped_column(Text, nullable=True)
    tpv_bolcob_potencial: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_bolcob_cadastrado: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_prim_liq_bolcob: Mapped[str | None] = mapped_column(Text, nullable=True)
    dt_ult_emissao_bolcob: Mapped[str | None] = mapped_column(Text, nullable=True)
    qtd_bolcob_emtd_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    vl_bolcob_emtd_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    qtd_bolcob_liq_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    vl_bolcob_liq_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    volume_antecipado: Mapped[str | None] = mapped_column(Text, nullable=True)
    agenda_disponivel: Mapped[str | None] = mapped_column(Text, nullable=True)
    taxa_antecipacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    safra_boleto: Mapped[str | None] = mapped_column(Text, nullable=True)
    idade_safra_boleto: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Cash In ──────────────────────────────────────────────────────────────
    vl_cash_in_mtd: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_puro: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_boleto: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_setup: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_setup_pix_cnpj: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_setup_cdb_cartao: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_setup_pagamentos: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_cash_in_setup_deb_auto: Mapped[str | None] = mapped_column(Text, nullable=True)
    vl_saldo_medio_mensalizado: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Comissão / Qualificação ──────────────────────────────────────────────
    mes_ref_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    fl_qualificado_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_cash_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_saldo_medio: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_spending: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_cash_in_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    criterios_atingidos_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    apuracao_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    multiplicador: Mapped[str | None] = mapped_column(Text, nullable=True)
    ja_pago_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    previsao_comiss: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_max: Mapped[str | None] = mapped_column(Text, nullable=True)
    faixa_alvo: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshiold_cash_in: Mapped[str | None] = mapped_column(Text, nullable=True)  # typo original do banco
    threshold_spending: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshold_saldo_medio: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshold_conta_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    threshold_domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_cash_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_spending: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_saldo_medio: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_conta_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    gap_domicilio: Mapped[str | None] = mapped_column(Text, nullable=True)
    pct_cash_in: Mapped[str | None] = mapped_column(Text, nullable=True)
    pct_spending: Mapped[str | None] = mapped_column(Text, nullable=True)
    pct_saldo_medio: Mapped[str | None] = mapped_column(Text, nullable=True)
    pct_conta_global: Mapped[str | None] = mapped_column(Text, nullable=True)
    maior_progresso_pct: Mapped[str | None] = mapped_column(Text, nullable=True)
    criterio_proximo: Mapped[str | None] = mapped_column(Text, nullable=True)
    ja_recebeu_comissao: Mapped[str | None] = mapped_column(Text, nullable=True)
    comissao_prox_mes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status_qualificacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    dias_desde_abertura: Mapped[str | None] = mapped_column(Text, nullable=True)
    m2_dias_faltantes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ─── Receita Federal (CNPJ) ───────────────────────────────────────────────
    rf_razao_social: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_natureza_juridica: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_capital_social: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_porte_empresa: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_nome_fantasia: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_situacao_cadastral: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_data_inicio_ativ: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_cnae_principal: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_uf: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_municipio: Mapped[str | None] = mapped_column(Text, nullable=True)
    rf_email: Mapped[str | None] = mapped_column(Text, nullable=True)
