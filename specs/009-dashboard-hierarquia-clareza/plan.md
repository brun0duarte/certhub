# Implementation Plan: Hierarquia e Clareza do Dashboard

**Branch**: `009-dashboard-hierarquia-clareza` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-dashboard-hierarquia-clareza/spec.md`

## Summary

Corrigir 8 pontos de clareza/severidade/acessibilidade do Dashboard (`app/static/app.js` `views.dashboard`): mapear a cor dos cards de KPI pelo valor real do threshold (não pela posição no array) e sinalizar quais números são cumulativos; agrupar a tabela "Próximos vencimentos" por data; adicionar legenda/tooltip nas siglas de ambiente; comprimir e agrupar eventos repetidos na "Atividade Recente"; corrigir contraste WCAG AA dos badges de lifecycle e renomear o status "Excluir"; adicionar linha de média e destaque do mês atual no gráfico de demandas por mês; preencher o buraco da grade de análise trocando `grid-2` por `grid-3` (classe já existente); e adicionar ação rápida de renovação por linha, reaproveitando o padrão já usado em `views.monitor`. Abordagem: mudanças pontuais em `app/static/app.js`/`styles.css` + uma extensão aditiva de `app/routers/dashboard.py` (query `next_expiring`) — sem dependência nova, sem migração de schema.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI), JavaScript ES6+ vanilla (frontend, sem framework/bundler)

**Primary Dependencies**: FastAPI (rotas), sqlite3 stdlib (via `app/db.py`) — nenhuma dependência nova

**Storage**: SQLite (`app/db.py`) — tabelas `certificates`, `reqs`, `activity_log` já existentes; nenhuma coluna/tabela nova

**Testing**: pytest (backend, `tests/`); verificação manual em navegador pro frontend (sem framework de teste JS no projeto)

**Target Platform**: servidor Linux self-hosted (uvicorn) + navegador desktop

**Project Type**: web-service monolítico — mesmo serviço FastAPI que serve `/dashboard` (JSON) e os estáticos da SPA (`app/static/app.js` consome via `api("/dashboard")`)

**Performance Goals**: a extensão da query `next_expiring` (mais 3 colunas + 1 LEFT JOIN, mesmo padrão já usado em `app/routers/monitor.py`) não deve alterar perceptivelmente o tempo de resposta de `/dashboard` (já limitado a `LIMIT 10`)

**Constraints**: reaproveitar tokens de cor já definidos em `styles.css` (`--red/--amber/--green/--accent` e variantes `-soft`) em vez de introduzir paleta nova; reaproveitar o fluxo `newDemandModal('renovacao', ...)` já existente (usado em `views.monitor`) em vez de criar um fluxo de renovação paralelo

**Scale/Scope**: uso interno, `next_expiring`/`activity` já limitados a 10 itens cada — sem preocupação de escala

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` está no estado template (placeholders não preenchidos, nenhum princípio ratificado) — não há gates a avaliar. PASS por ausência de constituição ativa.

## Project Structure

### Documentation (this feature)

```text
specs/009-dashboard-hierarquia-clareza/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── routers/
│   └── dashboard.py           # next_expiring: + ownership/external_partner/partner_email/has_active_demand
└── static/
    ├── app.js                  # views.dashboard, chartVBars, LIFECYCLE_STATUS, ENVS/envBadge
    └── styles.css               # .stat-card (severidade), .badge-lc-*, .grid-2→.grid-3, .chart-vbars overlay

tests/
└── test_dashboard.py          # (novo ou existente) cobre next_expiring estendido
```

**Structure Decision**: Projeto único (monolito web já existente), mesma decisão estrutural da spec irmã `010-menu-lateral-reorganizacao` — sem novos diretórios de topo, tudo dentro de `app/static/` + extensão pontual de `app/routers/dashboard.py`.

## Complexity Tracking

*Sem violações de constituição a justificar — seção não aplicável (constituição não ratificada, ver Constitution Check acima).*
