# Implementation Plan: Demandas de Revogação de Certificados

**Branch**: `004-revogacao-certificados` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-revogacao-certificados/spec.md`

## Summary

Formaliza a revogação de certificados como um tipo de demanda de primeira classe: uma nova aba "Revogação" (mesmo padrão de Geração/Instalação), a ação "Revogar" a partir de um certificado do inventário, um destino/canal obrigatório por demanda (Internacional, Serpro, AC Interna NPRD, AC Interna PRD, Outros), e uma arquitetura de providers por destino — implementados de verdade (função, validação, logging) mas sem nenhuma conexão de rede real nesta fase, sempre retornando "não conectado, confirme manualmente". `demand_type='revogacao'` já existe no sistema hoje (reconhecido em toda a UI genérica), só falta o fluxo dedicado.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) + JavaScript vanilla (frontend estático em `app/static/app.js`) — nenhuma linguagem nova

**Primary Dependencies**: Nenhuma dependência nova — reaproveita FastAPI/pydantic (backend) e o JS vanilla já usado em todo `app.js`, consistente com specs/001-003.

**Storage**: SQLite existente (`app/db.py`). Migração pequena e aditiva: 3 colunas novas em `reqs` (`revoke_destination`, `revoke_destination_other`, `revoke_cert_id`), 1 valor novo (`revogado`) em `LIFECYCLE_STATUSES`. Sem tabela nova — `certificates`/`reqs` já cobrem o necessário.

**Testing**: pytest (padrão já usado em `tests/`) — novo `tests/test_revocation_providers.py`, extensão de `tests/test_reqs_lifecycle.py`.

**Target Platform**: Linux server (mesmo ambiente de deploy atual) + navegador desktop

**Project Type**: Web application — projeto único (`app/` backend FastAPI + frontend estático em `app/static/`), mesma estrutura de specs/001-003

**Performance Goals**: sem requisito de performance específico — mesma escala das demais listagens de demanda (dezenas a centenas de itens, já coberta por specs/002)

**Constraints**: nenhum provider de revogação MUST fazer chamada de rede/subprocess real nesta fase (FR-008) — cada `revoke()` é uma função real, testável, mas sempre retorna "não conectado"; `revoke_destination` obrigatório pra `demand_type='revogacao'` (FR-004); duplicidade de demanda de revogação em aberto pro mesmo certificado é aviso, não bloqueio (FR-010, diferente do bloqueio rígido já existente pra `geracao`/`recebimento`)

**Scale/Scope**: 1 aba nova no frontend, 3 endpoints estendidos/novos (`POST /reqs`, `PUT /reqs/{id}`, `POST /reqs/{id}/revoke`), 1 pacote novo de serviço (`app/services/revocation/`, 4 arquivos/5 classes)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` contém apenas os placeholders do template — nenhum princípio ratificado, nenhum gate formal a aplicar. O design segue os padrões implícitos já observáveis no código (arquitetura de provider por destino mirando `app/services/hsm/`, colunas aditivas em `reqs` mirando extensões já feitas por specs/001-003, guardas de transição de status condicionais por `demand_type` já em uso em `update_req`).

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. `data-model.md` e `contracts/` não introduzem tabela SQL nova, dependência nova, nem padrão divergente do já existente no projeto — nada a registrar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-revogacao-certificados/
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
│   └── reqs.py                    # ReqIn/ReqUpdate: novos campos revoke_*;
│                                   #   POST /reqs: validação + duplicidade não-bloqueante;
│                                   #   PUT /reqs/{id}: mesma validação + atualiza
│                                   #   certificates.lifecycle_status='revogado' ao concluir;
│                                   #   NOVO: POST /reqs/{id}/revoke (aciona provider)
├── services/
│   └── revocation/                # NOVO pacote — mesma forma de app/services/hsm/
│       ├── base.py                # NOVO: RevocationProvider (ABC, 1 método: revoke())
│       ├── internacional.py       # NOVO
│       ├── serpro.py              # NOVO
│       ├── ac_interna.py          # NOVO: AcInternaRevocationProvider(ambiente="nprd"|"prd")
│       └── outros.py              # NOVO
├── db.py                          # LIFECYCLE_STATUSES: +'revogado'; migração: reqs.revoke_destination,
│                                   #   reqs.revoke_destination_other, reqs.revoke_cert_id
└── static/
    ├── app.js                     # NOVO views.revogacao (mesmo padrão de views.instalacao);
    │                               #   newDemandModal(): bloco de destino quando type='revogacao';
    │                               #   certDetail(): botão "🚫 Revogar"; LIFECYCLE_STATUS: +'revogado'
    └── index.html                 # NOVO item de navegação "Revogação"

tests/
├── test_revocation_providers.py   # NOVO: 1 teste por provider (ok=False, code=NOT_CONNECTED)
└── test_reqs_lifecycle.py         # estende: validação de destino, duplicidade, lifecycle_status
```

**Structure Decision**: Projeto único (mesma estrutura de specs/001-003) — reaproveita `app/routers/reqs.py`, `app/db.py` e `app/static/`, mais um pacote de serviço novo (`app/services/revocation/`) espelhando `app/services/hsm/`. Nenhum router novo — a feature inteira vive dentro de `reqs.py` (é um tipo de demanda, não um domínio separado).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
