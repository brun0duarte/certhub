# Implementation Plan: Ajustes de Layout do HSM e Preservação de Estado entre Abas

**Branch**: `003-hsm-layout-navegacao` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-hsm-layout-navegacao/spec.md`

## Summary

Três correções independentes de UI/UX, sem novas dependências: (1) o painel "Criar chave" da aba HSM "sobrepõe" o painel seguinte porque a regra CSS `.panel + .panel` não se aplica através do container `.grid.grid-2` — fix é uma regra CSS local pra restaurar o espaçamento; (2) a aba HSM passa a mostrar nome/host/usuário do perfil de HSM ativo no topo, reaproveitando `GET /hsm/profiles` (specs/002) estendido com 2 campos não-sensíveis; (3) um armazenamento de estado em memória por-nome-de-view (`viewState`) preserva campos de formulário não salvos, filtros/busca e paginação ao trocar de aba dentro da mesma sessão (sem sobreviver a F5), aplicado às ~10 views com filtro/formulário relevante.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) + JavaScript vanilla (frontend estático em `app/static/app.js`) — nenhuma linguagem nova

**Primary Dependencies**: Nenhuma dependência nova — reaproveita FastAPI/pydantic (backend) e o JS vanilla já usado em todo `app.js` (frontend), consistente com specs/001 e specs/002.

**Storage**: Sem mudança de armazenamento persistente. `GET /hsm/profiles` (US2) só expõe 2 campos já salvos em `hsm_dinamo_profiles` (setting existente). O estado de view (US3) vive só em memória do processo do navegador (`viewState`, objeto de módulo em `app.js`) — nunca em SQLite, `localStorage`, `sessionStorage` ou cookie.

**Testing**: pytest (padrão já usado em `tests/`) — estende `tests/test_hsm_routes.py` pra cobrir os novos campos de `GET /hsm/profiles`. US1 (CSS) e US3 (estado de frontend) não têm framework de teste automatizado no projeto — validação manual/visual via `quickstart.md`.

**Target Platform**: Linux server (mesmo ambiente de deploy atual) + navegador desktop (mesmo suporte já assumido pelo resto do frontend)

**Project Type**: Web application — projeto único (`app/` backend FastAPI + frontend estático em `app/static/`), mesma estrutura de specs/001 e specs/002

**Performance Goals**: leitura/escrita de `viewState` é acesso direto a objeto JS em memória — sem impacto de performance perceptível; troca de aba continua buscando dados do servidor normalmente (FR-008), sem introduzir cache de dados obsoletos

**Constraints**: `viewState` MUST NUNCA ser serializado pra armazenamento persistente do navegador (FR-007 — inclui campos de senha preenchidos em formulários); campos de arquivo (`<input type="file">`) MUST NOT ser incluídos no estado preservado (limitação de segurança do navegador, não é possível reatribuir `FileList` via JS); resultados de ações já concluídas (ex.: CSR gerada, resultado de busca no HSM) MUST NOT ser preservados, só entradas ainda não enviadas (FR-011); `password` de perfil de HSM MUST continuar nunca presente em nenhuma resposta de API (FR-003)

**Scale/Scope**: ~10 views do frontend passam a usar `getViewState()` (listadas em `data-model.md`); 1 endpoint estendido (`GET /hsm/profiles`); 1 fix de CSS local com efeito colateral positivo em 3 outras telas que usam `.grid.grid-2` (Decoder, Certificados, Validar cadeia)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` contém apenas os placeholders do template — nenhum princípio ratificado, nenhum gate formal a aplicar. O design segue os padrões implícitos já observáveis no código (JS vanilla direto sem framework de estado, settings key/value JSON pra configuração, CSS utilitário compartilhado entre views), por consistência com specs/001 e specs/002.

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. `data-model.md` e `contracts/` não introduzem dependência, tabela SQL ou padrão novo divergente do já existente — nada a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-hsm-layout-navegacao/
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
│   └── hsm.py                     # list_profiles(): NOVO — inclui host/username por perfil
└── static/
    ├── app.js                     # NOVO: viewState{} + getViewState() (escopo de módulo);
    │                               #   views.geracao/instalacao/historico/monitor/auditoria/certs
    │                               #   passam a ler/gravar filtro+página em getViewState();
    │                               #   views.csr/hsm/decoder/settings passam a ler/gravar campos
    │                               #   de formulário em getViewState(); views.hsm ganha texto
    │                               #   "{name} · {host} · {username}" do perfil ativo no topo
    └── styles.css                 # NOVO: regra de espaçamento pra `.grid-2` seguido de `.panel`
                                    #   (fix da sobreposição — sem tabela/classe nova, só a regra)

tests/
└── test_hsm_routes.py             # estende: GET /hsm/profiles retorna host/username, nunca password
```

**Structure Decision**: Projeto único (mesma estrutura de specs/001 e specs/002) — reaproveita `app/routers/hsm.py` e `app/static/`, sem diretórios novos. Nenhum router, service ou módulo novo é criado; a mudança mais estrutural (`viewState`) é uma adição interna ao `app.js` já existente, seguindo o mesmo padrão vanilla JS do resto do arquivo.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
