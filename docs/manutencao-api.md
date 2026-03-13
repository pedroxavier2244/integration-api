# Guia de Manutencao da Integration API

## 1. Objetivo

Este documento descreve como operar, manter, publicar e diagnosticar a `integration-api`.
O foco aqui e manutencao tecnica e operacional. Para consumo por frontend, CRM ou outro sistema, use o [Guia de Integracao](guia-integracao.md).

## 2. Visao geral da arquitetura

### 2.1 Componentes

- API HTTP: FastAPI
- Runtime: Python 3.12
- Banco: PostgreSQL compartilhado com o ETL
- Cache/infra auxiliar: Redis
- Email: SMTP via `aiosmtplib`
- Worker async no repo: Celery para rotas CRM outbound
- Deploy atual de referencia: container Docker `integration-api`

### 2.2 Papel da API

A API nao processa a planilha diretamente. Ela:

- autentica usuarios e controla permissoes
- consulta dados consolidados do ETL
- registra logs de auditoria
- recebe e orquestra eventos CRM
- expoe contratos HTTP para integracao

### 2.3 Fonte de dados principal

A fonte principal do dominio de clientes e:

- `public.final_visao_cliente`

Essa tabela e populada pelo projeto ETL (`implementation` / `etl-system`). A `integration-api` apenas le esse dataset.

### 2.4 Fluxo de dados ponta a ponta

Fluxo resumido:

1. o ETL processa a planilha e consolida os dados em `staging_visao_cliente`
2. o ETL promove o resultado para `final_visao_cliente`
3. a `integration-api` consulta `final_visao_cliente` para responder clientes e empresas
4. a propria API grava suas tabelas de autenticacao, auditoria e CRM no mesmo banco

Consequencia operacional importante:

- se um campo nao chegou ao endpoint, a verificacao deve cobrir ETL, schema do banco e mapeamento da API

## 3. Tabelas utilizadas

### 3.1 Tabelas legadas / do ETL

- `final_visao_cliente`
- `staging_visao_cliente`
- `cnpj_rf_cache`
- `cnpj_divergencia`
- `analytics_indicator_snapshot`
- `etl_file`
- `etl_job_run`
- `etl_job_step`

### 3.2 Tabelas proprias da Integration API

- `users`
- `refresh_tokens`
- `password_reset_tokens`
- `audit_logs`
- `crm_inbound_events`
- `crm_outbound_jobs`

### 3.3 Regra de ownership

- `final_visao_cliente` e `staging_visao_cliente` pertencem ao ETL.
- As tabelas de autenticacao, auditoria e CRM pertencem a esta API.

## 4. Rotas expostas

### 4.1 Health

- `GET /api/v1/health`

### 4.2 Autenticacao

- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`
- `POST /api/v1/auth/reset-password`
- `POST /api/v1/auth/accept-invite`
- `POST /api/v1/auth/validate-token`

### 4.3 Usuarios

- `POST /api/v1/users`
- `GET /api/v1/users`
- `GET /api/v1/users/{user_id}`
- `PATCH /api/v1/users/{user_id}`
- `DELETE /api/v1/users/{user_id}`
- `POST /api/v1/users/{user_id}/revoke-sessions`
- `POST /api/v1/users/{user_id}/resend-invite`

### 4.4 Clientes

- `GET /api/v1/clientes/indicadores`
- `GET /api/v1/clientes`
- `GET /api/v1/clientes/completo`
- `GET /api/v1/clientes/{cd_cpf_cnpj}`

### 4.5 Empresas

- `GET /api/v1/empresas`
- `GET /api/v1/empresas/{cd_cpf_cnpj}`

### 4.6 CRM

- `POST /api/v1/crm/inbound/events`
- `POST /api/v1/crm/inbound/events/batch`
- `POST /api/v1/crm/outbound/export`
- `GET /api/v1/crm/outbound/export/{job_id}`

### 4.7 Auditoria

- `GET /api/v1/audit`

## 5. Perfis e permissoes

### 5.1 Roles

- `admin`
- `gestor`
- `operador`

### 5.2 Mapa de permissoes

`admin`

- `clientes:read`
- `empresas:read`
- `crm:inbound`
- `crm:outbound`
- `audit:read`
- `users:manage`

`gestor`

- `clientes:read`
- `empresas:read`
- `crm:outbound`
- `audit:read`

`operador`

- `clientes:read`
- `empresas:read`
- `crm:inbound`

## 6. Variaveis de ambiente

As variaveis abaixo estao documentadas em [.env.example](../.env.example).

### 6.1 Aplicacao

- `APP_NAME`
- `APP_VERSION`
- `ENVIRONMENT`
- `DEBUG`
- `API_PREFIX`
- `ALLOWED_HOSTS`
- `RATE_LIMIT_LOGIN`

### 6.2 JWT

- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`
- `JWT_REFRESH_TOKEN_EXPIRE_DAYS`
- `JWT_INVITE_TOKEN_EXPIRE_HOURS`
- `JWT_RESET_TOKEN_EXPIRE_HOURS`

