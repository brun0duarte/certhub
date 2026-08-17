---

description: "Task list for feature implementation"
---

# Tasks: Automação Real dos Providers de Instalação

**Input**: Design documents from `/specs/005-automacao-instaladores/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas, seguindo o padrão já existente no repositório.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1, US2, US3 (spec.md)

## Path Conventions

Projeto único (`app/` backend FastAPI + frontend estático em `app/static/`) — ver `plan.md` → Project Structure.

## Phase 1: Setup

- [X] T001 Adicionar `requests`, `boto3`, `edgegrid-python` a `requirements.txt`, conforme `research.md` #3 (únicas dependências novas, cobrem os 5 providers de nuvem de US1)

---

## Phase 2: Foundational

Nenhum pré-requisito bloqueante compartilhado entre as 3 user stories — cada provider é independente, e `installer_credentials` (usado só por US1) não bloqueia US2/US3, que dependem de uma lacuna diferente (integração com BeyondTrust, fora de escopo — `research.md` #2).

**Checkpoint**: Nenhum — pode-se ir direto para as user stories (T001 do Setup é o único pré-requisito real, e só pra US1).

---

## Phase 3: User Story 1 - Instalação automática nos provedores de nuvem (Priority: P1) 🎯 MVP

**Goal**: Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion e Akamai passam a tentar a instalação de verdade, usando credenciais configuráveis em Configurações.

**Independent Test**: Configurar `installer_credentials` de um provedor, cadastrar um local desse tipo, acionar "Instalar", e confirmar que o sistema tenta a operação real (sucesso ou erro real da API) — sem credencial configurada, confirmar a mensagem específica de credencial faltando.

### Implementation for User Story 1

- [X] T002 [US1] Adicionar `installer_credentials` (default `{"keyvault_azure": {}, "aws": {}, "azion": {}, "akamai": {}}`) a `DEFAULT_SETTINGS` em `app/db.py`, conforme `data-model.md`
- [X] T003 [US1] Adicionar `'installer_credentials'` a `JSON_KEYS` em `app/routers/settings.py`, conforme `contracts/settings-installer-credentials.md`
- [X] T004 [US1] Adicionar seção "Credenciais dos instaladores" em `views.settings` (`app/static/app.js`) com 4 blocos de campos (Azure: tenant/client id/secret; AWS: access key/secret/region; Azion: api token; Akamai: os 4 campos EdgeGrid), seguindo o mesmo padrão visual das seções de credenciais já existentes (HSM, hsmutil)
- [X] T005 [US1] Implementar `AzureKeyVaultProvider.install()` em `app/services/installers/providers.py`: sem credencial → erro específico; com credencial → token OAuth2 client-credentials + upload REST do certificado pro vault; erro real da API repassado em `error`, conforme `contracts/install-provider.md`
- [X] T006 [US1] Implementar `AwsAcmProvider.install()` em `app/services/installers/providers.py`: sem credencial → erro específico "AWS"; com credencial → `boto3` client ACM, `import_certificate`; exceções do `boto3` repassadas em `error`, conforme `contracts/install-provider.md`
- [X] T007 [US1] Implementar `AwsSecretsManagerProvider.install()` em `app/services/installers/providers.py`: mesmo padrão de credencial `aws` de T006; `boto3` client Secrets Manager, `put_secret_value` com as 3 chaves fixas (`tls.crt`/`tls.key`/`ca.crt`), conforme `contracts/install-provider.md`
- [X] T008 [US1] Implementar `AzionProvider.install()` em `app/services/installers/providers.py`: sem token → erro específico; com token → `POST /v4/edge_certificates` via `requests`, header `Authorization: Token`; erro HTTP real repassado, conforme `contracts/install-provider.md`
- [X] T009 [US1] Implementar `AkamaiProvider.install()` em `app/services/installers/providers.py`: sem credencial → erro específico; com credencial → chamada assinada via `edgegrid-python` pra API CPS (`enrollment_id`); erro real repassado, conforme `contracts/install-provider.md`
- [ ] T010 [US1] Validar manualmente conforme `quickstart.md` → seção US1 (5 provedores, com e sem credencial)

**Checkpoint**: Os 5 providers de nuvem tentam a instalação de verdade; sem credencial, erro específico por provedor; com credencial válida/inválida, resultado real repassado ao histórico do local.

---

## Phase 4: User Story 2 - Instalação automática em servidores via acesso remoto (Priority: P2)

**Goal**: Apache, Nginx e IIS validam a configuração de verdade e explicam especificamente por que a automação depende de uma integração com o BeyondTrust ainda não implementada — em vez do texto genérico único de hoje.

**Independent Test**: Cadastrar um local Apache/Nginx/IIS com configuração válida, acionar "Instalar", e confirmar a mensagem específica sobre a lacuna do BeyondTrust; sem configuração válida, confirmar o erro de configuração faltando antes disso.

### Implementation for User Story 2

- [X] T011 [US2] Implementar `ApacheSshProvider.install()` em `app/services/installers/providers.py`: validar campos obrigatórios do `config_fields`; retornar mensagem específica sobre a lacuna de integração com o BeyondTrust pra resolver `credential_ref`, conforme `contracts/install-provider.md` e `research.md` #2
- [X] T012 [US2] Implementar `NginxSshProvider.install()` em `app/services/installers/providers.py`: mesmo padrão de T011
- [X] T013 [US2] Implementar `IisWinrmProvider.install()` em `app/services/installers/providers.py`: mesmo padrão de T011 (WinRM em vez de SSH, mesma lacuna de credencial)
- [ ] T014 [US2] Validar manualmente conforme `quickstart.md` → seção US2

**Checkpoint**: Apache/Nginx/IIS retornam mensagens específicas e honestas em vez do texto genérico único — validação de configuração já é real, execução remota fica documentadamente bloqueada até existir integração com BeyondTrust.

---

## Phase 5: User Story 3 - Instalação automática em destinos especializados (Priority: P3)

**Goal**: Balanceador e Mainframe também deixam de responder com o texto genérico único, cada um com sua própria explicação específica.

**Independent Test**: Cadastrar um local Balanceador, confirmar a mensagem sobre protocolo não conhecido; cadastrar um local Mainframe, confirmar a mensagem sobre a lacuna do BeyondTrust (mesma de US2, já que Mainframe também depende de acesso remoto ao host USS).

### Implementation for User Story 3

- [X] T015 [US3] Implementar `MainframeRacdcertProvider.install()` em `app/services/installers/providers.py`: mesmo padrão de bloqueio por BeyondTrust de US2 (T011), conforme `research.md` #5
- [X] T016 [US3] Implementar `BalanceadorProvider.install()` em `app/services/installers/providers.py`: validar campos obrigatórios; retornar mensagem específica sobre a ausência de protocolo/API conhecido pro tipo informado, conforme `contracts/install-provider.md` e `research.md` #5
- [ ] T017 [US3] Validar manualmente conforme `quickstart.md` → seção US3

**Checkpoint**: Todos os 10 tipos de local têm uma resposta específica sua — nenhum mais cai no texto genérico único original.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 [P] Criar `tests/test_installer_providers.py`: pros 5 providers de nuvem (US1) — sem credencial (erro específico), com credencial + chamada HTTP/`boto3` mockada com sucesso, com credencial + chamada mockada com erro (mensagem real repassada); pros 5 restantes (US2/US3) — mensagem de bloqueio específica por tipo, confirmando que nenhuma tentativa de conexão real é feita
- [X] T019 [P] Rodar a suíte completa `pytest` (`tests/`) e corrigir qualquer regressão introduzida pelas mudanças em `providers.py`/`settings.py`/`db.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: `T001` (dependências novas) — só bloqueia US1, que é quem usa `requests`/`boto3`/`edgegrid-python`
- **Foundational (Phase 2)**: vazia — nenhum bloqueio compartilhado entre as 3 stories
- **User Stories (Phase 3-5)**: totalmente independentes entre si — cada uma mexe em classes de provider diferentes dentro do mesmo arquivo (`providers.py`), sem overlap de comportamento; US2/US3 nem dependem de T001 (não usam as libs novas)
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas

