from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.core.exceptions import ForbiddenException
from app.api.v1.schemas.auth import TokenPayload
from app.db.session import get_db

bearer_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> TokenPayload:
    return decode_access_token(credentials.credentials)


def require_permission(permission: str):
    async def _check(user: TokenPayload = Depends(get_current_user)) -> TokenPayload:
        if permission not in user.permissions:
            raise ForbiddenException(
                message=f"Você não tem permissão para executar esta ação. Requerido: '{permission}'."
            )
        return user
    return _check


RequireClientesRead = Depends(require_permission("clientes:read"))
RequireEmpresasRead = Depends(require_permission("empresas:read"))
RequireCrmInbound   = Depends(require_permission("crm:inbound"))
RequireCrmOutbound  = Depends(require_permission("crm:outbound"))
RequireAuditRead    = Depends(require_permission("audit:read"))
RequireUsersManage  = Depends(require_permission("users:manage"))

DBSession = Depends(get_db)
