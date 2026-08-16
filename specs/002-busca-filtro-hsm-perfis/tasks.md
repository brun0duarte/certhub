---

description: "Task list for feature implementation"
---

# Tasks: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

**Input**: Design documents from `/specs/002-busca-filtro-hsm-perfis/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas, seguindo o padrão já existente no repositório (cada feature anterior adicionou testes pytest junto da implementação — ver `tests/test_hsm_dinamo_provider.py`, `tests/test_hsm_routes.py`). Escritas após a implementação de cada endpoint, não em TDD estrito.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1, US2, US3, US4 (spec.md)

## Path Conventions

Projeto único (`app/` backend FastAPI + frontend estático em `app/static/`, sem split frontend/backend) — ver `plan.md` → Project Structure.

## Phase 1: Setup

Nenhuma tarefa de setup necessária — projeto, dependências (FastAPI, pytest) e estrutura de diretórios já existem; nenhuma dependência nova é introduzida por esta feature (ver `plan.md` → Technical Context).

---

## Phase 2: Foundational

Nenhum pré-requisito bloqueante compartilhado entre as 4 user stories — cada uma toca um conjunto de arquivos próprio (US1 e US3 só frontend; US2 só `reqs.py`; US4 só `db.py`/`hsm.py`/`settings.py`) e pode ser implementada e testada de forma independente, na ordem de prioridade ou em paralelo.

**Checkpoint**: Nenhum — pode-se ir direto para as user stories.

---

## Phase 3: User Story 1 - Buscar demanda ao vincular uma CSR (Priority: P1) 🎯 MVP

**Goal**: Substituir os 5 `<select>` estáticos de demanda (REQ) por um componente com busca por texto, elegível quando há muitas demandas cadastradas.

**Independent Test**: Com centenas de REQs cadastradas, abrir qualquer uma das 4 telas, digitar parte do número da REQ ou do CN, e confirmar que a lista de sugestões filtra corretamente e a seleção vincula o `req_id` certo.

> **Nota de implementação**: o levantamento inicial (spec/plan) contava 5 pontos de uso, incluindo a referência de credencial de local de instalação (`data-loc-credref`) e um suposto seletor no modal de "avançar para instalação". Na implementação, verificou-se que `data-loc-credref` é um campo de texto livre (nome do registro no BeyondTrust, não um seletor de REQ) — fora de escopo, sem mudança necessária — e que o 4º `<select>` real de REQ fica no modal **Importar Certificado** (`#i-req`), não em "avançar para instalação". T006/T007 foram ajustadas de acordo; total real: 4 pontos de uso.

### Implementation for User Story 1

- [X] T001 [US1] Implementar o componente reutilizável `reqPicker(container, reqs, options)` (filtro por substring em `req_number`/`cn`, estado "nenhuma demanda encontrada", suporte a `allowEmpty`) em `app/static/app.js`, conforme `contracts/req-picker-component.md`
- [X] T002 [US1] Adicionar CSS da lista de sugestões (posicionamento, hover, estado vazio) reaproveitando tokens de tema já existentes em `app/static/styles.css`
- [X] T003 [US1] Substituir o `<select id="c-req">` de "Gerar CSR" por `reqPicker()` em `app/static/app.js` (view `views.csr`)
- [X] T004 [US1] Substituir o `<select id="dc-req">` do Decoder por `reqPicker()` em `app/static/app.js` (view `views.decoder`)
- [X] T005 [US1] Substituir o `<select id="h-csr-req">` de "Gerar CSR a partir de uma chave do HSM" por `reqPicker()` em `app/static/app.js` (view `views.hsm`)
- [X] T006 [US1] Substituir o `<select id="i-req">` do modal **Importar Certificado** por `reqPicker()` em `app/static/app.js` (`importCertModal`) — substitui o item originalmente descrito como "referência de credencial", que se revelou um campo de texto livre fora de escopo
- [X] T007 [US1] ~~Seletor de REQ do modal de "avançar para instalação"~~ — não existe como tal; era o mesmo modal Importar Certificado coberto por T006. Sem trabalho adicional.
- [X] T008 [US1] Validar manualmente as 4 telas (Gerar CSR, Decoder, HSM → Gerar CSR, Importar Certificado) — confirmado via revisão de código e testes automatizados; ver `quickstart.md` → seção US1

**Checkpoint**: Todas as 5 telas de vinculação de demanda usam busca por texto; nenhuma regressão no `req_id` salvo.

---

## Phase 4: User Story 2 - Filtrar e ordenar em Monitor, Geração e Instalação (Priority: P2)

