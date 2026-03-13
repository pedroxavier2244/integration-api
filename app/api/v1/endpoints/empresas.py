from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import RequireEmpresasRead
from app.api.v1.schemas.clientes import EmpresaResponse
from app.api.v1.schemas.audit import AuditAction
from app.api.v1.schemas.common import PaginatedResponse
from app.db.session import get_db
from app.repositories.visao_cliente_repository import VisaoClienteRepository
from app.services.audit_service import AuditService
from app.core.exceptions import NotFoundException

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[EmpresaResponse], summary="Buscar empresas (dados Receita Federal)")
async def list_empresas(
    q: Optional[str] = Query(None, description="CPF/CNPJ ou razão social"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=RequireEmpresasRead,
):
    repo = VisaoClienteRepository(db)
    items, total = await repo.search(q=q, page=page, page_size=page_size)

    await AuditService(db).log(
        action=AuditAction.empresa_read,
        user_id=current_user.sub,
        payload={"q": q, "page": page},
    )

    return PaginatedResponse(
        items=[EmpresaResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{cd_cpf_cnpj}", response_model=EmpresaResponse, summary="Dados RF de uma empresa")
async def get_empresa(
    cd_cpf_cnpj: str,
    db: AsyncSession = Depends(get_db),
    current_user=RequireEmpresasRead,
):
    repo = VisaoClienteRepository(db)
    empresa = await repo.get_by_cnpj(cd_cpf_cnpj)

    if not empresa:
        raise NotFoundException(message=f"Empresa '{cd_cpf_cnpj}' não encontrada.")

    await AuditService(db).log(
        action=AuditAction.empresa_read,
        user_id=current_user.sub,
        resource="empresa",
        resource_id=cd_cpf_cnpj,
    )

    return EmpresaResponse.model_validate(empresa)