### 6.3 Banco

- `DATABASE_URL`
- `DATABASE_POOL_SIZE`
- `DATABASE_MAX_OVERFLOW`

### 6.4 Redis

- `REDIS_URL`

### 6.5 Email

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`
- `SMTP_TLS`

### 6.6 Frontend

- `FRONTEND_URL`

## 7. Deploy local

### 7.1 Requisitos

- Python 3.12
- PostgreSQL acessivel
- Redis acessivel

### 7.2 Instalacao

```bash
cp .env.example .env
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 7.3 Validacao

```bash
curl http://localhost:8000/api/v1/health
```

## 8. Deploy de referencia na VPS

### 8.1 Arquivos usados

- [Dockerfile](../Dockerfile)
- [docker-compose.vps.yml](../docker-compose.vps.yml)

### 8.2 Topologia de referencia

- container: `integration-api`
- porta host padrao: `8002`
- porta interna: `8000`
- rede Docker compartilhada com ETL: `implementation_default`

### 8.3 Passo a passo

```bash
git pull --ff-only origin main
docker compose -f docker-compose.vps.yml up -d --build
docker ps
curl http://127.0.0.1:8002/api/v1/health
```

### 8.4 Healthcheck

O compose usa o endpoint:

```text
GET /api/v1/health
```

## 9. Operacao de rotina

### 9.1 Conferir saude

