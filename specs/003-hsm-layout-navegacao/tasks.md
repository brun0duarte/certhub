---

description: "Task list for feature implementation"
---

# Tasks: Ajustes de Layout do HSM e Preservação de Estado entre Abas

**Input**: Design documents from `/specs/003-hsm-layout-navegacao/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas onde há cobertura automatizada aplicável (backend). US1 (CSS) e a maior parte de US3 (estado de frontend) não têm framework de teste automatizado no projeto — validação é manual/visual, conforme `quickstart.md`.

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1, US2, US3 (spec.md)

## Path Conventions

Projeto único (`app/` backend FastAPI + frontend estático em `app/static/`, sem split frontend/backend) — ver `plan.md` → Project Structure.

## Phase 1: Setup

Nenhuma tarefa de setup necessária — projeto, dependências e estrutura já existem; nenhuma dependência nova é introduzida por esta feature (ver `plan.md` → Technical Context).

---

## Phase 2: Foundational

Nenhum pré-requisito bloqueante compartilhado entre as 3 user stories — cada uma é sustentada por uma decisão técnica independente (US1: regra CSS local; US2: campo extra num endpoint já existente; US3: novo store `viewState` em `app.js`). US2 e US3 tocam `views.hsm` no mesmo arquivo (`app/static/app.js`), mas em seções diferentes (cabeçalho vs. formulários) — coordenação de edição, não bloqueio de dependência.

**Checkpoint**: Nenhum — pode-se ir direto para as user stories.

---

## Phase 3: User Story 1 - Corrigir sobreposição do painel "Criar chave" (Priority: P1) 🎯 MVP

**Goal**: Eliminar a sobreposição visual entre o `grid.grid-2` (Criar chave + Importar certificado) e o painel seguinte na aba HSM, restaurando o espaçamento padrão do sistema.

**Independent Test**: Abrir a aba HSM em larguras de desktop comuns (1440/1024/768px) e confirmar visualmente que não há sobreposição entre o `grid-2` e o painel "Gerar CSR a partir de uma chave do HSM" logo abaixo.

### Implementation for User Story 1

- [ ] T001 [US1] Adicionar regra CSS `.grid + .panel { margin-top: 16px; }` em `app/static/styles.css`, restaurando o espaçamento que `.panel + .panel` (linha ~121) não aplica quando o irmão anterior é um container `.grid` em vez de outro `.panel` diretamente — conforme `research.md` #1
- [ ] T002 [US1] Validar visualmente nas larguras 1440/1024/768px na aba HSM e conferir o mesmo espaçamento nas demais telas com `.grid.grid-2` (Decoder, Certificados, Validar cadeia), conforme `quickstart.md` → seção US1

**Checkpoint**: Painel "Criar chave"/"Importar certificado" com espaçamento consistente em relação ao painel seguinte, em todas as telas que usam `.grid.grid-2`.

---

## Phase 4: User Story 2 - Exibir o perfil de HSM ativo no topo da aba (Priority: P2)

**Goal**: Mostrar nome, host e usuário do perfil de HSM atualmente ativo, visível assim que a aba HSM é aberta, sem nunca expor a senha.

**Independent Test**: Com dois ou mais perfis de HSM cadastrados, abrir a aba HSM e confirmar que nome/host/usuário do perfil ativo aparecem no topo; trocar o perfil ativo e confirmar atualização imediata da informação exibida.

### Implementation for User Story 2

- [ ] T003 [US2] Estender `list_profiles()` (`GET /hsm/profiles`) em `app/routers/hsm.py` pra incluir `host` e `username` de cada perfil na resposta, mantendo `password` sempre omitida, conforme `contracts/hsm-profiles-api-extension.md`
- [ ] T004 [US2] Atualizar `tests/test_hsm_routes.py::test_get_hsm_profiles_lists_names_without_credentials` pra validar que `host`/`username` aparecem na resposta e `password` nunca aparece
- [ ] T005 [US2] Adicionar, no topo da aba HSM (`views.hsm`, `app/static/app.js`), um texto exibindo `"{name} · {host} · {username}"` do perfil ativo (usando os dados já retornados por `GET /hsm/profiles`, já chamado nessa view), atualizado no `onchange` do seletor de troca rápida (`#h-active-profile`) existente; preservar o aviso de "nenhum perfil configurado" quando `profiles` estiver vazio
- [ ] T006 [US2] Validar manualmente conforme `quickstart.md` → seção US2 (exibição, troca de perfil, estado sem perfil configurado)

**Checkpoint**: Perfil ativo (nome, host, usuário) visível no topo da aba HSM, sem exibir senha, atualizando ao trocar de perfil.

---

## Phase 5: User Story 3 - Preservar dados ao trocar de aba (Priority: P3)

**Goal**: Formulários não salvos, filtros/busca aplicados e página atual de listas paginadas continuam como estavam ao voltar a uma aba visitada antes, dentro da mesma sessão (sem sobreviver a F5).

**Independent Test**: Preencher parcialmente um formulário ou aplicar filtro/busca/página numa lista, trocar de aba, voltar, e confirmar que tudo continua exatamente como estava; recarregar a página (F5) e confirmar que o estado reseta normalmente (fora de escopo).

### Implementation for User Story 3

