# Guia de Integracao da Integration API

## 1. Objetivo

Este documento orienta times de frontend, CRM e integradores externos sobre como consumir a `integration-api`.
O foco aqui e contrato HTTP, autenticacao, filtros, exemplos e cuidados de consumo.

## 2. Visao geral

### 2.1 Base path

Todos os endpoints de negocio usam o prefixo:

```text
/api/v1
```

### 2.2 Principais casos de uso

- autenticar usuario e obter JWT
- listar clientes com filtros operacionais
- consultar payload detalhado por documento
- obter KPIs da carteira
- consultar dados RF de empresas
- registrar eventos CRM

### 2.3 Endpoint principal para consulta operacional

Para telas e integracoes que precisam do payload completo do cliente, o endpoint principal e:

```text
GET /api/v1/clientes/completo
```

Ele permite:

- buscar por `documento`, `cnpj`, `nome` ou `q`
- filtrar por criterios de negocio
- receber, no mesmo item, os dados operacionais da `final_visao_cliente`, aliases RF e campos computados

## 3. Autenticacao

### 3.1 Login

Endpoint:

```http
POST /api/v1/auth/login
Content-Type: application/json
```

Body:

```json
{
  "email": "adm@teste.com",
  "password": "123456"
}
```

Resposta:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<refresh>",
  "token_type": "Bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "adm@teste.com",
    "full_name": "Administrador",
    "role": "admin"
  }
}
```

### 3.2 Header esperado

Nos endpoints protegidos:

```http
Authorization: Bearer <access_token>
```

### 3.3 Refresh

```http
POST /api/v1/auth/refresh
```

Body:

```json
{
  "refresh_token": "<refresh_token>"
}
```

### 3.4 Usuario autenticado

```http
GET /api/v1/auth/me
```

Resposta:

```json
{
  "id": "uuid",
  "email": "adm@teste.com",
  "full_name": "Administrador",
  "role": "admin",
  "permissions": [
    "clientes:read",
    "empresas:read",
    "crm:inbound",
    "crm:outbound",
    "audit:read",
    "users:manage"
  ],
  "last_login_at": "2026-03-13T19:26:14.541364Z"
}
```

## 4. Perfis e permissoes

### 4.1 `admin`

- clientes
- empresas
- CRM inbound
- CRM outbound
- auditoria
- gestao de usuarios

### 4.2 `gestor`

- clientes
- empresas
- CRM outbound
- auditoria

### 4.3 `operador`

- clientes
- empresas
- CRM inbound

## 5. Headers de rastreio

Voce pode enviar opcionalmente:

```http
X-Trace-Id: abc12345
X-Correlation-Id: req-frontend-001
```

A API devolve esses headers na resposta.

## 6. Formato de erro

Erros de aplicacao seguem este envelope:

```json
{
  "success": false,
  "error": {
    "code": "AUTH_INVALID_TOKEN",
    "message": "Token invalido ou expirado.",
    "details": null,
    "trace_id": "763123db"
  }
}
```

## 7. Health

```http
GET /api/v1/health
```

Resposta:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "production",
  "database": "ok",
  "redis": "ok"
}
```

## 8. Endpoints de clientes

### 8.1 Quando usar cada endpoint

Use `GET /clientes` quando:

- precisar de listagem mais leve
- tela de grid simples
- filtros operacionais sem precisar de payload completo

Use `GET /clientes/completo` quando:

- precisar do payload completo da pessoa ou empresa
- precisar filtrar e ja receber todos os campos operacionais
- quiser espelhar a estrutura consolidada para frontend, BI leve ou integracao

Use `GET /clientes/{cd_cpf_cnpj}` quando:

- ja tiver o documento exato
- quiser detalhe completo de um unico registro

### 8.2 `GET /api/v1/clientes`

Paginacao:

- `page`
- `page_size`

Filtros suportados:

- `q`
- `cnpj`
- `nome`
- `safra_maquina`
- `nunca_qualificou`
- `comissao_prox_mes`
- `apuracao_comiss`
- `criterios_atingidos_comiss`
- `chaves_pix_forte`
- `cancelamento_maq`
- `m2_dias_faltantes`
- `fl_bolcob_cadastrado`
- `criterio_proximo`

### 8.3 `GET /api/v1/clientes/completo`

Este e o endpoint principal para integracao rica.

