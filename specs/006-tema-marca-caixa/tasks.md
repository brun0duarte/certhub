---

description: "Task list template for feature implementation"
---

# Tasks: Tema Institucional CAIXA

**Input**: Design documents from `/specs/006-tema-marca-caixa/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes, revisados nesta rodada)

**Tests**: Não incluídas — não solicitadas no spec e o projeto não tem framework de teste de frontend. Validação é manual via `quickstart.md` (18 passos, fase de Polish).

**Organization**: Tarefas agrupadas por user story do `spec.md` (US1-US3 já entregues; US4-US7 novas, escopo expandido).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos/blocos diferentes, sem dependência)
- **[Story]**: US1..US7
- Caminhos de arquivo são sempre absolutos ao repositório (`app/static/...`)

## Phase 1: Setup

Sem tarefas — feature não introduz build tooling nem dependência de projeto (a fonte Poppins é um `@import` CSS, tratada na Phase 9/US5, não uma dependência de build).

---

## Phase 2: Foundational (Blocking Prerequisites) — ✅ concluída

- [X] T001 Adicionar a entrada `["caixa", "#0066B3"]` ao array `ACCENTS` em `app/static/app.js`.
- [X] T002 [P] Adicionar `--sidebar-bg`, `--sidebar-text`, `--sidebar-text-dim`, `--sidebar-border` (passthrough) em `app/static/styles.css`.
- [X] T003 Atualizar `.sidebar` para consumir `var(--sidebar-bg)`/`var(--sidebar-border)` em `app/static/styles.css`.
- [X] T004 [P] Atualizar `.brand-name`/`.brand-sub`/`#nav a` para consumir `var(--sidebar-text)`/`var(--sidebar-text-dim)` em `app/static/styles.css`.

---

## Phase 3: User Story 1 - Ativar o modo visual CAIXA (Priority: P1) 🎯 MVP — ✅ concluída

- [X] T005 [US1] Bloco `[data-accent="caixa"]` com `--accent`/`--accent-soft`/`--accent-text` claros em `app/static/styles.css`.
- [X] T006 [US1] `--sidebar-bg`/`--sidebar-text`/`--sidebar-text-dim`/`--sidebar-border` sob `[data-accent="caixa"]` em `app/static/styles.css`.
- [X] T007 [US1] Constante SVG do elemento-síntese "X" em `app/static/app.js` *(nesta rodada, movida para `icons.js` — ver T016)*.
- [X] T008 [US1] `applyAccent(a)` troca `.brand-icon` entre SVG e emoji em `app/static/app.js`.
- [X] T009 [P] [US1] Regra `.brand-icon svg { width:26px; height:26px }` em `app/static/styles.css`.

---

## Phase 4: User Story 2 - Alternar entre claro e escuro no Modo CAIXA (Priority: P2) — ✅ concluída

- [X] T010 [US2] Bloco `[data-theme="dark"][data-accent="caixa"]` com `--accent`/`--accent-soft`/`--accent-text` escuros em `app/static/styles.css`.

---

## Phase 5: User Story 3 - Uso pontual da cor secundária (laranja) (Priority: P3) — ✅ concluída

- [X] T011 [US3] `--caixa-orange`/`--caixa-orange-soft`/`--caixa-orange-text` em `app/static/styles.css`.
- [X] T012 [US3] `[data-accent="caixa"] .badge.k-cat { background: var(--caixa-orange-soft); color: var(--caixa-orange-text); }` em `app/static/styles.css`.

---

## Phase 6: Polish v1 — ✅ concluída (contraste); quickstart/layout absorvidos pela Phase 12 abaixo