```bash
curl http://127.0.0.1:8002/api/v1/health
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 9.2 Ver logs

```bash
docker logs --tail=200 integration-api
```

### 9.3 Rebuild da API

```bash
docker compose -f docker-compose.vps.yml up -d --build
```

### 9.4 Rollback

```bash
git checkout <commit_ou_tag_anterior>
docker compose -f docker-compose.vps.yml up -d --build
```

### 9.5 Smoke test minimo pos-deploy

Depois de qualquer publicacao, valide no minimo:

```bash
curl http://127.0.0.1:8002/api/v1/health
curl -X POST http://127.0.0.1:8002/api/v1/auth/login -H "Content-Type: application/json" -d '{"email":"adm@teste.com","password":"123456"}'
curl "http://127.0.0.1:8002/api/v1/clientes/completo?documento=26018023000117&limit=1&offset=0" -H "Authorization: Bearer <token>"
```

## 10. Usuarios e autenticacao

### 10.1 Criacao de usuarios

O fluxo oficial e por:

- `POST /api/v1/users`

Isso cria o usuario, gera token de convite e envia email.

### 10.2 Ambientes sem SMTP funcional

Se o SMTP nao estiver operacional:

- a criacao de usuario pode falhar ao enviar email
- em ambientes internos, o cadastro pode ser feito diretamente no banco apenas para suporte ou teste

### 10.3 Revogacao de sessoes

Use:

- `POST /api/v1/users/{user_id}/revoke-sessions`

### 10.4 Reset de senha

Fluxo:

1. `POST /api/v1/auth/forgot-password`
2. usuario recebe token
3. `POST /api/v1/auth/reset-password`

## 11. Observabilidade

### 11.1 Headers de rastreio

A API adiciona:

- `X-Trace-Id`
- `X-Correlation-Id`

Se o cliente enviar esses headers, a API reutiliza os valores.

### 11.2 Logs

Cada request gera ao menos:

- `request_started`
- `request_finished`

Campos relevantes:

- `trace_id`
- `correlation_id`
- `method`
- `path`
- `status_code`
- `duration_ms`

### 11.3 Auditoria de negocio

A tabela `audit_logs` registra eventos como:

- login
- logout
- leitura de cliente
- leitura de empresa
- criacao e alteracao de usuario
- eventos CRM

## 12. Observacoes de dados

### 12.1 Tabela de clientes

O endpoint `/clientes/completo` espelha `final_visao_cliente` e acrescenta aliases calculados.

### 12.2 Tipagem real

Muitos campos semanticamente numericos ou de data ainda saem como string porque refletem o legado do ETL.
Exemplos:

- `tpv_m0`
- `pct_cash_in`
- `dias_desde_abertura`
- `threshold_spending`

Excecao importante:

- `metrica_ativacao`
- `metrica_progresso`
- `metrica_urgencia`
- `metrica_financeiro`
- `metrica_intencao`
- `score_perfil`

Esses campos hoje sao `float`.

### 12.3 Valores literais "nan"

Alguns campos podem chegar como `"nan"` em vez de `null`, porque esse valor ja vem assim da carga do ETL.
Consumidores devem tratar `"nan"` como ausencia de dado quando fizer sentido.

### 12.4 Campos alias

Os campos abaixo sao montados pela API a partir de `rf_*`:

- `nome_fantasia`
- `situacao_cadastral`
- `cnae_fiscal`
- `natureza_juridica`
- `capital_social`
- `porte`
- `data_inicio_ativ`

Os campos abaixo existem no contrato, mas atualmente podem vir `null`:

- `descricao_situacao`
- `cnae_descricao`

## 13. Cuidado critico com migrations

### 13.1 Banco compartilhado

O banco `etl_db` e compartilhado com o projeto `implementation`.

### 13.2 Risco

Existe risco de conflito de `alembic_version` se a `integration-api` tentar gerenciar o mesmo banco com um historico Alembic diferente do ETL.

### 13.3 Regra operacional recomendada

- nao execute `alembic upgrade head` da `integration-api` cegamente no mesmo `etl_db`
- trate o schema compartilhado como controlado pelo ETL
- se precisar adicionar tabela propria da API no mesmo banco, alinhe antes a estrategia de versionamento

### 13.4 Estado atual de referencia

No ambiente de referencia, o schema compartilhado foi alinhado manualmente para suportar:

- colunas de safra/cancelamento/elegibilidade
- colunas de metricas e `score_perfil`

### 13.5 Procedimento seguro para alteracao de schema

Quando um novo campo da planilha precisar aparecer na API:

1. validar se o ETL ja produz a coluna em `shared/visao_cliente_schema.py`
2. garantir que a migration do ETL foi aplicada no banco correto
3. confirmar se a coluna existe fisicamente em `final_visao_cliente`
4. mapear a coluna no model SQLAlchemy da `integration-api`
5. expor a coluna no schema Pydantic correspondente
6. publicar e validar o endpoint real na VPS

## 14. Troubleshooting

### 14.1 `health` retorna `degraded`

Verifique:

- conectividade com PostgreSQL
- conectividade com Redis
- variaveis `DATABASE_URL` e `REDIS_URL`

### 14.2 `401` em endpoints protegidos

Verifique:

- token expirado
- token refresh revogado
- role sem permissao
- `Authorization: Bearer <token>`

### 14.3 `/clientes/completo` sem retorno para documento esperado

Verifique:

- se o documento existe na `final_visao_cliente`
- se o ETL processou a data base correta
- se o documento consultado esta limpo de mascara

### 14.4 Campos esperados vindo `null`

Verifique:

- se o campo existe no banco
- se a coluna esta mapeada no model/schema da API
- se o ETL populou a coluna para aquela linha

### 14.5 Campos com `"nan"`

Isso normalmente nao e erro da API. O valor ja esta persistido assim no banco.

## 15. Checklist de release

Antes de publicar:

1. validar sintaxe dos arquivos alterados
2. revisar `git status`
3. publicar no branch alvo e fazer `git pull --ff-only`
4. rebuildar com `docker compose -f docker-compose.vps.yml up -d --build`
5. validar `GET /api/v1/health`
6. validar `POST /api/v1/auth/login`
7. validar pelo menos um `GET /api/v1/clientes/completo?documento=<cnpj>`
8. verificar logs do container

## 16. Melhorias futuras recomendadas

- unificar estrategia de migrations entre ETL e Integration API
- normalizar valores `"nan"` para `null`
- padronizar paginacao entre endpoints (`page/page_size` vs `limit/offset`)
- decidir contrato final para `data_source`
- enriquecer `descricao_situacao` e `cnae_descricao` no payload de empresas/clientes