Paginacao:

- `limit`
- `offset`

Filtros suportados:

- `q`
- `documento`
- `cnpj`
- `nome`
- `safra`
- `safra_maquina`
- `nunca_qualificou`
- `comissao_prox_mes`
- `comissao_este_mes`
- `apuracao_comiss`
- `criterios_atingidos_comissao`
- `criterios_atingidos_comiss`
- `pix_forte`
- `chaves_pix_forte`
- `cancelamento_maquina`
- `cancelamento_maq`
- `m2_faltantes`
- `m2_dias_faltantes`
- `boletos`
- `fl_bolcob_cadastrado`
- `marco`
- `criterio_proximo`

#### Mapa de filtros de negocio

Se o usuario falar no front ou no negocio:

- `cnpj`: use `documento` ou `cnpj`
- `safra`: use `safra` ou `safra_maquina`
- `nome`: use `nome`
- `nunca qualificou`: use `nunca_qualificou`
- `comissao proximo mes`: use `comissao_prox_mes`
- `comissao para este mes`: use `comissao_este_mes` ou `apuracao_comiss`
- `criterios atingidos comissao`: use `criterios_atingidos_comissao` ou `criterios_atingidos_comiss`
- `chave pix forte`: use `pix_forte` ou `chaves_pix_forte`
- `cancelamento maquina`: use `cancelamento_maquina` ou `cancelamento_maq`
- `m2 faltantes`: use `m2_faltantes` ou `m2_dias_faltantes`
- `boletos`: use `boletos` ou `fl_bolcob_cadastrado`
- `marco`: use `marco` ou `criterio_proximo`

#### Exemplo por documento

```http
GET /api/v1/clientes/completo?documento=26018023000117&limit=1&offset=0
Authorization: Bearer <token>
```

#### Exemplo por filtros de negocio

```http
GET /api/v1/clientes/completo?safra=2025-02&nunca_qualificou=true&comissao_prox_mes=SIM&pix_forte=SIM&marco=CASH_IN&limit=20&offset=0
Authorization: Bearer <token>
```

#### Estrutura da resposta

```json
{
  "documento_consultado": "26018023000117",
  "total": 1,
  "limit": 1,
  "offset": 0,
  "items": [
    {
      "cd_cpf_cnpj_cliente": "26018023000117",
      "nome_cliente": "JESSE JAMES MONIZ FRANCO",
      "tipo_pessoa": "PJ",
      "data_base": "2026-03-04 00:00:00",
      "cidade": "MANAUS",
      "status_cc": "LIBERADA",
      "criterio_proximo": "CASH_IN",
      "metrica_ativacao": 0.15,
      "metrica_intencao": 0.1,
      "score_perfil": 0.25
    }
  ]
}
```

### 8.4 Campos devolvidos por `clientes/completo`

O item devolve todos os campos operacionais da `final_visao_cliente`, mais aliases e alguns campos computados.

#### Identificacao e relacionamento

- `data_base`
- `cd_cpf_cnpj_cliente`
- `nome_cliente`
- `tipo_pessoa`
- `cd_cpf_cnpj_parceiro`
- `nome_parceiro`
- `cd_cpf_cnpj_consultor`
- `nome_consultor`
- `uf`
- `cidade`
- `bairro`
- `telefone`
- `telefone_master`
- `email`
- `dt_fundacao_empresa`
- `ramo_atuacao`

#### Conta e cartao

- `num_conta`
- `limite_conta`
- `dt_conta_criada`
- `dt_encer_cc`
- `status_cc`
- `conta_ativa_90d`
- `chaves_pix_forte`
- `dt_conta_criada_global`
- `vl_cash_in_conta_global_mtd`
- `nivel_conta`
- `limite_cartao`
- `limite_alocado_cartao_cdb`
- `dt_entrega_cartao`
- `dt_ativ_cartao_cred`
- `vl_spending_total_mtd`
- `status_pagamento_fatura`
- `nivel_cartao`

#### C6Pay e maquininha

