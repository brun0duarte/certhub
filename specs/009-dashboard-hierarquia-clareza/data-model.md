# Data Model: Hierarquia e Clareza do Dashboard

Nenhuma migração de schema — as entidades abaixo já existem em `app/db.py` (`certificates`, `reqs`, `activity_log`); esta feature só amplia o que é *lido* (`next_expiring`) e como é *apresentado* no frontend.

## Card de KPI (stat-card)

Puramente de apresentação (não persiste) — derivado de `d.expiring`/`d.totals` no payload de `GET /dashboard`.

| Campo | Origem | Observações |
|---|---|---|
| `valor` | `exp.vencidos`, `exp["ate_"+a]`, `d.totals.reqs_abertas`, `d.totals.certificados` | inalterado |
| `rótulo` | texto fixo por card | inalterado |
| `severidade` | **novo cálculo** — antes por índice, agora por valor do threshold `a` | `a<=30`→crítico, `a<=60`→atenção, `a>60`→ok; "Vencidos" sempre crítico+destaque extra |
| `cumulativo` | **novo, derivado** — `true` para todo card de threshold que não é o primeiro da lista `alert_days` | controla a exibição do `stat-hint` |

## Linha de vencimento (next_expiring)

Estende o `SELECT` já existente em `app/routers/dashboard.py` (`next_expiring`).

| Campo | Novo? | Origem |
|---|---|---|
| `id`, `cn`, `not_after`, `days_left`, `req_number`, `env` | não | já selecionados hoje |
| `ownership` | **sim** | `certificates.ownership` |
| `external_partner` | **sim** | `certificates.external_partner` |
| `partner_email` | **sim** | `certificates.partner_email` |
| `has_active_demand` | **sim** | `CASE WHEN active_req.id IS NOT NULL THEN 1 ELSE 0 END`, mesmo `LEFT JOIN` de `app/routers/monitor.py:47-51` |

Usado tanto pra montar o grupo por data (US5) quanto pra decidir se a linha oferece a ação "Renovar" (US6, `has_active_demand=0`).

## Grupo de vencimento (apresentação, client-side)

Não persiste — resultado de agrupar `next_expiring` por `not_after` no render.

| Campo | Cálculo |
|---|---|
| `data` | `not_after` compartilhado |
| `itens` | lista de linhas de vencimento daquela data |
| `contagem` | `itens.length` |
| `expandido` | estado local de UI (toggle), não persiste |

## Evento de atividade (agrupado, apresentação)

Deriva de `d.activity` (já retornado por `GET /dashboard`, `LIMIT 10`) sem mudança de backend.

| Campo | Origem | Observações |
|---|---|---|
| `action`, `req_number`, `detail`, `created_at`, `user_name` | `activity_log` (já existente) | inalterados |
| `repeticoes` | **novo, derivado** — contagem de eventos consecutivos com mesma `action`+`req_number` | só afeta apresentação, não é persistido |

## Badge de status de lifecycle

| Campo | Mudança |
|---|---|
| `status` (chave: `pedido`/`instalado`/`em_inventario`/`reservado`/`excluir`/`fim_de_vida`) | inalterada — nenhuma chave de dado muda |
| `rótulo` exibido | `excluir` → **"Baixado do inventário"** (era "Excluir"); demais inalterados |
| par cor/fundo | migra de hex fixo por status pra tokens de tema (`var(--cor)`/`var(--cor-soft)`) — mesmo valor semântico, contraste corrigido |

## Regras de validação (derivadas dos Functional Requirements do spec)

- A severidade de um card de KPI é sempre determinada pelo valor do seu threshold, nunca pela posição no array `alert_days` (FR-001).
- Uma linha de `next_expiring` só oferece a ação de renovação quando `has_active_demand = 0` (FR-011).
- Todo par cor/fundo de badge de lifecycle atinge contraste ≥ 4.5:1 nos dois temas (FR-004) — validação por cálculo, não por dado em runtime.
