# Empresas — Filtros de Carteira para Tela do Gestor

## Contexto

O gestor de carteira precisa visualizar todas as empresas de uma vez para fazer distribuição de leads. Hoje o endpoint `GET /empresas` só aceita busca por `q` (CNPJ ou nome) com `page_size` máximo de 100, o que torna inviável trabalhar a carteira em bloco.

## Objetivo

Expandir `GET /empresas` com filtros operacionais e aumentar o `page_size` máximo, sem criar novo endpoint.

## Escopo

### O que muda

**`GET /api/v1/empresas`** — novos query params opcionais:

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `uf` | `str` | Filtro exato por UF (ex: `SP`) |
| `status_cc` | `str` | Filtro exato por status da conta corrente (ex: `LIBERADA`) |
| `ramo_atuacao` | `str` | Busca parcial case-insensitive no ramo de atuação |
| `consultor` | `str` | Busca parcial no nome ou CNPJ do consultor |
| `page_size` | `int` | Aumenta máximo de 100 para 500 |

Todos os filtros são opcionais e combinam entre si (AND).

**`EmpresaResponse`** — 2 campos novos:

| Campo | Tipo | Fonte |
|---|---|---|
| `nome_consultor` | `str \| None` | `etl.final_visao_cliente.nome_consultor` |
| `cd_cpf_cnpj_consultor` | `str \| None` | `etl.final_visao_cliente.cd_cpf_cnpj_consultor` |

### O que NÃO muda

- Autenticação e autorização (`RequireEmpresasRead`) — inalteradas
- Auditoria — inalterada
- Endpoint `/empresas/{cd_cpf_cnpj}` — inalterado
- Paginação — mantida (sem modo "exportar tudo")

## Arquivos a modificar

| Arquivo | Mudança |
|---|---|
| `app/api/v1/schemas/clientes.py` | Adicionar `nome_consultor` e `cd_cpf_cnpj_consultor` em `EmpresaResponse` |
| `app/repositories/visao_cliente_repository.py` | Adicionar método `search_empresas()` com os 4 filtros novos |
| `app/api/v1/endpoints/empresas.py` | Adicionar 4 query params e chamar `search_empresas()`, page_size max 500 |

## Comportamento dos filtros

- `uf`: `WHERE uf = :uf` (case-insensitive, strip)
- `status_cc`: `WHERE UPPER(status_cc) = UPPER(:status_cc)`
- `ramo_atuacao`: `WHERE UPPER(ramo_atuacao) LIKE '%VALUE%'`
- `consultor`: `WHERE UPPER(nome_consultor) LIKE '%VALUE%' OR cd_cpf_cnpj_consultor LIKE '%VALUE%'`
- Filtros combinam com AND
- `q` existente (busca por CNPJ ou nome) continua funcionando em conjunto

## Critérios de aceitação

1. `GET /empresas?uf=SP` retorna apenas empresas do estado SP
2. `GET /empresas?status_cc=LIBERADA&uf=RJ` retorna empresas com conta liberada no RJ
3. `GET /empresas?consultor=joao` retorna empresas cujo consultor tem "joao" no nome
4. `GET /empresas?page_size=500` aceita e retorna até 500 registros
5. `GET /empresas` sem filtros continua funcionando igual a antes
6. `EmpresaResponse` inclui `nome_consultor` e `cd_cpf_cnpj_consultor`
7. Todos os filtros são opcionais — nenhum é obrigatório

## Testes

- `test_empresas_filtro_uf` — filtra por UF e verifica que só retorna da UF correta
- `test_empresas_filtro_status_cc` — filtra por status e verifica resultado
- `test_empresas_filtro_consultor` — filtra por nome parcial do consultor
- `test_empresas_filtros_combinados` — combina uf + status_cc e verifica AND
- `test_empresas_page_size_500` — page_size=500 retorna 200 OK
- `test_empresas_sem_filtro` — sem params continua funcionando
- `test_empresa_response_tem_consultor` — response inclui campos de consultor
