# Clientes Lote — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar `POST /api/v1/clientes/lote` que aceita uma lista de até 100 CNPJs com filtros opcionais e retorna os registros completos de cada um encontrado.

**Architecture:** Novo método `get_by_documentos()` no repositório existente faz `WHERE cd_cpf_cnpj_cliente IN (...)` com filtros opcionais em AND. O endpoint calcula `not_found` comparando os documentos do request com os retornados pelo banco. Dois novos schemas (`ClienteLoteRequest`, `ClienteLoteResponse`) em `schemas/clientes.py`.

**Tech Stack:** FastAPI, SQLAlchemy async (select + IN clause), Pydantic v2 (Field com min_length/max_length em lista), pytest-asyncio, SQLite in-memory (testes).

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `tests/integration/test_clientes_lote_endpoint.py` | Create | 9 testes de integração |
| `app/api/v1/schemas/clientes.py` | Modify | adicionar `ClienteLoteRequest` e `ClienteLoteResponse` |
| `app/repositories/visao_cliente_repository.py` | Modify | adicionar `get_by_documentos()` |
| `app/api/v1/endpoints/clientes.py` | Modify | adicionar `POST /lote` antes de `GET /{cd_cpf_cnpj}` |

---

## Task 1: Criar arquivo de testes com todos os casos de aceite

**Files:**
- Create: `tests/integration/test_clientes_lote_endpoint.py`

- [ ] **Step 1: Criar o arquivo de testes**

```python
"""
Testes de integração para POST /api/v1/clientes/lote.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.visao_cliente import VisaoCliente

BASE = "/api/v1/clientes/lote"


@pytest_asyncio.fixture
async def clientes_lote(db: AsyncSession):
    """3 clientes com UF, status_cc e consultores distintos para testes de lote."""
    c1 = VisaoCliente(
        cd_cpf_cnpj_cliente="10000000000100",
        nome_cliente="CLIENTE SP LIBERADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="LIBERADA",
        ramo_atuacao="VAREJO",
        nome_consultor="Joao Silva",
        cd_cpf_cnpj_consultor="99999999000199",
    )
    c2 = VisaoCliente(
        cd_cpf_cnpj_cliente="20000000000200",
        nome_cliente="CLIENTE RJ BLOQUEADA",
        tipo_pessoa="PJ",
        uf="RJ",
        status_cc="BLOQUEADA",
        ramo_atuacao="SERVICOS",
        nome_consultor="Maria Souza",
        cd_cpf_cnpj_consultor="88888888000188",
    )
    c3 = VisaoCliente(
        cd_cpf_cnpj_cliente="30000000000300",
        nome_cliente="CLIENTE SP BLOQUEADA",
        tipo_pessoa="PJ",
        uf="SP",
        status_cc="BLOQUEADA",
        ramo_atuacao="INDUSTRIA",
        nome_consultor="Carlos Joao",
        cd_cpf_cnpj_consultor="77777777000177",
    )
    db.add_all([c1, c2, c3])
    await db.flush()
    return [c1, c2, c3]


class TestClientesLote:
    async def test_lote_todos_encontrados(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Todos os CNPJs existem → not_found vazio."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "20000000000200", "30000000000300"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 3
        assert data["total_not_found"] == 0
        assert data["not_found"] == []

    async def test_lote_parcialmente_encontrado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Alguns CNPJs existem, outros não → ambas as listas preenchidas."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "99999999999999"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1
        assert data["total_not_found"] == 1
        assert "99999999999999" in data["not_found"]

    async def test_lote_nenhum_encontrado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Nenhum CNPJ existe → found vazio, todos em not_found."""
        resp = await client.post(
            BASE,
            json={"documentos": ["99999999999991", "99999999999992"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 0
        assert data["total_not_found"] == 2
        assert data["found"] == []

    async def test_lote_filtro_uf_exclui_outro_estado(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """CNPJ existe mas é de outro estado → vai para not_found."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100", "20000000000200"], "uf": "SP"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 1
        assert data["found"][0]["cd_cpf_cnpj_cliente"] == "10000000000100"
        assert "20000000000200" in data["not_found"]

    async def test_lote_filtro_consultor_parcial(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """Filtro consultor faz busca parcial — 'joao' bate em 'Joao Silva' e 'Carlos Joao'."""
        resp = await client.post(
            BASE,
            json={
                "documentos": ["10000000000100", "20000000000200", "30000000000300"],
                "consultor": "joao",
            },
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 2

    async def test_lote_response_tem_campos_completos(
        self, client: AsyncClient, admin_token: str, clientes_lote
    ):
        """found retorna ClienteDetailResponse com campos completos."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100"]},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 200
        item = resp.json()["found"][0]
        assert "cd_cpf_cnpj_cliente" in item
        assert "nome_cliente" in item
        assert "uf" in item
        assert "status_cc" in item
        assert item["cd_cpf_cnpj_cliente"] == "10000000000100"

    async def test_lote_documentos_vazio_retorna_422(
        self, client: AsyncClient, admin_token: str
    ):
        """Lista vazia de documentos → 422."""
        resp = await client.post(
            BASE,
            json={"documentos": []},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_lote_mais_de_100_documentos_retorna_422(
        self, client: AsyncClient, admin_token: str
    ):
        """Mais de 100 documentos → 422."""
        docs = [f"{i:014d}" for i in range(101)]
        resp = await client.post(
            BASE,
            json={"documentos": docs},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 422

    async def test_lote_sem_autenticacao_retorna_403(self, client: AsyncClient):
        """Sem token → 403."""
        resp = await client.post(
            BASE,
            json={"documentos": ["10000000000100"]},
        )
        assert resp.status_code == 403
```

