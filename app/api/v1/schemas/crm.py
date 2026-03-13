from pydantic import BaseModel, field_validator
from typing import Optional, List, Any, Dict
from datetime import datetime
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class CrmEventType(str, Enum):
    """
    Tipos de evento que o CRM pode enviar (inbound).
    PENDENTE: alinhar com o CRM real — adicionar/remover conforme contrato de integração.
    """
    contato_realizado = "contato_realizado"
    proposta_enviada  = "proposta_enviada"
    contrato_fechado  = "contrato_fechado"
    churn             = "churn"
    atualizacao_dados = "atualizacao_dados"


class CrmSyncStatus(str, Enum):
    pending   = "pending"
    sent      = "sent"
    failed    = "failed"
    confirmed = "confirmed"


# ─── Inbound (CRM → API) ──────────────────────────────────────────────────────

class CrmInboundEventRequest(BaseModel):
    """
    Payload enviado pelo CRM para registrar um evento na API.
    PENDENTE: validar campos obrigatórios reais com o CRM.
    """
    cd_cpf_cnpj_cliente: str
    event_type: CrmEventType
    event_at: datetime
    payload: Optional[Dict[str, Any]] = None    # dados extras livres do CRM
    crm_record_id: Optional[str] = None         # ID do registro no CRM (usado para idempotência)

    @field_validator("cd_cpf_cnpj_cliente")
    @classmethod
    def document_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("cd_cpf_cnpj_cliente não pode ser vazio.")
        return v.strip()


class CrmInboundEventResponse(BaseModel):
    id: str                    # UUID gerado pela API
    cd_cpf_cnpj_cliente: str
    event_type: CrmEventType
    event_at: datetime
    status: CrmSyncStatus
    received_at: datetime
    model_config = {"from_attributes": True}


class CrmInboundBatchRequest(BaseModel):
    """Envio em lote de eventos pelo CRM (máx. 500 por chamada)."""
    events: List[CrmInboundEventRequest]

    @field_validator("events")
    @classmethod
    def events_not_empty(cls, v: List) -> List:
        if not v:
            raise ValueError("Lista de eventos não pode ser vazia.")
        if len(v) > 500:
            raise ValueError("Máximo de 500 eventos por lote.")
        return v


class CrmInboundBatchResponse(BaseModel):
    total: int
    accepted: int
    rejected: int
    errors: List[Dict[str, Any]] = []


# ─── Outbound (API → CRM) ─────────────────────────────────────────────────────

class CrmOutboundExportRequest(BaseModel):
    """
    Solicita exportação/sincronização de clientes para o CRM.
    PENDENTE: definir filtros reais conforme necessidade do CRM.
    Sem filtros = exporta todos os clientes ativos.
    """
    cd_cpf_cnpj_clientes: Optional[List[str]] = None   # lista específica; None = todos
    segmento: Optional[str] = None
    uf: Optional[str] = None
    data_base_inicio: Optional[str] = None
    data_base_fim: Optional[str] = None


class CrmOutboundExportResponse(BaseModel):
    """Resposta imediata ao solicitar exportação (job assíncrono via Celery)."""
    job_id: str
    status: CrmSyncStatus
    total_records: int
    queued_at: datetime


class CrmOutboundStatusResponse(BaseModel):
    """Status detalhado de um job de exportação."""
    job_id: str
    status: CrmSyncStatus
    total_records: int
    sent: int
    failed: int
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    errors: List[Dict[str, Any]] = []
    model_config = {"from_attributes": True}
