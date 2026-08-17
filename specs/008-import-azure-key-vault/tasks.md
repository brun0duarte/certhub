---

description: "Task list for feature implementation"
---

# Tasks: Importação Completa pro Azure Key Vault

**Input**: Design documents from `/specs/008-import-azure-key-vault/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas, seguindo o padrão já existente no repositório (specs/005).

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1, US2 (spec.md)

## Path Conventions

Projeto único (`app/` backend FastAPI) — ver `plan.md` → Project Structure. Toda a mudança de implementação fica num único método, `AzureKeyVaultProvider.install()` em `app/services/installers/providers.py`.

## Phase 1: Setup

Vazia — nenhuma dependência nova (`research.md` confirma: `requests` já é usado por este provider, `datetime`/`base64` são da stdlib). Nada a inicializar além do que specs/001-007 já deixaram pronto.

---

## Phase 2: Foundational

Vazia — as duas user stories alteram o mesmo método (`AzureKeyVaultProvider.install()`) em pontos distintos (montagem da requisição vs. processamento da resposta), sem nenhum pré-requisito comum a resolver antes.

**Checkpoint**: Nenhum — pode-se ir direto para as user stories.

---

## Phase 3: User Story 1 - Ver o resultado real da importação no Key Vault (Priority: P1) 🎯 MVP

**Goal**: Quando a importação no Key Vault tem sucesso, a mensagem exibida ao usuário mostra validade, thumbprint e versão do certificado — não mais só uma frase genérica.

**Independent Test**: Acionar "Instalar" num local Azure Key Vault configurado corretamente e confirmar que o resultado exibido no histórico do local inclui validade (início/expiração), thumbprint e identificador de versão.

### Implementation for User Story 1

- [X] T001 [US1] Implementar em `AzureKeyVaultProvider.install()` (`app/services/installers/providers.py`) a extração de `id` (versão, último segmento do path), `x5t` (thumbprint) e `attributes.nbf`/`attributes.exp` (convertidos de epoch pra data legível) da resposta 200 do Key Vault, montando uma mensagem de sucesso detalhada no mesmo padrão de `AzionProvider.install()`; qualquer campo ausente/mal formado (`try/except (ValueError, KeyError, TypeError)`) MUST cair na mensagem genérica já existente sem afetar `result["ok"]`, conforme `research.md` #2/#3 e `contracts/azure_keyvault_import.md`
- [X] T002 [US1] Validar manualmente conforme `quickstart.md` → "Validação manual end-to-end", passos 1-4

**Checkpoint**: Importação bem-sucedida no Key Vault passa a mostrar validade/thumbprint/versão; resposta em formato inesperado continua sendo sucesso, com mensagem genérica.

---

## Phase 4: User Story 2 - Requisição de importação alinhada com a política real do certificado (Priority: P2)

**Goal**: A requisição de importação sempre declara a política do certificado (RSA 2048, exportável, sem reúso de chave, conteúdo PKCS#12), em vez de deixar o Key Vault inferir uma política padrão.

**Independent Test**: Acionar "Instalar" num local Azure Key Vault e inspecionar (log/depuração) que o corpo da requisição enviada contém o bloco `policy` com os valores esperados.

### Implementation for User Story 2

- [X] T003 [US2] Adicionar ao corpo da requisição de importação em `AzureKeyVaultProvider.install()` (`app/services/installers/providers.py`) o bloco `policy` fixo (`key_props`: `exportable=true`, `kty="RSA"`, `key_size=2048`, `reuse_key=false`; `secret_props`: `contentType="application/x-pkcs12"`), conforme `research.md` #1 e `contracts/azure_keyvault_import.md`
- [X] T004 [US2] Validar manualmente conforme `quickstart.md` → "Validação manual end-to-end", confirmando o bloco `policy` no corpo da requisição enviada

**Checkpoint**: Toda importação passa a declarar a política de chave/conteúdo esperada, sem depender do padrão inferido pelo Key Vault.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T005 [P] Estender `tests/test_installer_providers.py` (seção "Azure Key Vault"): `test_azure_success` passa a mockar uma resposta realista (`id`/`x5t`/`attributes.nbf`/`attributes.exp`, conforme `contracts/azure_keyvault_import.md`) e a checar que `result["output"]` contém validade/thumbprint/versão (US1); novo teste cobrindo resposta 200 sem esses campos → `result["ok"] is True` com mensagem genérica (US1, FR-004); novo teste inspecionando o `json=` passado ao `requests.post` de importação pra confirmar o bloco `policy` (US2, FR-001); testes já existentes (`test_azure_missing_credentials`, `test_azure_missing_key_material`, `test_azure_api_error_passed_through`) continuam passando sem alteração
- [X] T006 Rodar a suíte completa `pytest` e corrigir qualquer regressão introduzida em `providers.py` (depende de T005)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: vazia
- **Foundational (Phase 2)**: vazia — nenhum bloqueio compartilhado entre as 2 stories
- **User Stories (Phase 3-4)**: totalmente independentes entre si — cada uma mexe numa parte distinta do mesmo método (`install()`), sem overlap de comportamento (US1 = processar resposta; US2 = montar requisição)
- **Polish (Phase 5)**: depende de US1 e US2 estarem completas (os testes de T005 cobrem as duas)

### Dentro de cada User Story

- US1: T001 (implementação) antes de T002 (validação manual)
- US2: T003 (implementação) antes de T004 (validação manual)

### Parallel Opportunities

- US1 e US2 podem ser feitas em paralelo por pessoas/agentes diferentes, coordenando edições no mesmo método (`AzureKeyVaultProvider.install()`, `app/services/installers/providers.py`) — T001 mexe no processamento da resposta (depois do `requests.post`), T003 mexe na montagem do `json=` (antes do `requests.post`), sem overlap de linhas
- T005 é a única tarefa marcada `[P]` no Polish, por não ter nenhuma outra tarefa em paralelo com ela nesta fase; T006 depende de T005 (precisa dos testes novos escritos antes de rodar a suíte completa)

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 3 (US1) — T001-T002
2. **VALIDAR**: confirmar que a mensagem de sucesso mostra validade/thumbprint/versão
3. Entregar/demonstrar (já resolve o pedido central da feature: "devemos exibir as informações relevantes")

### Incremental Delivery

1. US1 (P1) → validar → entregar (resposta detalhada exibida ao usuário)
2. US2 (P2) → validar → entregar (requisição com política explícita)
3. Phase 5 (Polish) → suíte de testes completa cobrindo as duas stories

Cada story soma valor sem quebrar a anterior — ambas mexem em trechos isolados do mesmo método, sem dependência cruzada de comportamento.
