# Implementation Plan: Reorganização do Menu Lateral

**Branch**: `010-menu-lateral-reorganizacao` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-menu-lateral-reorganizacao/spec.md`

## Summary

Reestruturar o menu lateral do CertHub (18 itens hoje numa lista plana) em 4 categorias funcionais visíveis (Certificados, Ciclo de vida, Segurança, Sistema) com o Dashboard solto no topo; extrair Aparência/Configurações da lista rolável pra um bloco fixo separado; remover o botão de tema duplicado do rodapé (o controle completo já existe em Aparência); corrigir a quebra de linha do rótulo "Manuais & Comandos" (e blindar contra qualquer rótulo futuro); adicionar badges de contagem de pendências em Revogação/Kanban via um novo endpoint leve; e subir o contraste do texto/ícone inativo do menu no modo institucional CAIXA de 4.45:1 pra ~4.78:1 (AA). Abordagem: só CSS/JS/markup no frontend estático existente (`app/static/`) + uma extensão pequena e aditiva do backend FastAPI (`app/routers/dashboard.py`) — nenhuma dependência nova, nenhuma migração de schema.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI), JavaScript ES6+ vanilla (frontend, sem framework/bundler)

**Primary Dependencies**: FastAPI (rotas), sqlite3 stdlib (via `app/db.py`) — nenhuma dependência nova necessária

**Storage**: SQLite (`app/db.py`), tabelas `reqs` (coluna `demand_type`, valores incl. `'revogacao'`) e `tasks` (coluna `lane`, valores incl. `'concluido'`) já existentes

**Testing**: pytest (backend, `tests/`); verificação manual em navegador pro frontend (sem framework de teste JS no projeto)

**Target Platform**: servidor Linux self-hosted (uvicorn) + navegador desktop (Chrome/Edge/Firefox)

**Project Type**: web-service monolítico — backend FastAPI serve API JSON + arquivos estáticos (`app/static/index.html`, `app.js`, `styles.css`, `icons.js`) como SPA sem build step

**Performance Goals**: endpoint novo (`/nav-counts`) deve responder bem abaixo de 100ms — só 2 `COUNT(*)` simples sobre tabelas já indexadas por status/lane

**Constraints**: não introduzir dependência JS/CSS externa nova; preservar o sistema de tema/layout/accent existente (incl. modo institucional CAIXA da spec 006/007) sem quebrar nenhuma combinação já suportada; mudança de estrutura do `#nav` não pode quebrar `applyAccent`/`applyIconSkin`/`NAV_ICONS` (icons.js) que hoje dependem de `#nav a[data-view]`

**Scale/Scope**: uso interno, 18 itens de menu, poucas centenas/milhares de linhas em `reqs`/`tasks` — sem preocupação de escala

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` está no estado template (placeholders não preenchidos, nenhum princípio ratificado neste projeto) — não há gates a avaliar. PASS por ausência de constituição ativa.

## Project Structure

### Documentation (this feature)

```text
specs/010-menu-lateral-reorganizacao/
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
├── main.py                    # registro de routers (sem mudança de estrutura, só se necessário)
├── db.py                      # schema existente (reqs.demand_type, tasks.lane) — só leitura
├── routers/
│   └── dashboard.py           # + GET /nav-counts (novo endpoint aditivo)
└── static/
    ├── index.html             # #nav reestruturado em grupos + .sidebar-secondary novo
    ├── app.js                 # applyAccent/applyTheme/applyLayout ajustados; refreshNavCounts() novo
    ├── styles.css              # .nav-group-label, .sidebar-secondary, .nav-badge, fix .nav-txt, contraste CAIXA
    └── icons.js                # sem mudança de API — só precisa continuar casando com #nav a[data-view]

tests/
└── test_dashboard.py          # (novo ou existente) cobre GET /nav-counts
```

**Structure Decision**: Projeto único (monolito web já existente) — sem novos diretórios de topo. Toda a mudança acontece dentro de `app/static/` (frontend estático servido pelo FastAPI, sem processo de build) e uma extensão pontual de `app/routers/dashboard.py`. Não há frontend separado nem projeto mobile — a opção "web application" com backend/frontend isolados do template não se aplica; o projeto já é um único serviço que serve os dois.

## Complexity Tracking

*Sem violações de constituição a justificar — seção não aplicável (constituição não ratificada, ver Constitution Check acima).*
