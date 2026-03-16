import re
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireClientesRead, get_current_user
from app.api.v1.schemas.clientes import (
    ClienteResumoResponse, ClienteDetailResponse,
    ClienteConsultaItemResponse, ClienteConsultaResponse,
    ClienteHistoricoAlteracaoItemResponse, ClienteHistoricoAlteracoesResponse,
    ClienteListResponse, IndicadoresResponse,
)
from app.api.v1.schemas.audit import AuditAction
from app.db.session import get_db
from app.repositories.visao_cliente_repository import VisaoClienteRepository
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException

router = APIRouter()


def _only_digits(value: str) -> str:
    return re.sub(r"[^0-9]", "", value or "")


def _resolve_documento_consultado(
    q: Optional[str],
    documento: Optional[str],
    cnpj: Optional[str],
) -> Optional[str]:
    if documento:
        return documento
    if cnpj:
        return cnpj
    if q and q.replace(".", "").replace("/", "").replace("-", "").isdigit():
        return q
    return None


@router.get(
    "/indicadores",
    response_model=IndicadoresResponse,
    summary="KPIs da carteira (contas abertas, C6Pay, qualificação)",
)
async def get_indicadores(
    as_of: date = Query(default_factory=date.today, description="Data de referência para calcular janelas"),
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    from dateutil.relativedelta import relativedelta

    repo = VisaoClienteRepository(db)

    # Contas abertas: janela Q1 do ano corrente (ajustar conforme regra de negócio)
    year = as_of.year
    contas_start = date(year, 1, 1)
    contas_end = date(year, 3, 31)

    # C6Pay: instalações dos últimos 5 meses até as_of
    install_start = (as_of - relativedelta(months=5)).replace(day=1)
    install_end = as_of

    contas_abertas, instalacao_c6pay, qualificacao_c6pay, contas_qualificadas = (
        await repo.count_contas_abertas(contas_start, contas_end),
        await repo.count_instalacao_c6pay(install_start, install_end),
        await repo.count_qualificacao_c6pay(install_start, install_end),
        await repo.count_contas_qualificadas(),
    )

    return IndicadoresResponse(
        contas_abertas=contas_abertas,
        instalacao_c6pay=instalacao_c6pay,
        qualificacao_c6pay=qualificacao_c6pay,
        contas_qualificadas=contas_qualificadas,
        as_of=as_of,
    )


@router.get("/", response_model=ClienteListResponse, summary="Buscar clientes")
async def list_clientes(
    q: Optional[str] = Query(None, description="CPF/CNPJ ou nome (busca parcial)"),
    cnpj: Optional[str] = Query(None, description="Filtro por CPF/CNPJ"),
    nome: Optional[str] = Query(None, description="Filtro por nome do cliente"),
    safra_maquina: Optional[str] = Query(None, description="Filtro por safra da maquininha"),
    nunca_qualificou: Optional[bool] = Query(None, description="Filtra clientes que nunca se qualificaram para comissao"),
    comissao_prox_mes: Optional[str] = Query(None, description="Filtro por status de comissao do proximo mes"),
    apuracao_comiss: Optional[str] = Query(None, description="Filtro pela apuracao de comissao do mes atual"),
    criterios_atingidos_comiss: Optional[str] = Query(None, description="Filtro por criterios atingidos de comissao"),
    chaves_pix_forte: Optional[str] = Query(None, description="Filtro por uso de chave PIX forte"),
    cancelamento_maq: Optional[str] = Query(None, description="Filtro por cancelamento de maquina"),
    m2_dias_faltantes: Optional[str] = Query(None, description="Filtro por dias faltantes para atingir m2"),
    fl_bolcob_cadastrado: Optional[str] = Query(None, description="Filtro por cadastro de boleto/cobranca"),
    criterio_proximo: Optional[str] = Query(None, description="Filtro por marco ou criterio proximo"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    repo = VisaoClienteRepository(db)
    items, total = await repo.search(
        q=q,
        cnpj=cnpj,
        nome=nome,
        safra_maquina=safra_maquina,
        nunca_qualificou=nunca_qualificou,
        comissao_prox_mes=comissao_prox_mes,
        apuracao_comiss=apuracao_comiss,
        criterios_atingidos_comiss=criterios_atingidos_comiss,
        chaves_pix_forte=chaves_pix_forte,
        cancelamento_maq=cancelamento_maq,
        m2_dias_faltantes=m2_dias_faltantes,
        fl_bolcob_cadastrado=fl_bolcob_cadastrado,
        criterio_proximo=criterio_proximo,
        page=page,
        page_size=page_size,
    )

    applied_filters = {
        "q": q,
        "cnpj": cnpj,
        "nome": nome,
        "safra_maquina": safra_maquina,
        "nunca_qualificou": nunca_qualificou,
        "comissao_prox_mes": comissao_prox_mes,
        "apuracao_comiss": apuracao_comiss,
        "criterios_atingidos_comiss": criterios_atingidos_comiss,
        "chaves_pix_forte": chaves_pix_forte,
        "cancelamento_maq": cancelamento_maq,
        "m2_dias_faltantes": m2_dias_faltantes,
        "fl_bolcob_cadastrado": fl_bolcob_cadastrado,
        "criterio_proximo": criterio_proximo,
        "page": page,
        "page_size": page_size,
    }

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        payload={key: value for key, value in applied_filters.items() if value is not None},
    )

    return ClienteListResponse(
        items=[ClienteResumoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/completo",
    response_model=ClienteConsultaResponse,
    summary="Buscar clientes com todos os detalhes e resposta operacional completa",
)
async def list_clientes_completo(
    q: Optional[str] = Query(None, description="CPF/CNPJ ou nome (busca parcial)"),
    documento: Optional[str] = Query(None, description="CPF/CNPJ para busca detalhada"),
    cnpj: Optional[str] = Query(None, description="Alias de documento para CPF/CNPJ"),
    nome: Optional[str] = Query(None, description="Nome da pessoa ou empresa"),
    safra: Optional[str] = Query(None, description="Safra da maquina ou do boleto"),
    safra_maquina: Optional[str] = Query(None, description="Safra da maquininha"),
    nunca_qualificou: Optional[bool] = Query(None, description="Filtra clientes que nunca se qualificaram para comissao"),
    comissao_prox_mes: Optional[str] = Query(None, description="Status de comissao do proximo mes"),
    comissao_este_mes: Optional[str] = Query(None, description="Apuracao de comissao do mes atual"),
    apuracao_comiss: Optional[str] = Query(None, description="Alias tecnico para comissao do mes atual"),
    criterios_atingidos_comissao: Optional[str] = Query(None, description="Criterios atingidos para comissao"),
    criterios_atingidos_comiss: Optional[str] = Query(None, description="Alias tecnico dos criterios atingidos"),
    pix_forte: Optional[str] = Query(None, description="Filtro por chave PIX forte"),
    chaves_pix_forte: Optional[str] = Query(None, description="Alias tecnico para chave PIX forte"),
    cancelamento_maquina: Optional[str] = Query(None, description="Filtro por cancelamento de maquina"),
    cancelamento_maq: Optional[str] = Query(None, description="Alias tecnico para cancelamento de maquina"),
    m2_faltantes: Optional[str] = Query(None, description="Dias faltantes para atingir m2"),
    m2_dias_faltantes: Optional[str] = Query(None, description="Alias tecnico para dias faltantes de m2"),
    boletos: Optional[str] = Query(None, description="Busca por status ou metricas de boleto"),
    fl_bolcob_cadastrado: Optional[str] = Query(None, description="Alias tecnico para cadastro de boleto/cobranca"),
    marco: Optional[str] = Query(None, description="Marco ou criterio proximo a ser atingido"),
    criterio_proximo: Optional[str] = Query(None, description="Alias tecnico para marco"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    repo = VisaoClienteRepository(db)
    documento_consultado = _resolve_documento_consultado(q, documento, cnpj)
    items, total = await repo.search(
        q=q,
        cnpj=documento or cnpj,
        nome=nome,
        safra=safra,
        safra_maquina=safra_maquina,
        nunca_qualificou=nunca_qualificou,
        comissao_prox_mes=comissao_prox_mes,
        apuracao_comiss=comissao_este_mes or apuracao_comiss,
        criterios_atingidos_comiss=criterios_atingidos_comissao or criterios_atingidos_comiss,
        chaves_pix_forte=pix_forte or chaves_pix_forte,
        cancelamento_maq=cancelamento_maquina or cancelamento_maq,
        m2_dias_faltantes=m2_faltantes or m2_dias_faltantes,
        boletos=boletos,
        fl_bolcob_cadastrado=fl_bolcob_cadastrado,
        criterio_proximo=marco or criterio_proximo,
        limit=limit,
        offset=offset,
    )

    applied_filters = {
        "q": q,
        "documento": documento,
        "cnpj": cnpj,
        "nome": nome,
        "safra": safra,
        "safra_maquina": safra_maquina,
        "nunca_qualificou": nunca_qualificou,
        "comissao_prox_mes": comissao_prox_mes,
        "comissao_este_mes": comissao_este_mes,
        "apuracao_comiss": apuracao_comiss,
        "criterios_atingidos_comissao": criterios_atingidos_comissao,
        "criterios_atingidos_comiss": criterios_atingidos_comiss,
        "pix_forte": pix_forte,
        "chaves_pix_forte": chaves_pix_forte,
        "cancelamento_maquina": cancelamento_maquina,
        "cancelamento_maq": cancelamento_maq,
        "m2_faltantes": m2_faltantes,
        "m2_dias_faltantes": m2_dias_faltantes,
        "boletos": boletos,
        "fl_bolcob_cadastrado": fl_bolcob_cadastrado,
        "marco": marco,
        "criterio_proximo": criterio_proximo,
        "limit": limit,
        "offset": offset,
        "view": "completo",
    }

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        payload={key: value for key, value in applied_filters.items() if value is not None},
    )

    return ClienteConsultaResponse(
        documento_consultado=documento_consultado,
        total=total,
        limit=limit,
        offset=offset,
        items=[ClienteConsultaItemResponse.model_validate(i) for i in items],
    )


@router.get(
    "/historico-alteracoes",
    response_model=ClienteHistoricoAlteracoesResponse,
    summary="Historico persistido de alteracoes do cliente",
)
async def get_cliente_historico_alteracoes(
    documento: str = Query(..., description="CPF/CNPJ com ou sem pontuacao"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    documento_consultado = _only_digits(documento)
    if not documento_consultado:
        raise HTTPException(status_code=400, detail="documento invalido")

    repo = VisaoClienteRepository(db)
    items, total = await repo.get_change_history(
        documento=documento_consultado,
        limit=limit,
        offset=offset,
    )

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        resource="cliente_historico_alteracoes",
        resource_id=documento_consultado,
        payload={
            "documento": documento,
            "documento_normalizado": documento_consultado,
            "limit": limit,
            "offset": offset,
        },
    )

    return ClienteHistoricoAlteracoesResponse(
        documento_consultado=documento_consultado,
        total=total,
        limit=limit,
        offset=offset,
        items=[ClienteHistoricoAlteracaoItemResponse.model_validate(i) for i in items],
    )


@router.get("/{cd_cpf_cnpj}", response_model=ClienteDetailResponse, summary="Detalhe completo de cliente")
async def get_cliente(
    cd_cpf_cnpj: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    repo = VisaoClienteRepository(db)
    cliente = await repo.get_by_cnpj(cd_cpf_cnpj)

    if not cliente:
        raise NotFoundException(message=f"Cliente '{cd_cpf_cnpj}' não encontrado.")

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        resource="cliente",
        resource_id=cd_cpf_cnpj,
    )

    return ClienteDetailResponse.model_validate(cliente)