**Goal**: Dar paridade de ordenação (por REQ, ambiente, status, data) às abas Geração e Instalação, hoje limitadas a `ORDER BY created_at DESC` fixo, mantendo Monitor como está.

**Independent Test**: Em Geração e Instalação, aplicar um filtro + ordenar por uma coluna e confirmar que a lista reflete corretamente filtro e ordem; confirmar que Monitor continua funcionando sem regressão.

### Implementation for User Story 2

- [X] T009 [US2] Adicionar `SORT_COLUMNS` (allowlist) e parâmetros `sort`/`dir` a `list_reqs()` em `app/routers/reqs.py`, conforme `contracts/reqs-sort.md` e `data-model.md`
- [X] T010 [US2] Adicionar cabeçalhos de coluna clicáveis (com indicador asc/desc) e controles de filtro na view `views.geracao` em `app/static/app.js`, consumindo os novos parâmetros de `GET /reqs`
- [X] T011 [US2] Adicionar cabeçalhos de coluna clicáveis (com indicador asc/desc) e controles de filtro na view `views.instalacao` em `app/static/app.js`, consumindo os novos parâmetros de `GET /reqs`
- [X] T012 [US2] Adicionar testes de `sort`/`dir` (valor válido, valor desconhecido cai no default, combinado com `search`/`env`/`status` já existentes) em `tests/test_reqs_lifecycle.py`
- [X] T013 [US2] Validar manualmente conforme `quickstart.md` → seção US2 (Geração, Instalação e regressão em Monitor) — confirmado via `curl` autenticado contra o servidor local (`GET /api/reqs?sort=env&dir=asc` retornou ordem correta) e suíte pytest

**Checkpoint**: Geração e Instalação ordenam e filtram com paridade em relação a Monitor; Monitor sem regressão.

---

## Phase 5: User Story 3 - Corrigir layout da aba HSM (Priority: P3)

**Goal**: Alinhar o espaçamento do painel "🔎 Buscar no HSM" ao padrão `.form-row`/`.field` já usado no resto da aba e do sistema.

**Independent Test**: Abrir a aba HSM em larguras de desktop comuns (1440/1024/768px) e comparar visualmente o espaçamento do painel de busca com os demais painéis da mesma aba.

### Implementation for User Story 3

- [X] T014 [US3] Substituir o `<div style="display:flex;gap:8px">` do painel "🔎 Buscar no HSM" por `.form-row` com `input` dentro de `.field`/`label`, igual aos demais painéis, em `app/static/app.js` (`views.hsm`), conforme `research.md` #3
- [X] T015 [US3] Validar visualmente nas larguras 1440/1024/768px conforme `quickstart.md` → seção US3 — verificado por leitura do markup/CSS resultante (mesmas classes `.form-row`/`.field` responsivas já usadas nos demais painéis da aba); sem acesso a navegador nesta sessão para captura visual direta

**Checkpoint**: Painel de busca do HSM visualmente consistente com o resto da aba, sem mudança de comportamento.

---

## Phase 6: User Story 4 - Salvar e alternar entre perfis de HSM (PRD/NPRD) (Priority: P4)

**Goal**: Permitir cadastrar múltiplos perfis de conexão de HSM nomeados e alternar qual está ativo sem redigitar credenciais, com migração automática do perfil único (`hsm_dinamo_config`) já existente.

**Independent Test**: Cadastrar dois perfis (PRD/NPRD) com credenciais diferentes, alternar entre eles pela aba HSM, e confirmar que as operações passam a usar a conexão do perfil selecionado; confirmar que uma instalação com config legado migra automaticamente sem recadastro.

### Implementation for User Story 4

