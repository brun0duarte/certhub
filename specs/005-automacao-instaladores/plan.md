# Implementation Plan: Automação Real dos Providers de Instalação

**Branch**: `005-automacao-instaladores` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-automacao-instaladores/spec.md`

## Summary

Substitui o stub único `_not_implemented()` (hoje compartilhado pelos 10 tipos de local de instalação) por comportamento real por provider. Os 5 providers de nuvem (Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion, Akamai) ficam totalmente funcionais, usando credenciais de conta/API configuráveis em Configurações (novo setting `installer_credentials`, mesmo padrão de `hsm_dinamo_profiles`). Os 4 providers de acesso remoto a servidor (Apache, Nginx, IIS, Mainframe) e o Balanceador ganham validação real de configuração, mas ficam honestamente bloqueados por uma lacuna concreta descoberta na pesquisa: não existe integração com a API do BeyondTrust pra buscar a credencial real do alvo (`credential_ref` hoje é só uma referência textual), e Balanceador não tem protocolo de automação conhecido documentado em lugar nenhum do sistema — ambos retornam mensagens específicas e honestas em vez do texto genérico atual, em vez de inventar uma integração não pedida.

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) — sem mudança de frontend nesta feature (a UI de "Instalar"/histórico já existe e não muda)

**Primary Dependencies**: **Novas**: `requests` (Azure Key Vault, Azion), `boto3` (AWS Certificate Manager + Secrets Manager), `edgegrid-python` (Akamai). Únicas adições — o projeto tem hoje só 5 dependências (`requirements.txt`), filosofia enxuta já estabelecida (specs/001 usou bridge Node em vez de SDK Python pro HSM); aqui a complexidade de assinatura (SigV4 da AWS, EdgeGrid da Akamai) torna reimplementar à mão mais arriscado que a dependência.

**Storage**: SQLite existente. Um novo setting (`installer_credentials`, JSON) — sem tabela nova, mesmo mecanismo já usado por `hsm_dinamo_profiles`/`hsmutil_templates`.

**Testing**: pytest — novo `tests/test_installer_providers.py`, mockando as chamadas HTTP/boto3 (sem depender de contas reais de nuvem pra rodar a suíte).

**Target Platform**: Linux server (mesmo ambiente de deploy atual)

**Project Type**: Web application — projeto único (`app/`), mesma estrutura de specs/001-004

**Performance Goals**: sem requisito específico — cada tentativa de instalação já é uma ação pontual (clique em "Instalar"), latência de rede do provedor externo é aceitável como já é hoje pro fluxo manual

**Constraints**: nenhuma credencial (conta/API dos 5 providers de nuvem) MUST aparecer em log ou resposta de API (FR-008) — mesmo princípio já aplicado a `hsm_dinamo_profiles`; providers de acesso remoto a servidor (Apache/Nginx/IIS/Mainframe) MUST NOT tentar autenticação sem uma credencial real resolvida — como não há integração com BeyondTrust nesta rodada, esses providers MUST retornar o bloqueio específico em vez de tentar conectar sem segredo válido

**Scale/Scope**: 10 classes de provider (`app/services/installers/providers.py`) tendo o corpo de `install()` reescrito; 1 setting novo; 1 painel novo em Configurações

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` contém só os placeholders do template — nenhum princípio ratificado, nenhum gate formal a aplicar. O design segue os padrões implícitos já observáveis no código (interface `InstallProvider` já existente, settings key/value JSON pra credenciais compartilhadas, princípio já documentado de nunca guardar credencial de acesso ao alvo dentro do CertHub).

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. `data-model.md`/`contracts/` não introduzem tabela SQL nova nem violam o princípio de credencial-de-alvo-fora-do-CertHub já documentado em `app/services/installers/base.py` — as 3 dependências novas (`requests`, `boto3`, `edgegrid-python`) são justificadas em `research.md` #3 (assinatura de request complexa/sensível o suficiente pra não valer reimplementar à mão) e registradas aqui por transparência, não como violação a corrigir.

## Project Structure

### Documentation (this feature)

```text
specs/005-automacao-instaladores/
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
│   └── settings.py                # JSON_KEYS: +'installer_credentials'
├── services/
│   └── installers/
│       └── providers.py           # 10 classes: install() real por tipo (ver contracts/install-provider.md)
├── db.py                          # DEFAULT_SETTINGS: +'installer_credentials'
└── static/
    └── app.js                     # views.settings: nova seção "Credenciais dos instaladores"

requirements.txt                   # +requests, +boto3, +edgegrid-python

tests/
└── test_installer_providers.py    # NOVO: 1+ testes por provider, HTTP/boto3 mockado
```

**Structure Decision**: Projeto único (mesma estrutura de specs/001-004) — reaproveita `app/services/installers/`, `app/routers/settings.py`, `app/db.py`, `app/static/app.js`. Nenhum router novo (a orquestração de instalação já existe em `app/routers/reqs.py`, sem mudança). Nenhuma view nova no frontend além da nova seção de credenciais em Configurações — a UI de "Instalar"/histórico é agnóstica de provider e já funciona.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