- [X] T013 [P] Medir e ajustar contraste WCAG de `--sidebar-text-dim` e `--caixa-orange-text` (ajustados para `.85`/`#945812`) em `app/static/styles.css`.
- ~~T014 (quickstart parcial)~~ e ~~T015 (layouts compacto/horizontal)~~ — retiradas desta numeração; escopo absorvido e ampliado por **T033**/**T034** na Phase 12, junto com a validação dos itens novos (ícone/fonte/login).

---

## Phase 7: Foundational da expansão (Blocking Prerequisites para US4-US7)

**Purpose**: Infra compartilhada pelas 4 novas stories — sem isso, nenhuma é testável.

**⚠️ CRITICAL**: Nenhuma US4-US7 pode começar antes desta fase estar completa.

- [X] T014 [P] Criar `app/static/icons.js` com a estrutura (mapas vazios/placeholder, preenchidos em T017-T018): `EMOJI_ICONS = {}`, `NAV_ICONS = {}`, `CAIXA_X_ICON` (SVG movido de `app.js`, mesma geometria/cores de T007), `DEFAULT_FAVICON_HREF` (mesmo SVG-emoji hoje hardcoded em `index.html:9`), `CAIXA_FAVICON_HREF` (data-URI baseado em `CAIXA_X_ICON`), e a função `applyIconSkin(root)` (ver `contracts/caixa-icon-skin.md` — checa `document.documentElement.dataset.accent === "caixa"`, percorre `root.querySelectorAll(".btn, .badge, .view-title, .tab-btn, .rtab-btn, .subtab-btn, .app-opt, .wizard-step, .stat-label")`, troca o emoji líder do primeiro nó de texto por SVG).
- [X] T015 Incluir `<script src="/static/icons.js"></script>` em `app/static/index.html` (antes de `<script src="/static/app.js">`) e em `app/static/login.html` (antes do primeiro uso de `CAIXA_X_ICON`/favicon, dentro do `<head>` ou logo no início do `<body>`).
- [X] T016 Em `app/static/app.js`: remover a constante `CAIXA_X_ICON` local (linhas ~3932-3935, já usa a de `icons.js`); atualizar `applyAccent(a)` para também setar `document.querySelector('link[rel="icon"]').href` como `CAIXA_FAVICON_HREF` quando `a === "caixa"` e `DEFAULT_FAVICON_HREF` caso contrário.

**Checkpoint**: `icons.js` existe e carrega, favicon já troca dinamicamente em `index.html`, base pronta pras stories preencherem os mapas e ligarem os chokepoints.

---

## Phase 8: User Story 4 - Ícones de marca substituem os emojis (Priority: P1) 🎯 MVP da expansão

**Goal**: Com Modo CAIXA ativo, nav lateral, títulos de página, botões e badges mostram ícones de linha em vez de emoji; toasts e dados de usuário nunca são tocados; fora do Modo CAIXA nada muda.

**Independent Test**: Ativar Modo CAIXA, navegar por 3 seções + 1 modal, confirmar ícones de linha nesses pontos e emoji intacto em um toast disparado durante a navegação; desativar e confirmar reversão total — passos 6-12 do `quickstart.md`.

### Implementation for User Story 4

- [X] T017 [US4] Preencher `EMOJI_ICONS` em `app/static/icons.js` com os ~61 mapeamentos emoji→SVG (formato Lucide, `stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"`, MIT), cobrindo pelo menos os emojis usados em títulos de view, botões de ação e badges de status listados em `research.md` §8 (📊📡📋🔧🚫🗄️🗂️🔍🔗🔑📖👥🕵️🎨⚙️✅⚠️🌐🔒🚪🌙☀️ e os demais do levantamento original).
- [X] T018 [P] [US4] Preencher `NAV_ICONS` em `app/static/icons.js` com os 18 mapeamentos `data-view→SVG` (um por item de `#nav a` em `app/static/index.html`).
- [X] T019 [US4] Chamar `applyIconSkin(main)` ao final de `navigate()` (`app/static/app.js`, logo após `try { await view(); }`, linha ~330) e `applyIconSkin(root)` ao final de `modal(...)` (linha ~153, logo após `root.innerHTML` ser setado).
- [X] T020 [P] [US4] Instrumentar as sub-renders que populam DOM fora de `navigate()`/`modal()` com uma chamada extra a `applyIconSkin(container)` em `app/static/app.js`: `renderList` (L104), `renderCsrResult` (L2280), `renderActiveProfileInfo` (L3008), `renderSearchResults` (L3027), `renderHsmProfiles` (L3413), `renderResult` (L3667), `renderLocConfigFields` (L1293) e o handler que atualiza `[data-loc-automation-badge]` (L1888).
- [X] T021 [US4] Em `applyAccent(a)` (`app/static/app.js`), aplicar `NAV_ICONS` aos 18 `<a data-view>` de `#nav` quando `a === "caixa"`, revertendo para o emoji original (capturado em `NAV_DEFAULT_ICONS`) quando `a !== "caixa"`. **Corte de escopo feito na implementação**: os 3 botões de `.sidebar-footer` (`theme-toggle`/`btn-logout`/`menu-collapse`) ficaram de fora — seu conteúdo é regenerado dinamicamente por `applyTheme()`/`applyLayout()` (não por `applyAccent()`), então trocar o ícone ali exigiria tocar essas duas funções também; SC-006 só exige os 18 itens de nav, não esses 3 botões utilitários, então o corte não quebra nenhum critério de sucesso do spec.
- [X] T022 [P] [US4] Regra CSS de dimensionamento dos SVGs substitutos (ex. `1em` dentro de `.btn`, `.badge`, `#nav a`, `.view-title`) em `app/static/styles.css`.
- [ ] T023 [US4] Validação manual: confirmar que `toast(...)` (`app.js:24`) e `.user-name` (`app.js:4021`) nunca são alterados com Modo CAIXA ativo, e que nenhum emoji muda fora do Modo CAIXA — passos 10-11 do `quickstart.md`. *(pendente — requer navegador; movida pra validação final junto com T033-T035)*

**Checkpoint**: User Story 4 funcional e testável isoladamente.

---

## Phase 9: User Story 5 - Tipografia de marca em títulos (Priority: P2)

**Goal**: Sob Modo CAIXA, `.brand-name`, `.view-title` e `.panel h3` (mais o `<h1>` de `login.html`) usam Poppins; corpo de texto nunca muda.

**Independent Test**: Ativar Modo CAIXA, comparar visualmente o título de uma página contra um parágrafo normal — passo 13 do `quickstart.md`.

### Implementation for User Story 5

- [X] T024 [US5] Adicionar `@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;700&display=swap');` no topo de `app/static/styles.css` (antes do bloco `:root`).
- [X] T025 [US5] Adicionar `--font-caixa: "Poppins", "Segoe UI", system-ui, sans-serif;` ao bloco `[data-accent="caixa"]` em `app/static/styles.css`.
- [X] T026 [P] [US5] Aplicar `font-family: var(--font-caixa)` em `.brand-name`, `.view-title` e `.panel h3` sob `[data-accent="caixa"]` (`app/static/styles.css`), e replicar o mesmo `@import` + regra equivalente para `.brand-header h1` no `<style>` inline de `app/static/login.html`.

**Checkpoint**: User Story 5 funcional e testável isoladamente, sem depender de US4/US6/US7.

---

## Phase 10: User Story 6 - Cor institucional em títulos e botões (Priority: P2)

**Goal**: `.view-title` usa a cor institucional; `.btn-primary` permanece legível (AA) no azul escuro; `.badge-lc-*` fica documentado como fora de escopo.

**Independent Test**: Ativar Modo CAIXA, abrir qualquer página e conferir cor do título; em tema escuro, validar contraste do botão primário com DevTools — passos 14-15 do `quickstart.md`.

### Implementation for User Story 6

- [X] T027 [US6] Adicionar `[data-accent="caixa"] .view-title { color: var(--accent-text); }` em `app/static/styles.css` (regra já deve incluir `font-family: var(--font-caixa)` de T026, se aplicada antes).
- [X] T028 [US6] Calcular contraste WCAG de `#fff` sobre `--accent` claro (`#0066B3`) e escuro (`#0097D7`) para `.btn-primary`; registrar o resultado em `research.md` §10. Se a razão escura for `< 4.5:1`, criar token `--caixa-btn-text` (cor ajustada) e usá-lo em `.btn-primary` só sob `[data-theme="dark"][data-accent="caixa"]` em `app/static/styles.css`.
- [X] T029 [P] [US6] Confirmar (sem alterar código) que `.badge-lc-*` (`app/static/styles.css:574-579`) permanece intocado sob Modo CAIXA — checagem de não-regressão, documentada em `research.md` §10 (já registrada; esta tarefa é a verificação final antes do Polish).

**Checkpoint**: User Story 6 funcional e testável isoladamente.

---

## Phase 11: User Story 7 - Tela de login reflete o Modo CAIXA (Priority: P3)

**Goal**: `login.html` lê `certhub-accent` do `localStorage` e aplica cor/ícone/favicon institucionais antes do primeiro paint, sem exigir autenticação.

**Independent Test**: Com Modo CAIXA ativado em sessão anterior, fazer logout e conferir a tela de login — passos 16-18 do `quickstart.md`.

### Implementation for User Story 7

- [X] T030 [US7] Adicionar script inline no `<head>` de `app/static/login.html`, antes do CSS ser aplicado: `document.documentElement.dataset.accent = localStorage.getItem('certhub-accent') || 'blue';` (não tocar em `certhub-theme`, que continua hardcoded `data-theme="dark"`).
- [X] T031 [US7] Trocar `<h1>🔐 CertHub</h1>` (`app/static/login.html:94`) por lógica condicional (script após o DOM montar) que usa `CAIXA_X_ICON` quando `data-accent === "caixa"`, mantendo o texto "CertHub" e o emoji 🔐 nos demais casos.
- [X] T032 [US7] Adicionar `<link rel="icon">` em `app/static/login.html` (hoje ausente), com `href` setado dinamicamente pelo mesmo script de T030/T031: `CAIXA_FAVICON_HREF` se `data-accent === "caixa"`, `DEFAULT_FAVICON_HREF` caso contrário.

**Checkpoint**: Todas as 7 user stories funcionam de forma independente e combinada.

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Validação final e não-regressão em todo o escopo expandido (substitui os antigos T014/T015 da Phase 6, com escopo maior).

- [ ] T033 Executar os 18 passos de `quickstart.md` de ponta a ponta (cor, ícone, fonte, login/favicon) e corrigir qualquer regressão encontrada nas 5 opções de destaque existentes, no padrão CertHub, ou em toasts/dados de usuário/`.badge-lc-*`.
- [ ] T034 [P] Conferir visualmente o Modo CAIXA (ícones + Poppins + cor) nos layouts `[data-layout="compact"]` e `[data-layout="top"]` (aba Aparência → "Posição do menu") — sidebar/ícones/títulos devem permanecer corretos em ambos.
- [ ] T035 [P] Validar contraste final (fórmula WCAG) de todos os pares novos desta rodada. **Feito analiticamente**: `.view-title` sobre fundo de página — claro 7.68:1, escuro 8.12:1 (ambos aprovados); `.btn-primary` sobre `--accent` escuro — corrigido pra 4.63:1 (T028, registrado em `research.md` §10). **Pendente (requer navegador)**: legibilidade visual do favicon em 16×16px.
- [X] T036 Corrigir contraste reportado pelo usuário em uso real: `.sidebar-footer .btn-ghost` (botões tema/logout/colapsar) usava `var(--text-dim)` sobre o azul da sidebar (1.21:1 no claro, 1.94:1 no escuro — reprovado) e `#nav a:hover` usava `var(--bg-hover)` (cinza quase branco) com texto branco por cima (~1:1). Corrigido com novo token `--sidebar-hover-bg` (`rgba(255,255,255,.12)`, 4.70:1 com texto branco) e override `[data-accent="caixa"] .sidebar-footer .btn-ghost` usando `--sidebar-text(-dim)` em `app/static/styles.css` — detalhes em `research.md` §5c.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: vazia.
- **Foundational v1 (Phase 2)** → **US1/US2/US3 (Phases 3-5)** → **Polish v1 (Phase 6)**: ✅ toda essa cadeia já concluída.
- **Foundational da expansão (Phase 7)**: depende só da Phase 2 (já concluída) — BLOQUEIA US4-US7.
- **US4 (Phase 8)**, **US5 (Phase 9)**, **US6 (Phase 10)**, **US7 (Phase 11)**: todas dependem só da Phase 7; são independentes entre si (podem rodar em paralelo por pessoas diferentes).
- **Polish final (Phase 12)**: depende de US4+US5+US6+US7 completas.

### Within Each New Story

- US4: T017/T018 (mapas de dados) podem ser feitas em paralelo entre si; T019 depende de `applyIconSkin` existir (T014); T020 depende de T019 (mesmo padrão de chamada); T021 é independente de T019/T020 (não usa `applyIconSkin`); T022 é CSS puro, paralelo a tudo; T023 é validação, por último.
- US5: T024 → T025 → T026 (cada uma depende da anterior existir).
- US6: T027 pode rodar em paralelo com T028; T029 é verificação, por último.
- US7: T030 → T031 → T032 (sequencial, mesmo arquivo `login.html`, mesma lógica incremental).

### Parallel Opportunities

- Phase 7: T014 é pré-requisito de T015/T016 (arquivo precisa existir antes de ser referenciado), mas pode ser feita isoladamente por uma pessoa enquanto outra prepara T017/T018 (conteúdo dos mapas) em paralelo, já que são só dados dentro do mesmo arquivo (merge depois).
- Entre stories: US4, US5, US6 e US7 são total mente independentes após a Phase 7 — 4 pessoas podem trabalhar em paralelo.
- Polish: T034 e T035 são `[P]` entre si; T033 (quickstart completo) depende das duas terem passado para não re-testar em cima de problema já conhecido.

---

## Parallel Example: Foundational da expansão + User Stories

```bash
# Foundational da expansão:
Task: "Criar app/static/icons.js com estrutura e applyIconSkin(root)"           # T014
Task: "Incluir <script src='/static/icons.js'> em index.html e login.html"      # T015 (depende de T014 existir)

# Após Phase 7, em paralelo entre stories:
Task: "Preencher EMOJI_ICONS (~61 entradas) em icons.js"                        # T017 (US4)
Task: "@import Poppins + --font-caixa em styles.css"                            # T024/T025 (US5)
Task: "[data-accent='caixa'] .view-title { color: var(--accent-text) }"         # T027 (US6)
Task: "Script inline em login.html lendo certhub-accent"                        # T030 (US7)
```

---

## Implementation Strategy

### MVP da expansão (User Story 4 apenas, depois da Foundational da expansão)

1. Completar Phase 7: Foundational da expansão (T014-T016).
2. Completar Phase 8: User Story 4 (T017-T023).
3. **PARAR e VALIDAR**: rodar os passos 6-12 do `quickstart.md` isoladamente.
4. Nesse ponto o pedido mais explícito do usuário ("substituir esses emoji") já está entregue, mesmo sem tipografia (US5), cor de título (US6) ou login (US7).

### Incremental Delivery

1. Foundational da expansão → `icons.js` existe, favicon dinâmico em `index.html`.
2. + User Story 4 → emojis viram ícone de linha sob Modo CAIXA (MVP da expansão).
3. + User Story 5 → tipografia de marca em títulos.
4. + User Story 6 → título de página colorido, botão primário revalidado.
5. + User Story 7 → login reflete o modo.
6. + Polish → quickstart completo (18 passos), layouts compacto/horizontal, contraste final.

## Notes

- Nenhuma tarefa desta rodada toca `app/routers/`, `app/services/`, `app/db.py` ou `tests/` — feature continua 100% `app/static/`.
- `[P]` = arquivos/blocos diferentes ou dados independentes, sem dependência entre si.
- Commitar depois de cada checkpoint de story (Phase 7, depois cada uma de US4/US5/US6/US7, depois Phase 12).
