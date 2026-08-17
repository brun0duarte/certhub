# Implementation Plan: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

**Branch**: `002-busca-filtro-hsm-perfis` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-busca-filtro-hsm-perfis/spec.md`

## Summary

Quatro melhorias incrementais na UI/UX já existente, sem novas dependências: (1) trocar os `<select>` estáticos de demanda por um componente de busca reutilizável nos 5 pontos onde uma operação vincula uma REQ; (2) estender `GET /reqs` com `sort`/`dir` (mesmo padrão já usado em `GET /monitor/expiring`) para dar paridade de ordenação às abas Geração e Instalação; (3) corrigir o painel "Buscar no HSM" para usar as classes `.form-row`/`.field` já padrão no resto da aba, em vez do `style` inline que causa o desalinhamento; (4) substituir a configuração única `hsm_dinamo_config` por `hsm_dinamo_profiles` (lista nomeada + perfil ativo), com migração automática do perfil único existente e um endpoint dedicado de troca rápida.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) + JavaScript vanilla (frontend estático já existente em `app/static/app.js`) — nenhuma linguagem nova

**Primary Dependencies**: Nenhuma dependência nova. Reaproveita FastAPI, pydantic, SQLite (`app/db.py`) já usados no projeto.

**Storage**: SQLite existente (`app/db.py`, tabela `settings` key/value) — sem migração de schema SQL; `hsm_dinamo_profiles` é um novo valor JSON na mesma tabela `settings` (mesmo padrão de `hsmutil_templates`)

**Testing**: pytest (padrão já usado em `tests/`) — estende `tests/test_hsm_routes.py` (perfis, migração) e adiciona cobertura para `sort`/`dir` em `GET /reqs`

**Target Platform**: Linux server (mesmo ambiente de deploy atual da aplicação)

**Project Type**: Web application — projeto único (`app/` como backend FastAPI + frontend estático em `app/static/`), sem split frontend/backend em diretórios separados

**Performance Goals**: filtro do seletor de demanda responde à digitação sem atraso perceptível (client-side, sem round-trip — SC-001: localizar REQ em <10s); troca de perfil de HSM ativo em <5s (SC-005, é uma escrita simples em `settings`, sem chamada ao HSM)

**Constraints**: `ORDER BY` de `GET /reqs` MUST vir de uma tabela de colunas permitidas (nunca interpolar `sort` do cliente direto em SQL); senha de perfil de HSM segue o mesmo tratamento de armazenamento já usado hoje em `hsm_dinamo_config` (sem novo requisito de criptografia); migração de `hsm_dinamo_config` → `hsm_dinamo_profiles` MUST ser transparente (instalações existentes continuam operando sem recadastro, FR-013)

**Scale/Scope**: mesma escala já observada no projeto — dezenas a centenas de REQs abertas por instalação (SC-001 assume centenas); tipicamente 2 perfis de HSM (PRD/NPRD), estrutura suporta mais sem mudança (Assumption em `spec.md`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` contém apenas os placeholders do template — nenhum princípio ratificado para este projeto. Não há gates formais a aplicar; nenhuma violação a justificar. O design segue os padrões implícitos já observáveis no código (settings key/value JSON para configuração, `SORT_COLUMNS` como allowlist de ordenação já usado em `monitor.py`, componentes de UI reutilizáveis em `app.js`), por consistência com o restante do sistema.

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. `data-model.md` e `contracts/` não introduzem tabela SQL nova, dependência nova, nem padrão divergente do já existente no projeto — nada a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-busca-filtro-hsm-perfis/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
├── contracts/            # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
app/
├── routers/
│   ├── reqs.py                    # list_reqs(): NOVO — params sort/dir + SORT_COLUMNS (allowlist)
│   ├── hsm.py                     # _provider(): passa a ler perfil ativo de hsm_dinamo_profiles;
│   │                               #   NOVO: GET /hsm/profiles, PUT /hsm/active-profile
│   └── settings.py                # validação adicional da chave hsm_dinamo_profiles em PUT /settings
├── db.py                          # DEFAULT_SETTINGS: novo hsm_dinamo_profiles; migração automática
│                                   #   de hsm_dinamo_config (perfil único legado) na primeira leitura
└── static/
    ├── app.js                     # NOVO helper reqPicker() (contracts/req-picker-component.md),
    │                               #   usado nos 5 pontos de seleção de REQ; views.geracao/instalacao
    │                               #   ganham cabeçalho de coluna ordenável; views.hsm corrige o
    │                               #   painel de busca (.form-row/.field) e ganha seletor de perfil ativo
    └── styles.css                 # sem classe nova necessária — reaproveita .form-row/.field existentes

tests/
├── test_hsm_routes.py             # estende: GET /hsm/profiles, PUT /hsm/active-profile, migração
└── test_reqs_lifecycle.py         # estende: GET /reqs com sort/dir (válido, inválido, default)
```

**Structure Decision**: Projeto único (mesma estrutura já usada em `001-integracao-hsm-dinamo`) — reaproveita `app/routers/`, `app/db.py` e `app/static/`, sem diretórios novos. Todas as mudanças são extensões de arquivos já existentes; nenhum router, service ou módulo novo é criado.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
