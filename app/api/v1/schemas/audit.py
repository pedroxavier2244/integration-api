from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


class AuditAction(str, Enum):
    """Ações rastreadas pelo sistema de auditoria."""
    login                    = "login"
    logout                   = "logout"
    login_failed             = "login_failed"
    user_created             = "user_created"
    user_updated             = "user_updated"
    user_deactivated         = "user_deactivated"
    invite_sent              = "invite_sent"
    invite_accepted          = "invite_accepted"
    password_reset_requested = "password_reset_requested"
    password_reset           = "password_reset"
    sessions_revoked         = "sessions_revoked"
    cliente_read             = "cliente_read"
    empresa_read             = "empresa_read"
    crm_inbound              = "crm_inbound"
    crm_outbound             = "crm_outbound"


class AuditLogResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    user_email: Optional[str] = None
    action: AuditAction
    resource: Optional[str] = None           # ex: "cliente", "user", "crm_job"
    resource_id: Optional[str] = None        # ID do recurso afetado
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    payload: Optional[Dict[str, Any]] = None # dados extras sanitizados (sem senhas/tokens)
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditListParams(BaseModel):
    """Parâmetros de filtro e paginação para GET /audit."""
    page: int = 1
    page_size: int = 50
    user_id: Optional[str] = None
    action: Optional[AuditAction] = None
    resource: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
