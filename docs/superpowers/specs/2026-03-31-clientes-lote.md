# Spec: POST /clientes/lote — Busca em Lote por Lista de CNPJs

**Data:** 2026-03-31
**Status:** approved

---

## Objetivo

Permitir que o frontend (ou qualquer consumidor da API) envie uma lista de até 100 documentos (CPF/CNPJ) e receba de volta o registro completo de cada um encontrado, com filtros opcionais adicionais.

---

## Endpoint

```
POST /api/v1/clientes/lote
Authorization: Bearer <token>
Content-Type: application/json
```

**Permissão:** `clientes:read` (mesmo nível do `GET /clientes/`)

---

## Request

### Schema: `ClienteLoteRequest`

| Campo | Tipo | Obrigatório | Regra |
|---|---|---|---|
| `documentos` | `List[str]` | sim | mínimo 1, máximo 100 itens |
| `uf` | `str` | não | filtro exato, case-insensitive (ex: `SP`) |
| `status_cc` | `str` | não | filtro exato, case-insensitive (ex: `LIBERADA`) |
| `ramo_atuacao` | `str` | não | busca parcial case-insensitive |
| `consultor` | `str` | não | busca parcial no `nome_consultor` ou `cd_cpf_cnpj_consultor` |

Todos os filtros são opcionais e combinam com AND sobre a lista de documentos.

Exemplo:
```json
{
  "documentos": ["11111111000111", "22222222000122", "33333333000133"],
  "uf": "SP",
  "status_cc": "LIBERADA",
  "ramo_atuacao": null,
  "consultor": null
}
```

---

## Response

### Schema: `ClienteLoteResponse`

| Campo | Tipo | Descrição |
|---|---|---|
| `found` | `List[ClienteDetailResponse]` | registros completos encontrados |
| `not_found` | `List[str]` | documentos que não existem na base |
| `total_found` | `int` | quantidade de registros retornados |
| `total_not_found` | `int` | quantidade de documentos não encontrados |

`ClienteDetailResponse` é o schema já existente em `app/api/v1/schemas/clientes.py` com todos os campos de `etl.final_visao_cliente`.

Exemplo:
```json
{
  "found": [
    {
      "cd_cpf_cnpj_cliente": "11111111000111",
      "nome_cliente": "EMPRESA SP LIBERADA",
      "uf": "SP",
      "status_cc": "LIBERADA",
      "...": "todos os campos de ClienteDetailResponse"
    }
  ],
  "not_found": ["33333333000133"],
  "total_found": 2,
  "total_not_found": 1
}
```

---

## Comportamento dos filtros

- Os filtros são aplicados **sobre a lista de documentos** — um CNPJ que existe na base mas não passa no filtro vai para `not_found`.
- Lógica: `cd_cpf_cnpj_cliente IN (:documentos) AND <filtros opcionais>`
- `uf` e `status_cc`: comparação exata `UPPER(campo) = UPPER(:valor)`
- `ramo_atuacao`: `LIKE %valor%` case-insensitive
- `consultor`: `LIKE %valor%` em `nome_consultor` OR `cd_cpf_cnpj_consultor`

---

## Validação e erros

| Situação | HTTP | Resposta |
|---|---|---|
| `documentos` ausente ou vazio | 422 | erro de validação Pydantic |
| `documentos` com mais de 100 itens | 422 | erro de validação Pydantic |
| Nenhum documento encontrado | 200 | `found: [], not_found: [todos]` |
| Sem autenticação | 403 | padrão da API |

---

## Arquivos a modificar

| Arquivo | Ação | O que muda |
|---|---|---|
| `app/api/v1/schemas/clientes.py` | Modify | adicionar `ClienteLoteRequest` e `ClienteLoteResponse` |
| `app/repositories/visao_cliente_repository.py` | Modify | adicionar `get_by_documentos()` |
| `app/api/v1/endpoints/clientes.py` | Modify | adicionar `POST /lote` |
| `tests/integration/test_clientes_lote_endpoint.py` | Create | testes de integração |

---

## Método no repositório: `get_by_documentos()`

```python
async def get_by_documentos(
    self,
    documentos: List[str],
    uf: Optional[str] = None,
    status_cc: Optional[str] = None,
    ramo_atuacao: Optional[str] = None,
    consultor: Optional[str] = None,
) -> List[VisaoCliente]:
```

- Faz `WHERE cd_cpf_cnpj_cliente IN (:documentos)` + filtros opcionais
- Retorna lista de `VisaoCliente` — o endpoint calcula `not_found` comparando os documentos do request com os `cd_cpf_cnpj_cliente` retornados

---

## Testes a cobrir

1. lote com todos os documentos encontrados → `not_found` vazio
2. lote com documentos mistos (alguns existem, alguns não) → `found` e `not_found` corretos
3. lote onde nenhum documento existe → `found` vazio, todos em `not_found`
4. filtro `uf` reduz resultado — CNPJ existe mas é de outro estado → vai para `not_found`
5. filtro `consultor` parcial funciona
6. `documentos` com mais de 100 itens → 422
7. `documentos` vazio → 422
8. sem autenticação → 403