### Dentro de cada User Story

- US1: T002-T004 (plumbing de credencial) antes de T005-T009 (cada provider lê `installer_credentials`); T010 (validação) por último. T005-T009 tocam o mesmo arquivo (`providers.py`) — sequenciais entre si, apesar de logicamente independentes
- US2: T011-T013 independentes entre si (mesmo arquivo, sem overlap de classe); T014 por último
- US3: T015-T016 independentes entre si; T017 por último

### Parallel Opportunities

- US1, US2, US3 podem ser feitas em paralelo por pessoas/agentes diferentes, coordenando edições em `app/services/installers/providers.py` (arquivo compartilhado, classes distintas por provider)
- T018/T019 (Polish) são as únicas tarefas marcadas `[P]`, por não terem dependente subsequente entre si

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1 (Setup) — T001
2. Completar Phase 3 (US1) — T002-T010
3. **VALIDAR**: confirmar automação real nos 5 provedores de nuvem, com e sem credencial configurada
4. Entregar/demonstrar

### Incremental Delivery

1. Setup → US1 (P1) → validar → entregar (resolve os provedores de maior volume: Azure/AWS/Azion/Akamai)
2. US2 (P2) → validar → entregar (mensagens honestas em vez do texto genérico, Apache/Nginx/IIS)
3. US3 (P3) → validar → entregar (Balanceador/Mainframe, últimos dois tipos)
4. Phase 6 (Polish) → suíte de testes completa

Cada story soma valor sem quebrar as anteriores — todas mexem em classes de provider isoladas, sem dependência cruzada de comportamento.