- [ ] T007 [US3] Implementar `viewState = {}` e `getViewState(name, defaults)` no escopo de módulo de `app/static/app.js`, conforme `contracts/view-state-store.md`
- [ ] T008 [US3] Estender `reqPicker()` (`app/static/app.js`) com callback opcional `onChange(value)`, disparado a cada seleção/limpeza, sem alterar o comportamento existente de `getValue()` pros chamadores que não passarem `onChange`
- [ ] T009 [US3] Migrar `views.geracao` (`app/static/app.js`) pra ler/gravar `search`, `env`, `status`, `type`, `sortKey`, `sortDir`, `page` via `getViewState("geracao", ...)` em vez de variáveis locais, conforme `data-model.md`
- [ ] T010 [US3] Migrar `views.instalacao` (`app/static/app.js`) pra ler/gravar `search`, `env`, `status`, `sortKey`, `sortDir`, `page` via `getViewState("instalacao", ...)`
- [ ] T011 [US3] Migrar `views.historico` (`app/static/app.js`) pra ler/gravar `search`, `env`, `status`, `type`, `page` via `getViewState("historico", ...)`
- [ ] T012 [US3] Migrar `views.monitor` (`app/static/app.js`) pra ler/gravar `search`, `days`, `ownership`, `pendingOnly`, `sortKey`, `sortDir`, `page` via `getViewState("monitor", ...)`
- [ ] T013 [US3] Migrar `views.auditoria` (`app/static/app.js`) pra ler/gravar seus filtros existentes (usuário/ação/busca) + `page` via `getViewState("auditoria", ...)`
- [ ] T014 [US3] Migrar `views.certs` (`app/static/app.js`) pra ler/gravar seu filtro/busca existente + `page` via `getViewState("certs", ...)`
- [ ] T015 [US3] Migrar `views.csr` (`app/static/app.js`) pra ler/gravar engine, demanda vinculada (via `onChange` do `reqPicker`, T008), CN, SANs, campos do Subject DN (O/OU/C/ST/L/E), tipo de chave e label HSM via `getViewState("csr", ...)`; resultado exibido (`#c-result`) MUST NOT ser preservado (FR-011)
- [ ] T016 [US3] Migrar `views.hsm` (`app/static/app.js`) pra ler/gravar os campos dos 4 formulários (criar chave: rótulo/tipo; importar: rótulo/PEM colado — não o arquivo; gerar CSR: rótulo/CN/SANs/subject DN/demanda vinculada via `onChange`; exportar: rótulo/formato) via `getViewState("hsm", ...)`; resultados exibidos (`#h-search-result`, `#h-csr-result`) MUST NOT ser preservados (FR-011)
- [ ] T017 [US3] Migrar `views.decoder` (`app/static/app.js`) pra ler/gravar o campo de texto PEM colado via `getViewState("decoder", ...)`; arquivo selecionado e resultado decodificado (`#dc-result`) MUST NOT ser preservados (FR-010/FR-011, limitação de `FileList`)
- [ ] T018 [US3] Migrar `views.settings` (`app/static/app.js`) pra ler/gravar todos os campos do formulário (pastas, alertas, política de senha, templates, perfis de HSM em edição — incluindo campos de senha, mantidos só em memória) via `getViewState("settings", ...)`
- [ ] T019 [US3] Nas views paginadas migradas (T009-T014), ao restaurar `page` de `getViewState` e o total de páginas retornado pelo servidor for menor que a página salva, ajustar automaticamente pra última página válida antes de renderizar (FR-009)
- [ ] T020 [US3] Validar manualmente conforme `quickstart.md` → seção US3 (formulários, filtros/busca/paginação, reset em F5, ajuste de página quando dados diminuem)

**Checkpoint**: Trocar de aba e voltar preserva formulários não salvos, filtros/busca e paginação em todas as views migradas; F5 continua resetando tudo; nenhum dado sensível é persistido em armazenamento do navegador.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 [P] Rodar a suíte completa `pytest` (`tests/`) e corrigir qualquer regressão introduzida pela mudança em `app/routers/hsm.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** e **Foundational (Phase 2)**: vazias — nenhum bloqueio compartilhado
- **User Stories (Phase 3-5)**: cada uma pode começar imediatamente, em qualquer ordem — não dependem umas das outras; único ponto de coordenação é edição concorrente em `app/static/app.js` (US1 não toca esse arquivo; US2 toca o cabeçalho de `views.hsm`; US3 toca corpo de `views.hsm` e outras ~9 views)
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas

### Dentro de cada User Story

- US1: T001 antes de T002 (validação)
- US2: T003 (backend) antes de T004 (teste) e de T005 (frontend consome os novos campos); T006 (validação) por último
- US3: T007 (store) e T008 (extensão do `reqPicker`) antes de T009-T018 (migração das views, cada uma independente entre si, mas T015/T016 dependem de T008 por usarem `reqPicker`); T019 depende de T009-T014 (views paginadas) já migradas; T020 (validação) por último

### Parallel Opportunities

- US1, US2, US3 podem ser feitas em paralelo por pessoas/agentes diferentes, coordenando edições em `app/static/app.js`
- Dentro de US3, T009-T014 (views de lista) são independentes entre si (arquivos/seções distintas da mesma view function, sem dependência umas das outras) — podem avançar em paralelo depois de T007; T015-T018 (views de formulário) igualmente independentes entre si depois de T007-T008
- T021 (Polish) é a única tarefa marcada `[P]`, por não ter dependente subsequente

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 3 (US1) — T001-T002
2. **VALIDAR**: confirmar visualmente que a sobreposição sumiu na aba HSM (e nas demais telas com `.grid.grid-2`)
3. Entregar/demonstrar

### Incremental Delivery

1. US1 (P1) → validar → entregar (corrige o defeito visual ativo)
2. US2 (P2) → validar → entregar (reduz risco de operar no HSM errado)
3. US3 (P3) → validar → entregar (evita perda de trabalho não salvo)
4. Phase 6 (Polish) → suíte de testes completa

Cada story soma valor sem quebrar as anteriores — US1 é só CSS, US2 só estende um endpoint e um trecho isolado da UI, US3 é aditiva (todo comportamento atual continua funcionando mesmo sem o estado restaurado).