- `fl_propensao_c6pay`
- `tpv_c6pay_potencial`
- `fl_elegivel_venda_c6pay`
- `status_proposta_sf_pay`
- `dt_aprovacao_pay`
- `dt_install_maq`
- `dt_ativacao_pay`
- `c6pay_ativa_30`
- `dt_cancelamento_maq`
- `dt_ult_trans_pay`
- `recebimento`
- `banco_domicilio`
- `tpv_m2`
- `tpv_m1`
- `tpv_m0`
- `faixa_tpv_prometido`
- `cancelamento_maq`
- `elegivel_c6`
- `safra_maquina`
- `idade_safra_maquina`

#### Metricas de perfil

- `metrica_ativacao`
- `metrica_progresso`
- `metrica_urgencia`
- `metrica_financeiro`
- `metrica_intencao`
- `score_perfil`

#### Boleto e cobranca

- `fl_propensao_bolcob`
- `tpv_bolcob_potencial`
- `fl_bolcob_cadastrado`
- `dt_prim_liq_bolcob`
- `dt_ult_emissao_bolcob`
- `qtd_bolcob_emtd_mtd`
- `vl_bolcob_emtd_mtd`
- `qtd_bolcob_liq_mtd`
- `vl_bolcob_liq_mtd`
- `volume_antecipado`
- `agenda_disponivel`
- `taxa_antecipacao`
- `safra_boleto`
- `idade_safra_boleto`

#### Cash in, comissao e qualificacao

- `vl_cash_in_mtd`
- `fl_cash_in_puro`
- `fl_cash_in_boleto`
- `fl_cash_in_setup`
- `fl_cash_in_setup_pix_cnpj`
- `fl_cash_in_setup_cdb_cartao`
- `fl_cash_in_setup_pagamentos`
- `fl_cash_in_setup_deb_auto`
- `vl_saldo_medio_mensalizado`
- `mes_ref_comiss`
- `fl_qualificado_comiss`
- `faixa_cash_in`
- `faixa_domicilio`
- `faixa_saldo_medio`
- `faixa_spending`
- `faixa_cash_in_global`
- `criterios_atingidos_comiss`
- `apuracao_comiss`
- `multiplicador`
- `ja_pago_comiss`
- `previsao_comiss`
- `faixa_max`
- `faixa_alvo`
- `threshiold_cash_in`
- `threshold_spending`
- `threshold_saldo_medio`
- `threshold_conta_global`
- `threshold_domicilio`
- `gap_cash_in`
- `gap_spending`
- `gap_saldo_medio`
- `gap_conta_global`
- `gap_domicilio`
- `pct_cash_in`
- `pct_spending`
- `pct_saldo_medio`
- `pct_conta_global`
- `maior_progresso_pct`
- `criterio_proximo`
- `ja_recebeu_comissao`
- `comissao_prox_mes`
- `status_qualificacao`
- `dias_desde_abertura`
- `m2_dias_faltantes`

#### Receita Federal e aliases

- `rf_razao_social`
- `rf_natureza_juridica`
- `rf_capital_social`
- `rf_porte_empresa`
- `rf_nome_fantasia`
- `rf_situacao_cadastral`
- `rf_data_inicio_ativ`
- `rf_cnae_principal`
- `rf_uf`
- `rf_municipio`
- `rf_email`
- `nome_fantasia`
- `situacao_cadastral`
- `descricao_situacao`
- `cnae_fiscal`
- `cnae_descricao`
- `natureza_juridica`
- `capital_social`
- `porte`
- `data_inicio_ativ`
- `data_source`
- `nunca_qualificou`

### 8.5 `GET /api/v1/clientes/{cd_cpf_cnpj}`

Retorna `ClienteDetailResponse`, sem envelope de lista.
Use quando o cliente ja foi identificado pelo documento exato.

### 8.6 `GET /api/v1/clientes/indicadores`

Parametros:

- `as_of` em `YYYY-MM-DD`

Resposta:

```json
{
  "contas_abertas": 120,
  "instalacao_c6pay": 35,
  "qualificacao_c6pay": 18,
  "contas_qualificadas": 42,
  "as_of": "2026-03-13"
}
```

## 9. Endpoints de empresas

### 9.1 `GET /api/v1/empresas`

Busca empresas com dados RF paginados.

### 9.2 `GET /api/v1/empresas/{cd_cpf_cnpj}`

Retorna os campos RF de um documento especifico.

## 10. Endpoints de usuarios

Uso principal administrativo.

### 10.1 Criar usuario

```http
POST /api/v1/users
```

Body:

```json
{
  "email": "novo.usuario@empresa.com",
  "full_name": "Novo Usuario",
  "role": "operador"
}
```

### 10.2 Listar usuarios

```http
GET /api/v1/users?page=1&page_size=20&is_active=true
```

## 11. Endpoints de auditoria

```http
GET /api/v1/audit?page=1&page_size=50&action=cliente_read
```

Filtros:

- `page`
- `page_size`
- `user_id`
- `action`
- `resource`
- `date_from`
- `date_to`

## 12. Endpoints CRM

### 12.1 Inbound single

```http
POST /api/v1/crm/inbound/events
```

Body:

```json
{
  "cd_cpf_cnpj_cliente": "26018023000117",
  "event_type": "contato_realizado",
  "event_at": "2026-03-13T12:00:00Z",
  "crm_record_id": "crm-123",
  "payload": {
    "observacao": "Ligacao concluida"
  }
}
```

### 12.2 Inbound batch

```http
POST /api/v1/crm/inbound/events/batch
```

Limite:

- maximo de 500 eventos por chamada

### 12.3 Outbound export

```http
POST /api/v1/crm/outbound/export
```

Body:

```json
{
  "cd_cpf_cnpj_clientes": [
    "26018023000117"
  ],
  "segmento": "relacionamento",
  "uf": "AM",
  "data_base_inicio": "2026-03-01",
  "data_base_fim": "2026-03-31"
}
```

### 12.4 Status do job

```http
GET /api/v1/crm/outbound/export/{job_id}
```

## 13. Convencoes importantes para integradores

### 13.1 Datas e numeros

Muitos campos retornam como string, inclusive quando representam:

- datas
- valores monetarios
- percentuais
- contadores

Se o consumidor precisar comparar ou ordenar esses campos, deve parsear explicitamente.

### 13.2 Valores faltantes

Valores ausentes podem vir como:

- `null`
- `"nan"`

Se o frontend tiver formatacao amigavel, trate ambos como dado ausente quando fizer sentido.

### 13.3 Paginacao

Nem todos os endpoints seguem a mesma convencao.

Use:

- `page` e `page_size` em listas administrativas e grids simples
- `limit` e `offset` em `GET /clientes/completo`

### 13.4 Campo `data_source`

Atualmente, em respostas da `integration-api` vindas do banco local, o valor esperado e:

```text
final_visao_cliente
```

### 13.5 Campo `nunca_qualificou`

Este campo e computado pela API a partir de:

- `ja_recebeu_comissao`
- `fl_qualificado_comiss`

Nao precisa existir fisicamente no banco.

## 14. Recomendacao de implementacao no frontend

### 14.1 Busca e detalhe

Fluxo recomendado:

1. use `GET /clientes` para grids leves e filtros simples
2. use `GET /clientes/completo` quando precisar do payload completo
3. use `GET /clientes/{cd_cpf_cnpj}` quando o documento ja estiver definido

### 14.2 Tratamento visual de campos

Recomendacoes:

- trate `null` e `"nan"` como ausencia de informacao quando fizer sentido
- nao assuma que datas viram sempre em ISO puro; alguns campos estao em formato legado string
- preserve o valor bruto em logs tecnicos quando houver divergencia de exibicao

### 14.3 Ordenacao e filtros locais

Se o frontend precisar ordenar:

- parseie datas antes de ordenar
- parseie numericos string antes de ordenar
- mantenha os campos `metrica_*` e `score_perfil` como numero

## 15. Fluxos recomendados

### 15.1 Frontend de carteira

1. fazer login
2. chamar `GET /auth/me`
3. montar filtros e grid com `GET /clientes`
4. quando precisar de payload completo ou busca detalhada, usar `GET /clientes/completo`
5. usar `GET /clientes/indicadores` para cards e KPIs

### 15.2 CRM

1. autenticar integracao com usuario de perfil adequado
2. registrar eventos via `crm/inbound`
3. consultar clientes elegiveis via `clientes` ou `clientes/completo`
4. disparar exportacao via `crm/outbound/export`

## 16. Checklist do integrador

Antes de homologar:

1. validar login e refresh
2. validar expiracao de token
3. validar `clientes/completo` por documento existente
4. validar filtros de negocio criticos
5. validar tratamento de `null` e `"nan"`
6. validar parse de datas e campos numericos string
7. logar `X-Trace-Id` para suporte
