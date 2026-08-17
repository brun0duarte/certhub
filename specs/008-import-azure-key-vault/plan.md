# Implementation Plan: Importação Completa pro Azure Key Vault

**Branch**: `008-import-azure-key-vault` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-import-azure-key-vault/spec.md`

## Summary

`AzureKeyVaultProvider` (`app/services/installers/providers.py:158`) já autentica no Azure AD e importa o PFX no Key Vault, mas (1) manda a requisição sem o bloco `policy` — o Key Vault fica livre pra aplicar uma política de chave/conteúdo divergente da que o usuário já validou manualmente — e (2) descarta o corpo da resposta 200, mostrando só uma frase genérica. Esta feature adiciona o bloco `policy` fixo (RSA 2048, exportável, sem reúso, conteúdo PKCS#12) na requisição e passa a extrair da resposta a validade (`attributes.nbf`/`attributes.exp`), o thumbprint (`x5t`) e o identificador de versão (sufixo de `id`), montando uma mensagem de sucesso detalhada — no mesmo padrão já usado por `AzionProvider.install()` (providers.py:298-308).

## Technical Context

**Language/Version**: Python 3.12 (backend FastAPI existente) — sem mudança de frontend; a mensagem de sucesso já é exibida pelo componente de histórico de instalação existente (`app/static/*`), só o conteúdo do texto muda.

**Primary Dependencies**: Nenhuma nova. `requests` (já usado pra chamar o Key Vault) e `datetime`/`base64` da stdlib pra converter `attributes.nbf`/`exp` (epoch) em data legível e decodificar o `id` — sem precisar de `cryptography.x509` pra ler o `cer`, já que `attributes` traz nbf/exp prontos e `x5t` já vem pronto como thumbprint.

**Storage**: Nenhuma mudança — resultado da instalação continua persistido em `install_runs.output` (texto), mesmo mecanismo já usado por todos os providers.

**Testing**: pytest — estende `tests/test_installer_providers.py` (seção "Azure Key Vault"), ajustando o mock `fake_post` pra retornar um corpo de resposta realista (igual ao payload real testado manualmente) e adicionando asserts sobre o conteúdo da mensagem de sucesso.

**Target Platform**: Linux server (mesmo ambiente de deploy atual)

**Project Type**: Web application — projeto único (`app/`), mesma estrutura de specs/001-007

**Performance Goals**: N/A — mesma chamada de rede pontual já existente (clique em "Instalar"); o processamento adicional da resposta é local e desprezível.

**Constraints**: A política de chave (FR-001) é um valor fixo no código (não configurável por local nesta etapa, conforme Assumptions do spec) — não pode divergir entre instalações. O parsing da resposta (FR-002/FR-003) MUST NOT fazer a instalação falhar quando um campo estiver ausente ou em formato inesperado (FR-004) — a chamada ao Key Vault já retornou sucesso (HTTP 2xx) antes do parsing começar.

**Scale/Scope**: 1 classe (`AzureKeyVaultProvider.install()`) alterada; nenhuma tabela, endpoint ou setting novo.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` contém só os placeholders do template — nenhum princípio ratificado, nenhum gate formal a aplicar. O design segue o padrão implícito já estabelecido em specs/005 (providers de nuvem tentam a operação real e nunca fabricam sucesso; erro real da API é sempre repassado) e reaproveita a interface `InstallProvider` existente sem alterá-la.

**Status**: PASS (sem constituição ratificada, sem violações identificadas)

**Re-check pós Phase 1**: mantido PASS. `data-model.md` não introduz entidade persistida nova (o "Resultado de instalação" já é o mesmo texto livre gravado em `install_runs.output` hoje); `contracts/` documenta apenas o formato da requisição/resposta já trocada com a API pública do Azure — nenhuma superfície nova exposta pelo CertHub.

## Project Structure

### Documentation (this feature)

```text
specs/008-import-azure-key-vault/
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
├── services/
│   └── installers/
│       ├── providers.py     # AzureKeyVaultProvider.install() — alterado (policy na requisição + parsing da resposta)
│       └── base.py           # InstallProvider — sem alteração
└── static/                   # UI que exibe install_runs.output — sem alteração (já renderiza texto livre)

tests/
└── test_installer_providers.py   # seção "Azure Key Vault" — estendida
```

**Structure Decision**: Projeto único já existente (`app/`), mesma estrutura de specs/001-007. Toda a mudança fica dentro de um único método (`AzureKeyVaultProvider.install()`) e seus testes — não há novo módulo, rota ou tabela.

## Complexity Tracking

*Sem violações da Constitution Check — seção não aplicável.*