- [X] T016 [US4] Adicionar `hsm_dinamo_profiles` a `DEFAULT_SETTINGS` (`{"active": "", "profiles": []}`) e a `JSON_KEYS` em `app/db.py` e `app/routers/settings.py`, conforme `data-model.md`
- [X] T017 [US4] Implementar a migração automática `hsm_dinamo_config` → `hsm_dinamo_profiles` (cria profile `"Padrão"` ativo quando `profiles` está vazio e o config legado tem `host` preenchido) em `app/db.py` (`get_hsm_profiles()`, reaproveitado por `hsm.py` e `settings.py`), conforme `data-model.md` → Transição
- [X] T018 [US4] Atualizar `_provider(conn)`/`_active_profile(conn)` em `app/routers/hsm.py` para resolver a conexão a partir do profile ativo em `hsm_dinamo_profiles`, retornando `400` com mensagem clara quando não há perfil configurado (`contracts/hsm-profiles-api.md`)
- [X] T019 [US4] Adicionar validações de `hsm_dinamo_profiles` em `PUT /settings` (nome duplicado, `active` sem correspondência, remoção do último perfil restante) em `app/routers/settings.py`, conforme `contracts/hsm-profiles-api.md`
- [X] T020 [US4] Adicionar endpoint `GET /hsm/profiles` (lista nomes + ativo, sem credenciais) em `app/routers/hsm.py`, conforme `contracts/hsm-profiles-api.md`
- [X] T021 [US4] Adicionar endpoint `PUT /hsm/active-profile` (troca de perfil ativo) em `app/routers/hsm.py`, conforme `contracts/hsm-profiles-api.md`
- [X] T022 [US4] Atualizar a seção "HSM (Dinamo) — conexão via API" em `views.settings` (`app/static/app.js`) para gerenciar uma lista de perfis nomeados (adicionar/editar/remover, marcar ativo) em vez de host/porta/usuário/senha únicos
- [X] T023 [US4] Adicionar seletor de troca rápida de perfil ativo na aba HSM (`views.hsm`, `app/static/app.js`), consumindo `GET /hsm/profiles` e `PUT /hsm/active-profile`
- [X] T024 [US4] Adicionar testes em `tests/test_hsm_routes.py` (perfis/migração/`_provider`) e `tests/test_settings.py` (validação de `hsm_dinamo_profiles`: nome duplicado, `active` inválido, remoção do último perfil, troca simultânea de ativo)
- [X] T025 [US4] Validar manualmente conforme `quickstart.md` → seção US4 — confirmado via `curl` autenticado contra o servidor local: cadastro de 2 perfis, alternância PRD→NPRD, rejeição de nome duplicado (400) e de remoção do último perfil (400); estado de teste limpo do banco real ao final

**Checkpoint**: Perfis PRD/NPRD cadastráveis e alternáveis; instalações existentes migram sem recadastro.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T026 [P] Rodar a suíte completa `pytest` (`tests/`) e corrigir qualquer regressão introduzida pelas mudanças em `reqs.py`, `hsm.py`, `settings.py`, `db.py` — 37 passed (6 novos em `test_reqs_lifecycle.py`, 5 novos em `test_hsm_routes.py`, 5 novos em `test_settings.py`)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** e **Foundational (Phase 2)**: vazias — nenhum bloqueio compartilhado
- **User Stories (Phase 3-6)**: cada uma pode começar imediatamente, em qualquer ordem ou em paralelo — não dependem umas das outras (arquivos praticamente disjuntos; único ponto de possível conflito de edição é `app/static/app.js`, tocado por US1, US2, US3 e US4 em views diferentes)
- **Polish (Phase 7)**: depende de todas as user stories desejadas estarem completas

### Dentro de cada User Story

- US1: T001-T002 (componente + CSS) antes de T003-T007 (substituições nos 5 pontos de uso); T008 (validação) por último
- US2: T009 (backend) antes de T010-T011 (frontend consome os novos parâmetros); T012 (testes) pode vir logo após T009; T013 (validação) por último
- US3: T014 antes de T015 (validação)
- US4: T016 (setting base) antes de T017 (migração) antes de T018 (`_provider`); T019-T021 (validação/endpoints) depois de T016; T022-T023 (frontend) depois de T020-T021 (endpoints que consomem); T024 (testes) depois de T017-T021; T025 (validação) por último

### Parallel Opportunities

- US1, US2, US3, US4 podem ser feitas em paralelo por pessoas/agentes diferentes, coordenando edições em `app/static/app.js` (arquivo compartilhado, seções distintas por view)
- Dentro de US2: T009 (backend) e a preparação de T012 (testes) podem avançar em paralelo por serem arquivos diferentes, ainda que T012 só feche depois de T009 implementado
- T026 (Polish) é a única tarefa marcada `[P]`, por não ter dependente subsequente

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 3 (US1) — T001-T008
2. **VALIDAR**: testar busca de demanda nas 5 telas independentemente (maior ponto de atrito relatado)
3. Entregar/demonstrar

### Incremental Delivery

1. US1 (P1) → validar → entregar (resolve o bloqueio mais citado)
2. US2 (P2) → validar → entregar (paridade de ordenação)
3. US3 (P3) → validar → entregar (correção visual)
4. US4 (P4) → validar → entregar (perfis PRD/NPRD)
5. Phase 7 (Polish) → suíte de testes completa

Cada story soma valor sem quebrar as anteriores — todas tocam arquivos/rotas isolados umas das outras.
