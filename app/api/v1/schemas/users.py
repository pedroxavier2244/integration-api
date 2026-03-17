from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserRole(str, Enum):
    admin = "admin"
    gestor = "gestor"
    operador = "operador"


ROLE_PERMISSIONS: dict[UserRole, List[str]] = {
    UserRole.admin: [
        "clientes:read",
        "empresas:read",
        "crm:inbound",
        "crm:outbound",
        "audit:read",
        "users:manage",
    ],
    UserRole.gestor: [
        "clientes:read",
        "empresas:read",
        "crm:outbound",
        "audit:read",
        "users:team:manage",
    ],
    UserRole.operador: [
        "clientes:read",
        "empresas:read",
        "crm:inbound",
    ],
}


def get_permissions(role: UserRole) -> List[str]:
    return ROLE_PERMISSIONS.get(role, [])


class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: str
    role: UserRole
    gestor_id: Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Nome completo nao pode ser vazio.")
        return v.strip()


class CreateUserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    gestor_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    invite_sent: bool = True
    model_config = {"from_attributes": True}


class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    gestor_id: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
    gestor_id: Optional[str] = None
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int


class DeactivateUserResponse(BaseModel):
    success: bool = True
    message: str = "Usuario desativado com sucesso."


class RevokeSessionsResponse(BaseModel):
    success: bool = True
    message: str = "Todas as sessoes ativas foram revogadas."


class ResendInviteResponse(BaseModel):
    success: bool = True
    message: str = "Email de convite reenviado com sucesso."
