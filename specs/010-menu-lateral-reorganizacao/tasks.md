---

description: "Task list template for feature implementation"
---

# Tasks: Reorganização do Menu Lateral

**Input**: Design documents from `/specs/010-menu-lateral-reorganizacao/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/nav-counts-api.md, contracts/sidebar-dom-structure.md, quickstart.md

**Tests**: Convenção do projeto (specs 001-009) cobre mudança de backend com pytest — por isso só a US5 (único endpoint novo) tem tarefa de teste automatizado. As demais US são markup/CSS/JS de apresentação, validadas manualmente via `quickstart.md`.

**Organization**: Tarefas agrupadas por user story (spec.md), em ordem de prioridade (P1 → P2 → P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story correspondente (US1-US7)

## Phase 1: Setup

Não aplicável — nenhuma dependência nova. Todas as tarefas alteram arquivos já existentes (`app/static/index.html`, `app/static/app.js`, `app/static/styles.css`, `app/routers/dashboard.py`).

## Phase 2: Foundational

Não aplicável formalmente, mas **US1 e US2 tocam o mesmo bloco de `app/static/index.html`** (a estrutura do `#nav`) — fazer T001 (US1) antes de T004 (US2) evita conflito de edição no mesmo trecho, mesmo as duas sendo independentemente testáveis e entregáveis. As demais stories (US3-US7) não têm essa restrição de ordem entre si.

---

## Phase 3: User Story 1 - Encontrar uma função pela categoria, não por posição decorada (Priority: P1)

**Goal**: Os 16 itens de uso frequente aparecem agrupados em 4 categorias rotuladas; Dashboard isolado no topo.

**Independent Test**: Abrir o menu lateral e ver os 4 cabeçalhos de grupo (Certificados, Ciclo de vida, Segurança, Sistema) acima dos itens correspondentes.

- [X] T001 [US1] Envolver os 16 itens de uso frequente do `#nav` em `app/static/index.html` com marcação de categoria: `<div class="nav-group-label">Certificados</div>` antes de `certs`/`decoder`/`validate`/`monitor`; `<div class="nav-group-label">Ciclo de vida</div>` antes de `geracao`/`instalacao`/`revogacao`/`historico`/`csr`/`kanban`; `<div class="nav-group-label">Segurança</div>` antes de `hsm`/`passwords`; `<div class="nav-group-label">Sistema</div>` antes de `users`/`auditoria`/`docs`; `dashboard` permanece sem cabeçalho, no topo (`data-model.md`)
- [X] T002 [P] [US1] Adicionar CSS `.nav-group-label` em `app/static/styles.css` (`font-size:10.5px`, `text-transform:uppercase`, `letter-spacing:.5px`, `color:var(--sidebar-text-dim)`, `opacity:.65`, padding) e `[data-layout="compact"] .nav-group-label { display: none; }` (rail só-ícones, edge case do spec)
- [X] T003 [US1] Validar os 4 cabeçalhos de grupo + Dashboard isolado no topo, nos 3 layouts — passo 2 do `quickstart.md`

**Checkpoint**: Menu lateral agrupado por categoria, independente das demais user stories.

---

## Phase 4: User Story 2 - Não competir por atenção com itens raros (Priority: P1)

**Goal**: Aparência e Configurações saem da lista rolável e viram um bloco fixo sempre visível.

**Independent Test**: Confirmar que Aparência/Configurações não estão na lista principal, mas aparecem num bloco fixo logo acima do rodapé, sempre acessíveis.

- [X] T004 [US2] Mover os `<a data-view="appearance">`/`<a data-view="settings">` de dentro do `#nav` pra um novo `<div class="sidebar-secondary">`, posicionado entre `</nav>` e `.sidebar-footer`, em `app/static/index.html` (contrato `sidebar-dom-structure.md`)
- [X] T005 [US2] Adicionar CSS `.sidebar-secondary` em `app/static/styles.css`: mesmo estilo de link de `#nav a` (seletor combinado `#nav a, .sidebar-secondary a { ... }` reaproveitando a regra existente) + `border-top: 1px solid var(--sidebar-border)` exclusivo do `.sidebar-secondary`
- [X] T006 [US2] Expandir em `app/static/app.js` os seletores que hoje só cobrem `#nav a[data-view]`/`#nav a` pra também alcançar `.sidebar-secondary a[data-view]`/`.sidebar-secondary a`: dentro de `applyAccent()` (troca de ícone CAIXA), `NAV_DEFAULT_ICONS` (captura inicial dos ícones originais), e `navigate()` (destaque de item ativo) — invariantes 2 e 4 do contrato `sidebar-dom-structure.md`
- [X] T007 [US2] Validar que Aparência/Configurações ficam sempre visíveis fora da lista rolável, recebem destaque de item ativo ao navegar, e trocam de ícone corretamente ao alternar accent CAIXA↔padrão nos dois sentidos — passo 3 do `quickstart.md`