- [ ] **Step 2: Rodar os testes para confirmar que falham (não import errors)**

```bash
cd "c:/Users/MB NEGOCIOS/integration-api"
python -m pytest tests/integration/test_clientes_lote_endpoint.py -v --tb=short 2>&1 | head -30
```

Esperado: `ImportError` ou `404` — não erros de sintaxe.

---

## Task 2: Adicionar schemas ClienteLoteRequest e ClienteLoteResponse

**Files:**
- Modify: `app/api/v1/schemas/clientes.py` (final do arquivo, após `EmpresaResponse`)

- [ ] **Step 1: Adicionar `Field` ao import do pydantic**

Localizar a linha 1 do arquivo:
```python
from pydantic import BaseModel, computed_field
```
Substituir por:
```python
from pydantic import BaseModel, Field, computed_field
```

- [ ] **Step 2: Adicionar os 2 novos schemas ao final do arquivo**

Após a classe `EmpresaResponse` (última classe do arquivo), adicionar:

```python

class ClienteLoteRequest(BaseModel):
    """Request para busca em lote de clientes por lista de CPF/CNPJ."""
    documentos: List[str] = Field(..., min_length=1, max_length=100)
    uf: Optional[str] = None
    status_cc: Optional[str] = None
    ramo_atuacao: Optional[str] = None
    consultor: Optional[str] = None


class ClienteLoteResponse(BaseModel):
    """Resposta da busca em lote."""
    found: List[ClienteDetailResponse]
    not_found: List[str]
    total_found: int
    total_not_found: int
```

- [ ] **Step 3: Verificar importação**

```bash
cd "c:/Users/MB NEGOCIOS/integration-api"
python -c "from app.api.v1.schemas.clientes import ClienteLoteRequest, ClienteLoteResponse; print('OK')"
```

Esperado: `OK`

---

## Task 3: Adicionar get_by_documentos() ao repositório

**Files:**
- Modify: `app/repositories/visao_cliente_repository.py`

- [ ] **Step 1: Adicionar `get_by_documentos()` após o método `get_by_cnpj()`**

Localizar o método `get_by_cnpj()` (linha ~48). Após ele, inserir:

```python
    async def get_by_documentos(
        self,
        documentos: List[str],
        uf: Optional[str] = None,
        status_cc: Optional[str] = None,
        ramo_atuacao: Optional[str] = None,
        consultor: Optional[str] = None,
    ) -> List[VisaoCliente]:
        """Busca em lote por lista de CPF/CNPJ com filtros opcionais (AND)."""
        query = select(VisaoCliente).where(
            VisaoCliente.cd_cpf_cnpj_cliente.in_(documentos)
        )
        filters = []

        if uf:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.uf, "")) == uf.strip().upper()
            )

        if status_cc:
            filters.append(
                func.upper(func.coalesce(VisaoCliente.status_cc, "")) == status_cc.strip().upper()
            )

        if ramo_atuacao:
            filters.append(self._contains(VisaoCliente.ramo_atuacao, ramo_atuacao))

        if consultor:
            pattern = f"%{consultor.strip().upper()}%"
            filters.append(or_(
                func.upper(func.coalesce(VisaoCliente.nome_consultor, "")).like(pattern),
                VisaoCliente.cd_cpf_cnpj_consultor.ilike(f"%{consultor.strip()}%"),
            ))

        if filters:
            query = query.where(*filters)

        result = await self.db.execute(query)
        return list(result.scalars().all())
```

- [ ] **Step 2: Verificar importação**

```bash
cd "c:/Users/MB NEGOCIOS/integration-api"
python -c "from app.repositories.visao_cliente_repository import VisaoClienteRepository; import inspect; print([m for m in dir(VisaoClienteRepository) if 'documento' in m])"
```

Esperado: `['get_by_documentos']`

---

## Task 4: Adicionar endpoint POST /lote em clientes.py

**Files:**
- Modify: `app/api/v1/endpoints/clientes.py`

- [ ] **Step 1: Adicionar imports necessários**

Localizar o bloco de imports do schemas (linha ~8):
```python
from app.api.v1.schemas.clientes import (
    ClienteResumoResponse, ClienteDetailResponse,
    ClienteConsultaItemResponse, ClienteConsultaResponse,
    ClienteHistoricoAlteracaoItemResponse, ClienteHistoricoAlteracoesResponse,
    ClienteListResponse, IndicadoresResponse,
)
```

Substituir por:
```python
from app.api.v1.schemas.clientes import (
    ClienteResumoResponse, ClienteDetailResponse,
    ClienteConsultaItemResponse, ClienteConsultaResponse,
    ClienteHistoricoAlteracaoItemResponse, ClienteHistoricoAlteracoesResponse,
    ClienteListResponse, IndicadoresResponse,
    ClienteLoteRequest, ClienteLoteResponse,
)
```

- [ ] **Step 2: Adicionar o endpoint POST /lote**

Inserir **antes** de `@router.get("/{cd_cpf_cnpj}", ...)` (linha ~293), após o endpoint `get_cliente_historico_alteracoes`:

```python

@router.post(
    "/lote",
    response_model=ClienteLoteResponse,
    summary="Busca em lote de clientes por lista de CPF/CNPJ",
)
async def get_clientes_lote(
    body: ClienteLoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user=RequireClientesRead,
):
    repo = VisaoClienteRepository(db)
    found_items = await repo.get_by_documentos(
        documentos=body.documentos,
        uf=body.uf,
        status_cc=body.status_cc,
        ramo_atuacao=body.ramo_atuacao,
        consultor=body.consultor,
    )
    found_docs = {item.cd_cpf_cnpj_cliente for item in found_items}
    not_found = [doc for doc in body.documentos if doc not in found_docs]

    await AuditService(db).log(
        action=AuditAction.cliente_read,
        user_id=current_user.sub,
        payload={k: v for k, v in {
            "total_documentos": len(body.documentos),
            "uf": body.uf,
            "status_cc": body.status_cc,
            "ramo_atuacao": body.ramo_atuacao,
            "consultor": body.consultor,
        }.items() if v is not None},
    )

    return ClienteLoteResponse(
        found=[ClienteDetailResponse.model_validate(i) for i in found_items],
        not_found=not_found,
        total_found=len(found_items),
        total_not_found=len(not_found),
    )
```

