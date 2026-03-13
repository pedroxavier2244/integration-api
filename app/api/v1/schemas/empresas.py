from pydantic import BaseModel
from typing import Optional
from datetime import date


class EmpresaResponse(BaseModel):
    """
    Schema para dados de empresa (clientes PJ).

    PENDENTE: confirmar após acesso ao Neon se empresas vêm de:
      (a) final_visao_cliente com filtro tipo_pessoa = 'PJ', ou
      (b) tabela dedicada separada.
    Ajustar campos e model conforme descoberta.
    """
    cd_cpf_cnpj_cliente: str                # CNPJ da empresa
    data_base: date                          # data do registro mais recente no ETL
    razao_social: Optional[str] = None      # PENDENTE: confirmar nome da coluna
    nome_fantasia: Optional[str] = None     # PENDENTE: confirmar se existe
    uf: Optional[str] = None               # PENDENTE: confirmar
    segmento: Optional[str] = None         # PENDENTE: confirmar
    # PENDENTE: adicionar campos específicos de PJ após acesso ao Neon

    model_config = {"from_attributes": True}


class EmpresaDetailResponse(EmpresaResponse):
    """
    Versão completa para endpoint de detalhe (GET /empresas/{cnpj}).
    PENDENTE: expandir após acesso ao Neon.
    """
    pass  # PENDENTE: adicionar campos completos


class EmpresaListParams(BaseModel):
    """Parâmetros de filtro e paginação para GET /empresas."""
    page: int = 1
    page_size: int = 20
    cnpj: Optional[str] = None              # busca exata por CNPJ
    razao_social: Optional[str] = None      # PENDENTE: busca parcial (ILIKE)
    uf: Optional[str] = None
    segmento: Optional[str] = None