**Checkpoint**: Aparência/Configurações fixos e sempre acessíveis, independente das demais user stories (mas ver nota da Phase 2 sobre ordem com US1 no mesmo arquivo).

---

## Phase 5: User Story 3 - Rodapé do menu sem controle duplicado (Priority: P2)

**Goal**: Botão de alternar tema sai do rodapé — o controle completo já vive em Aparência.

**Independent Test**: Rodapé mostra só usuário/Sair/recolher; alternância de tema em Aparência continua funcionando.

- [X] T008 [US3] Remover o `<button id="theme-toggle">...</button>` de `app/static/index.html`
- [X] T009 [US3] Remover `const themeBtn = $("#theme-toggle");`, as 2 linhas `themeBtn.innerHTML = ...` dentro de `applyTheme()`, e `themeBtn.onclick = ...` em `app/static/app.js`
- [X] T010 [US3] Validar que o rodapé fica só com usuário/Sair/recolher, e que o toggle de tema em Aparência continua funcional e persistente (recarregar a página mantém o tema) — passo 4 do `quickstart.md`

**Checkpoint**: Rodapé limpo, sem controle duplicado, independente das demais user stories.

---

## Phase 6: User Story 4 - Rótulos de menu que nunca quebram linha (Priority: P1)

**Goal**: "Manuais & Comandos" cabe numa linha; qualquer rótulo futuro degrada pra reticências em vez de quebrar.

**Independent Test**: Rótulo de Manuais numa linha só em qualquer tema/accent/layout; rótulo propositalmente longo corta com reticências.

- [X] T011 [US4] Encurtar o texto do `<span class="nav-txt">` do item de manuais de "Manuais & Comandos" pra "Manuais" em `app/static/index.html`, mantendo `title="Manuais & Comandos"` completo no `<a>`
- [X] T012 [P] [US4] Adicionar `white-space: nowrap; overflow: hidden; text-overflow: ellipsis;` na regra de `.nav-txt` em `app/static/styles.css`
- [X] T013 [US4] Validar o rótulo em uma linha só nos temas claro/escuro × accents padrão e "caixa" × 3 layouts, e o corte com reticências usando um rótulo propositalmente longo — passo 5 do `quickstart.md`

**Checkpoint**: Nenhum rótulo de menu quebra linha, independente das demais user stories.

---

## Phase 7: User Story 5 - Ver de relance onde há pendência (Priority: P2)

**Goal**: Itens "Revogação" e "Kanban" mostram contador de pendências, atualizado após ações relevantes.

**Independent Test**: Com pendências > 0, os itens mostram contador; ao resolver a pendência, o contador cai/some.

- [X] T014 [US5] Criar endpoint `GET /nav-counts` em `app/routers/dashboard.py` com as 2 queries (`SELECT COUNT(*) FROM reqs WHERE demand_type='revogacao' AND status NOT IN ('concluida','cancelada')`; `SELECT COUNT(*) FROM tasks WHERE lane != 'concluido'`), retornando `{revogacao_pendente, kanban_pendente}` (contrato `contracts/nav-counts-api.md`)
- [X] T015 [P] [US5] Escrever teste em `tests/test_dashboard.py` cobrindo `GET /nav-counts`: contagem correta com e sem pendências de cada tipo, ambos os campos sempre presentes (mesmo em zero)
- [X] T016 [US5] Implementar `refreshNavCounts()` em `app/static/app.js`: busca `/nav-counts`, injeta/remove `<span class="nav-badge">N</span>` dentro de `#nav a[data-view="revogacao"]`/`#nav a[data-view="kanban"]`, só quando `N > 0`
- [X] T017 [US5] Chamar `refreshNavCounts()` no bootstrap de `app.js` (junto de `applyTheme/applyLayout/applyAccent`), no fim do `load()` de `views.kanban` (após mover/criar/excluir tarefa), e após criar/concluir/cancelar uma demanda de revogação
- [X] T018 [P] [US5] Adicionar CSS `.nav-badge` em `app/static/styles.css` (contador numérico compacto, alinhado à direita do item de menu)
- [X] T019 [US5] Validar que os badges aparecem só com pendência > 0 e se atualizam após mover uma tarefa do Kanban pra "Concluído" — passo 6 do `quickstart.md`

**Checkpoint**: Badges de pendência funcionais, independente das demais user stories.

