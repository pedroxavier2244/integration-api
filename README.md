# Integration API

API FastAPI para autenticacao, consulta operacional de clientes, dados de empresas, auditoria e integracao CRM.

## Documentacao principal

Este repositorio possui dois guias formais, com focos diferentes:

- [Guia de Manutencao](docs/manutencao-api.md)
- [Guia de Integracao](docs/guia-integracao.md)

## Para quem e cada documento

- manutencao: operacao da API, deploy, variaveis de ambiente, troubleshooting e ownership tecnico
- integracao: autenticacao, contratos HTTP, filtros, exemplos de consumo e cuidados para frontend/CRM

## Escopo

Esta API atua sobre o banco compartilhado com o ETL (`etl_db`) e expoe:

- autenticacao com JWT e refresh token persistido
- gestao de usuarios por perfil (`admin`, `gestor`, `operador`) com escopo de equipe por `gestor_id`
- consultas de clientes e empresas
- auditoria operacional
- integracao CRM inbound e outbound

## Principais rotas

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/clientes`
- `GET /api/v1/clientes/completo`
- `GET /api/v1/clientes/historico-alteracoes`
- `GET /api/v1/clientes/{cd_cpf_cnpj}`
- `GET /api/v1/empresas`
- `POST /api/v1/crm/inbound/events`
- `POST /api/v1/crm/outbound/export`

## Observacoes importantes

- A fonte principal dos dados de negocio e a tabela `public.final_visao_cliente`.
- A API trata `final_visao_cliente` como read-only.
- O historico persistido de alteracoes vem de `public.visao_cliente_change_history`, tambem de ownership do ETL.
- Em ambiente de VPS, o deploy de referencia usa `docker compose -f docker-compose.vps.yml up -d --build`.
- A documentacao Swagger fica disponivel em `/docs` quando `DEBUG=true`.
- O endpoint `GET /api/v1/clientes/completo` e o contrato principal para consultas operacionais ricas por documento, nome e filtros de negocio.

## Links rapidos

- [Dockerfile](Dockerfile)
- [Compose VPS](docker-compose.vps.yml)
- [Exemplo de ambiente](.env.example)
- [Indice de documentacao](docs/README.md)
