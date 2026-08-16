# Implementation Plan: Integração com HSM via API (Dinamo Networks)

**Branch**: `001-integracao-hsm-dinamo` | **Date**: 2026-08-14 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-integracao-hsm-dinamo/spec.md`

## Summary

Adicionar um provider real de HSM (Dinamo Networks) ao sistema de certificados, cobrindo criação de chave, geração de CSR, importação de certificado, exportação PFX/P12 e busca de objetos na partição do HSM. A Dinamo não expõe uma API REST pública — o SDK oficial é nativo (JS/Java/.NET/C++) — então a integração usa um bridge Node.js (`@dinamonetworks/hsm-dinamo`) chamado via subprocess pelo backend Python/FastAPI, seguindo o padrão de provider (`KeyProvider`) já existente no projeto (`app/services/hsm/`).

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) + Node.js ≥18 (bridge dedicado ao SDK JS da Dinamo, sem outro uso no projeto)

**Primary Dependencies**: FastAPI, pydantic, `cryptography` (já usados no projeto); `@dinamonetworks/hsm-dinamo` (novo, npm, usado apenas pelo script bridge em Node)

**Storage**: SQLite existente (`app/db.py`) — reaproveita tabelas `certificates` (campo `source`, novo campo `hsm_label`) e `activity_log` (auditoria); o HSM em si é a fonte da verdade para chaves/certificados armazenados nele, não há espelhamento completo em banco local

**Testing**: pytest (padrão já usado em `tests/`); testes do provider Dinamo usam um bridge Node fake/mockado (sem exigir HSM real disponível em CI)

**Target Platform**: Linux server (mesmo ambiente de deploy atual da aplicação)

**Project Type**: Web application — projeto único (`app/` como backend FastAPI + frontend estático em `app/static/`), sem split frontend/backend em diretórios separados

**Performance Goals**: criação de chave confirmada em até 10s (SC-001); CSR completa em até 2min (SC-002); export PFX/P12 em até 1min (SC-004); busca com resposta em até 3s para até 10 mil objetos na partição (SC-005)

**Constraints**: chave privada nunca deixa o HSM fora do fluxo explícito de exportação; credenciais do HSM (usuário/senha de partição) e senha de PFX/P12 nunca aparecem em argv de processo nem em log — trafegam via stdin JSON para o bridge Node e reaproveitam o módulo de senhas já existente; toda operação é auditada via `log_activity` (mesmo padrão já usado por CSR/certificados)

**Scale/Scope**: uso interno por administradores de certificados de uma organização; uma única partição HSM configurada por ambiente (PRD/HMP/TQS/DES), inventário de até ~10 mil objetos por partição

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`. specify/memory/constitution.md` ainda contém apenas os placeholders do template (nenhum princípio foi ratificado para este projeto). Não há gates formais a aplicar — nenhuma violação a justificar. A integração segue os padrões implícitos já observáveis no código (provider pattern em `app/services/hsm/`, configuração via tabela `settings`, auditoria via `activity_log`), por consistência com o restante do sistema.

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. Design (data-model.md, contracts/) segue o mesmo provider pattern e mecanismo de configuração já existentes; nenhuma dependência ou estrutura nova introduz violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-integracao-hsm-dinamo/
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
│   └── hsm.py                     # NOVO: endpoints /hsm/keys, /hsm/keys/{label}/csr,
│                                   #   /hsm/keys/{label}/certificate, /hsm/keys/{label}/export, /hsm/search
├── services/
│   └── hsm/
│       ├── base.py                # EXISTENTE: interface KeyProvider — estender com
│       │                          #   import_cert, export_pfx, search_objects
│       ├── local.py               # EXISTENTE: provider em software (sem mudança de contrato)
│       ├── hsmutil.py             # EXISTENTE: provider via CLI hsmutil (sem mudança de contrato)
│       ├── dinamo_js.py           # EXISTENTE (stub) → implementação real: spawna o bridge Node
│       │                          #   e traduz request/response para o contrato KeyProvider
│       └── node/
│           └── hsm-helper.js      # NOVO: script Node usando @dinamonetworks/hsm-dinamo,
│                                   #   protocolo JSON via stdin/stdout (ver contracts/)
├── db.py                          # settings novas (conexão HSM) + coluna certificates.hsm_label
└── static/
    ├── app.js                     # nova aba/seção "HSM" (criar chave, CSR, importar, exportar, buscar)
    ├── index.html
    └── styles.css

tests/
└── test_hsm_dinamo_provider.py    # NOVO: testes do DinamoJsProvider com bridge Node mockado/fake
```

**Structure Decision**: Projeto único (Option 1), reaproveitando a estrutura já existente em `app/` (routers + services + static). Não há separação frontend/backend em diretórios distintos — o frontend é servido como estático a partir do mesmo backend FastAPI, como já ocorre hoje. O bridge Node fica isolado em `app/services/hsm/node/`, tratado como um detalhe de implementação do provider `dinamo_js`, nunca exposto diretamente à UI ou a outros routers.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