---

## Phase 8: User Story 6 - Saber o que o botão de recolher faz antes de clicar (Priority: P3)

**Goal**: Tooltip explica a ação do botão de recolher/expandir em cada estado.

**Independent Test**: Passar o mouse no botão nos dois estados (expandido/recolhido) e ver o texto correspondente.

- [X] T020 [US6] Confirmar (sem alteração de código esperada) que `#menu-collapse` já expõe `title` dinâmico via `applyLayout()` em `app/static/app.js` ("Recolher menu" quando expandido, "Expandir menu" quando compacto) — checagem de regressão, não implementação nova
- [X] T021 [US6] Validar o tooltip nos dois estados — passo 7 do `quickstart.md`

**Checkpoint**: Requisito já coberto pelo comportamento existente, confirmado sem regressão.

---

## Phase 9: User Story 7 - Ler ícones e rótulos inativos do menu institucional sem esforço (Priority: P1)

**Goal**: Contraste do texto/ícone inativo do menu no modo CAIXA atinge AA (4.5:1).

**Independent Test**: Medir o contraste do item de menu inativo sobre o azul institucional sólido.

- [X] T022 [US7] Subir `--sidebar-text-dim` de `rgba(255,255,255,.85)` pra `rgba(255,255,255,.92)` dentro do bloco `[data-accent="caixa"]` em `app/static/styles.css`
- [X] T023 [US7] Validar o contraste recalculado (~4.78:1, ≥4.5:1 AA) nos itens inativos do modo CAIXA — passo 8 do `quickstart.md`

**Checkpoint**: Contraste AA garantido no modo institucional, independente das demais user stories.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T024 [P] Rodar `node --check app/static/app.js` e `python3 -m py_compile app/routers/dashboard.py`
- [X] T025 [P] Rodar `pytest -q` (suíte completa) e confirmar nenhuma regressão introduzida
- [X] T026 Rodar o roteiro completo de `quickstart.md` nos 3 layouts (lateral/compacto/horizontal) × 2 temas × accents padrão e "caixa"

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: N/A.
- **Foundational**: N/A formalmente — ver nota da Phase 2 sobre US1→US2 tocarem o mesmo arquivo.
- **User Stories (Phase 3-9)**: Independentes entre si em valor de entrega. Única restrição prática: T001 (US1) antes de T004 (US2), ambas em `app/static/index.html`. US3 (remover botão de tema) faz mais sentido depois de US2 estar pronta (Aparência já acessível fixa), mas não é um bloqueio técnico.
- **Polish (Phase 10)**: Depende de todas as user stories desejadas estarem completas.

### Within Each User Story

- US1: T001 → T002 (paralelo) → T003
- US2: T004 → T005 (paralelo com T006) → T006 → T007
- US3: T008/T009 (paralelos, arquivos diferentes) → T010
- US4: T011 → T012 (paralelo) → T013
- US5: T014 → T015 (paralelo com T016, ambos após T014) → T016 → T017 → T018 (paralelo com T017) → T019
- US6: T020 → T021
- US7: T022 → T023

### Parallel Opportunities

- US3, US4, US5, US6, US7 podem ser trabalhadas em paralelo entre si e em paralelo com US1/US2 (arquivos com alguma sobreposição em `app/static/app.js`/`styles.css` — integrar com cuidado, mas sem dependência lógica).
- Dentro de cada story, tarefas `[P]` (ex. T002, T005/T006, T008/T009, T012, T015, T018) tocam arquivos ou trechos diferentes.

---

## Parallel Example: User Story 5

```bash
# T015 (teste) e T016 (implementação JS) tocam arquivos diferentes,
# mas ambas dependem de T014 (endpoint) já existir:
Task: "Escrever teste de GET /nav-counts em tests/test_dashboard.py"
Task: "Implementar refreshNavCounts() em app/static/app.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 3 (US1 — agrupamento por categoria).
2. **PARAR e VALIDAR**: testar US1 isoladamente via `quickstart.md` passo 2.
3. Já é um incremento de valor entregável sozinho.

### Incremental Delivery

1. US1 → valida → entrega (MVP, agrupamento).
2. US2 → valida → entrega (bloco fixo Aparência/Configurações, mesma prioridade P1, mesmo arquivo do US1 — fazer logo em seguida).
3. US4 → valida → entrega (fix de quebra de linha, P1).
4. US7 → valida → entrega (contraste CAIXA, P1).
5. US3, US5 (P2) → cada uma valida e entrega independentemente, em qualquer ordem.
6. US6 (P3) → última, é só confirmação de comportamento já existente.
7. Phase 10 (Polish) fecha a feature.