---

## Task 5: Rodar testes, commitar e deployar

- [ ] **Step 1: Rodar apenas os novos testes**

```bash
cd "c:/Users/MB NEGOCIOS/integration-api"
python -m pytest tests/integration/test_clientes_lote_endpoint.py -v --tb=short
```

Esperado — todos os 9 testes passam:
```
PASSED test_lote_todos_encontrados
PASSED test_lote_parcialmente_encontrado
PASSED test_lote_nenhum_encontrado
PASSED test_lote_filtro_uf_exclui_outro_estado
PASSED test_lote_filtro_consultor_parcial
PASSED test_lote_response_tem_campos_completos
PASSED test_lote_documentos_vazio_retorna_422
PASSED test_lote_mais_de_100_documentos_retorna_422
PASSED test_lote_sem_autenticacao_retorna_403
```

- [ ] **Step 2: Rodar suite completa para garantir sem regressão**

```bash
python -m pytest tests/integration/test_empresas_endpoints.py tests/integration/test_clientes_lote_endpoint.py -v --tb=short
```

Esperado: todos passando.

- [ ] **Step 3: Commit**

```bash
git add \
  app/api/v1/schemas/clientes.py \
  app/repositories/visao_cliente_repository.py \
  app/api/v1/endpoints/clientes.py \
  tests/integration/test_clientes_lote_endpoint.py

git commit -m "feat: POST /clientes/lote — busca em lote por lista de CNPJs com filtros"
```

- [ ] **Step 4: Push e deploy na VPS**

```bash
git push
```

SSH na VPS (5.189.163.33, root, senha: cb5D75sc41Txr):
```bash
cd /opt/apps/integration-api
git pull
docker compose -f docker-compose.vps.yml build api
docker compose -f docker-compose.vps.yml up -d api
```

- [ ] **Step 5: Smoke test em produção**

```bash
TOKEN=$(curl -s -X POST http://5.189.163.33:8002/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@mbfinance.com.br","password":"Admin@123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://5.189.163.33:8002/api/v1/clientes/lote \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"documentos":["49458062000130","20484329000182","00000000000000"]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('found:', d['total_found'], '| not_found:', d['total_not_found'], '|', d['not_found'])"
```

Esperado: `found: 2 | not_found: 1 | ['00000000000000']`

---

## Self-Review

**Spec coverage:**
- ✅ `documentos` min 1, max 100 — Task 2 (`Field(..., min_length=1, max_length=100)`)
- ✅ `uf` filtro exato case-insensitive — Task 3
- ✅ `status_cc` filtro exato case-insensitive — Task 3
- ✅ `ramo_atuacao` busca parcial — Task 3
- ✅ `consultor` busca parcial em nome e CNPJ — Task 3
- ✅ `found` com `ClienteDetailResponse` completo — Task 4
- ✅ `not_found` lista documentos ausentes — Task 4
- ✅ `total_found` e `total_not_found` — Task 2 schema + Task 4
- ✅ CNPJ que existe mas não passa no filtro → `not_found` — Task 4 (lógica de set)
- ✅ Auth `clientes:read` — Task 4 (`RequireClientesRead`)
- ✅ 422 para lista vazia — Task 2 (`min_length=1`)
- ✅ 422 para mais de 100 — Task 2 (`max_length=100`)
- ✅ 403 sem auth — Task 4 (`RequireClientesRead`)
- ✅ Auditoria — Task 4 (`AuditService.log`)

**Placeholder scan:** Nenhum TBD, TODO ou "implement later".

**Type consistency:** `get_by_documentos()` retorna `List[VisaoCliente]`. Endpoint usa `ClienteDetailResponse.model_validate(i)` — consistente com `get_cliente` existente. `ClienteLoteRequest` e `ClienteLoteResponse` nomeados identicamente em Tasks 2 e 4.
