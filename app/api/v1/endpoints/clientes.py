from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireClientesRead, get_current_user
from app.api.v1.schemas.clientes import (
    ClienteResumoResponse, ClienteDetailResponse,
    ClienteListResponse, IndicadoresResponse,
)
from app.api.v1.schemas.audit import AuditAction
from app.db.session import get_db
from app.repositories.visao_cliente_repository import VisaoClienteRepository
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException

router = APIRouter()


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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    repo = VisaoClienteRepository(db)
    items, total = await repo.search(q=q, page=page, page_size=page_size)

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        payload={"q": q, "page": page},
    )

    return ClienteListResponse(
        items=[ClienteResumoResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
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
