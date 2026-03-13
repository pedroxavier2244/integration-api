from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, users, clientes, empresas, crm_inbound, crm_outbound, audit

api_router = APIRouter()

api_router.include_router(health.router, tags=["Health"])
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(users.router, prefix="/users", tags=["Usuários"])
api_router.include_router(clientes.router, prefix="/clientes", tags=["Clientes"])
api_router.include_router(empresas.router, prefix="/empresas", tags=["Empresas"])
api_router.include_router(crm_inbound.router, prefix="/crm/inbound", tags=["CRM — Inbound"])
api_router.include_router(crm_outbound.router, prefix="/crm/outbound", tags=["CRM — Outbound"])
api_router.include_router(audit.router, prefix="/audit", tags=["Auditoria"])
