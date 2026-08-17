---

description: "Task list template for feature implementation"
---

# Tasks: Hierarquia e Clareza do Dashboard

**Input**: Design documents from `/specs/009-dashboard-hierarquia-clareza/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dashboard-api.md, quickstart.md

**Tests**: A spec não pede TDD explícito, mas o projeto tem convenção estabelecida (specs 001-008) de cobrir mudança de backend com pytest — por isso a única tarefa de teste automatizado aqui é a da US6 (a única com mudança de backend). As demais US são só CSS/JS de apresentação, validadas manualmente via `quickstart.md` (sem framework de teste JS no projeto).

**Organization**: Tarefas agrupadas por user story (spec.md), em ordem de prioridade (P1 → P2 → P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: User story correspondente (US1-US8)

## Phase 1: Setup

Não aplicável — nenhuma dependência nova, nenhuma inicialização de projeto. Todas as tarefas alteram arquivos já existentes (`app/static/app.js`, `app/static/styles.css`, `app/routers/dashboard.py`).

## Phase 2: Foundational

Não aplicável — não há infraestrutura compartilhada bloqueante. As 8 user stories alteram trechos independentes de `views.dashboard`/`styles.css`; a única dependência de backend (extensão de `next_expiring`) fica isolada dentro da fase da US6 e não bloqueia as demais.

---

## Phase 3: User Story 1 - Reconhecer severidade dos KPIs sem calcular (Priority: P1) 🎯 MVP

**Goal**: Cor de cada card de KPI reflete a severidade real do valor (não a posição), e cards cumulativos avisam disso.

**Independent Test**: Configurar 4+ janelas de alerta em Configurações e conferir visualmente que a cor de cada card bate com a urgência do threshold, e que os cards de threshold >1º mostram o aviso de cumulativo.

- [X] T001 [US1] Reescrever o mapeamento de cor dos stat-cards de alerta em `app/static/app.js` (`views.dashboard`, dentro do `.map` de `alerts`) pra decidir a classe por **valor** do threshold `a` (`a<=30`→`stat-red`, `a<=60`→`stat-amber`, `a>60`→`stat-green`) em vez do índice `i`
- [X] T002 [P] [US1] Adicionar classe `.stat-critical` (borda/peso extra) em `app/static/styles.css` e aplicá-la ao card "Vencidos" em `app/static/app.js`, além de `stat-red`
- [X] T003 [US1] Adicionar `<div class="stat-hint">` nos cards de threshold além do primeiro em `app/static/app.js` (texto "inclui os já contados em ≤Nd"), e a regra `.stat-hint` (`color: var(--text-dim)`, `font-size` pequeno) em `app/static/styles.css`
- [X] T004 [US1] Validar manualmente no navegador com 4+ janelas de alerta configuradas — passo 2 do `quickstart.md`

**Checkpoint**: Dashboard com hierarquia de severidade correta, independente das demais user stories.

---

## Phase 4: User Story 2 - Ler badges de status com contraste adequado e sem confundir com ação (Priority: P1)

**Goal**: Todos os badges de lifecycle atingem contraste AA nos dois temas; "Excluir" deixa de soar como botão de ação.

**Independent Test**: No tema claro, abrir um certificado com status `reservado`/`instalado`/`em_inventario` e confirmar legibilidade do badge; confirmar que nenhum status usa mais o rótulo "Excluir".

- [X] T005 [P] [US2] Reescrever as 6 regras `.badge-lc-*` em `app/static/styles.css` (~linhas 626-631) usando tokens de tema (`var(--purple)`/`-soft`, `var(--green)`/`-soft`, `var(--accent)`/`-soft`, `var(--amber)`/`-soft`, `var(--red)`/`-soft`, `var(--gray)`/`-soft`) em vez de hex fixo
- [X] T006 [P] [US2] Renomear o valor de `LIFECYCLE_STATUS.excluir` de `'Excluir'` para `'Baixado do inventário'` em `app/static/app.js` (a chave `excluir` do dicionário não muda)
- [X] T007 [US2] Validar contraste calculado (WCAG, ≥4.5:1) dos 6 pares nos temas claro e escuro — passo 3 do `quickstart.md`

**Checkpoint**: Badges de lifecycle legíveis e sem ambiguidade de ação, independente das demais user stories.

---

## Phase 5: User Story 3 - Ver os 3 gráficos de análise sem espaço vazio (Priority: P1)

**Goal**: A linha de painéis de análise (demandas por mês / tipos de chave / saúde dos certificados) preenche 3 colunas sem buraco.

**Independent Test**: Popular os 3 conjuntos de dados (`reqs_by_month`, `key_types`, `cert_health`) e conferir que os 3 painéis ocupam uma grade de 3 colunas sem espaço vazio.

- [X] T008 [US3] Trocar `class="grid grid-2 mt"` por `class="grid grid-3 mt"` na linha de painéis de análise em `app/static/app.js` (`views.dashboard`)
- [X] T009 [US3] Validar visualmente com os 3 conjuntos de dados presentes, e depois com só 1-2 presentes (sem quebra de layout) — passo 4 do `quickstart.md`

**Checkpoint**: Grade de análise sem espaço vazio, independente das demais user stories.

---

## Phase 6: User Story 4 - Entender os códigos de ambiente sem perguntar (Priority: P2)

**Goal**: Tooltip e legenda fixa explicam PRD/TQS/HMP/DES e a lógica de cor por severidade.

**Independent Test**: Passar o mouse num badge de ambiente (tooltip) e localizar a legenda fixa no Dashboard.

- [X] T010 [P] [US4] Criar mapa `ENV_LABEL` (`PRD`→"Produção", `HMP`→"Homologação", `TQS`→"Teste de Qualidade", `DES`→"Desenvolvimento") em `app/static/app.js`, usado no `title` de `envBadge()`
- [X] T011 [US4] Adicionar bloco de legenda fixa (4 siglas + ponto colorido + nome completo, com nota de que a cor segue severidade) abaixo de "Demandas por ambiente e status" em `app/static/app.js` (`views.dashboard`), reaproveitando as cores de `.badge-PRD/-TQS/-HMP/-DES`
- [X] T012 [P] [US4] Adicionar CSS da legenda (`.env-legend`, `.env-legend-dot`) em `app/static/styles.css`

**Checkpoint**: Siglas de ambiente autoexplicativas, independente das demais user stories.

---

## Phase 7: User Story 5 - Escanear vencimentos agrupados por data (Priority: P2)

**Goal**: Certificados vencendo na mesma data aparecem agrupados numa linha-resumo expansível.

**Independent Test**: Com 5+ certificados vencendo na mesma data, conferir a linha-resumo com contador e a expansão ao clicar.

- [X] T013 [US5] Implementar agrupamento client-side de `next_expiring` por `not_after` (reduce) em `app/static/app.js` (`views.dashboard`), gerando linha-resumo com contagem apenas quando houver **3 ou mais** certificados na mesma data (1 ou 2 permanecem como linhas soltas, FR-009)
- [X] T014 [US5] Implementar toggle de expansão/colapso da linha-resumo (classe CSS, sem framework) em `app/static/app.js`
- [X] T015 [P] [US5] Adicionar CSS da linha-resumo e indicador de expansão (`.expiry-group-row`) em `app/static/styles.css`
- [X] T016 [US5] Validar com 5+ certificados na mesma data (agrupa) e também com 1-2 certificados na mesma data (permanecem soltos, sem virar grupo) — passo 6 do `quickstart.md`

**Checkpoint**: Tabela de vencimentos agrupada por data, independente das demais user stories.

---

## Phase 8: User Story 6 - Iniciar renovação direto da tabela do Dashboard (Priority: P2)

**Goal**: Ação rápida de renovação por linha, reaproveitando o fluxo já existente no Monitor.

**Independent Test**: Clicar na ação de uma linha sem demanda ativa e confirmar que `newDemandModal('renovacao', ...)` abre pré-preenchido; linhas com demanda ativa não mostram a ação.

- [X] T017 [US6] Estender a query `next_expiring` em `app/routers/dashboard.py` com `c.ownership, c.external_partner, c.partner_email` e o mesmo `LEFT JOIN reqs active_req ON active_req.cn = c.cn AND active_req.demand_type IN ('geracao','recebimento') AND active_req.status NOT IN ('concluida','cancelada')` + `has_active_demand`, espelhando `app/routers/monitor.py:47-63` (contrato: `contracts/dashboard-api.md`)
- [X] T018 [P] [US6] Escrever/estender teste em `tests/test_dashboard.py` cobrindo os novos campos de `next_expiring` (presença de `ownership`/`external_partner`/`partner_email`, e `has_active_demand` correto com e sem REQ ativa pro mesmo CN)
- [X] T019 [US6] Adicionar 4ª coluna com botão de ação (`data-renew`, ícone "🔄", `title="Iniciar renovação"`) na tabela "Próximos vencimentos" em `app/static/app.js`, reaproveitando o handler `$$("[data-renew]").forEach(...)` já existente (mesmo padrão de `views.monitor`, `app.js:614-619`); linha com `has_active_demand=1` não renderiza o botão
- [X] T020 [US6] Validar abertura do `newDemandModal` pré-preenchido e a ausência da ação em linhas com demanda ativa — passo 7 do `quickstart.md`

**Checkpoint**: Renovação iniciável direto do Dashboard, independente das demais user stories (depende só da extensão de backend própria, T017).

---

## Phase 9: User Story 7 - Ler a Atividade Recente sem ruído repetido (Priority: P2)

**Goal**: Cada evento cabe em 2 linhas; eventos consecutivos idênticos aparecem agrupados.

**Independent Test**: Gerar 3+ eventos consecutivos idênticos (mesma ação, mesma REQ) e conferir a entrada agrupada com contador.

- [X] T021 [US7] Comprimir a renderização de cada evento em `app/static/app.js` (`views.dashboard`, bloco `d.activity.map`) de 3 linhas para 2 (detalhe + timestamp/usuário na mesma linha)
- [X] T022 [US7] Implementar agrupamento de eventos consecutivos idênticos (mesma `action` + mesmo `req_number`) via reduce client-side, com sufixo "×N", em `app/static/app.js` — limiar fixo de **3 ou mais** eventos consecutivos idênticos pra agrupar (1 ou 2 permanecem soltos, FR-013)
- [X] T023 [US7] Validar que 3+ eventos consecutivos idênticos agrupam com contador e que 1-2 eventos idênticos seguidos permanecem soltos (sem agrupar) — passo 8 do `quickstart.md`

**Checkpoint**: Feed de atividade compacto e agrupado, independente das demais user stories.

---

## Phase 10: User Story 8 - Ver tendência e o mês atual no gráfico de demandas (Priority: P3)

**Goal**: Gráfico "Demandas criadas por mês" mostra linha de média e destaca o mês corrente.

**Independent Test**: Com histórico de 3+ meses incluindo o mês atual, conferir a linha de referência e o destaque visual na barra correspondente.

- [X] T024 [US8] Estender `chartVBars(items, opts)` em `app/static/app.js` para aceitar `avg` (linha de referência posicionada via `top` calculado na mesma escala das barras) e `currentLabel` (aplica classe `.vbar-current` na barra correspondente)
- [X] T025 [US8] Calcular `avg` (`reqs_by_month.reduce((s,r)=>s+r.n,0)/reqs_by_month.length`) e `currentLabel` (`new Date().toISOString().slice(0,7)`) no chamador de `chartVBars` dentro de `views.dashboard`, em `app/static/app.js`
- [X] T026 [P] [US8] Adicionar CSS de `.vbar-avg-line` (linha horizontal absoluta) e `.vbar-current` (destaque de cor/negrito) em `app/static/styles.css`
- [X] T027 [US8] Validar com histórico de 3+ meses incluindo o mês corrente — passo 9 do `quickstart.md`

**Checkpoint**: Gráfico de demandas com contexto de média/mês atual, independente das demais user stories.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T028 [P] Rodar `node --check app/static/app.js` e `python3 -m py_compile app/routers/dashboard.py`
- [X] T029 [P] Rodar `pytest -q` (suíte completa) e confirmar nenhuma regressão introduzida pelas mudanças em `dashboard.py`
- [X] T030 Rodar o roteiro completo de `quickstart.md` nos temas claro e escuro

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup / Foundational**: N/A (ver Phase 1/2 acima) — user stories podem começar imediatamente.
- **User Stories (Phase 3-10)**: Todas independentes entre si — nenhuma depende de outra estar pronta. Podem ser feitas em qualquer ordem ou em paralelo; a ordem de prioridade (P1→P3) só reflete valor de entrega, não dependência técnica.
- **Polish (Phase 11)**: Depende de todas as user stories desejadas estarem completas.

### Within Each User Story

- US1: T001 → T002/T003 (paralelos entre si) → T004
- US2: T005/T006 (paralelos) → T007
- US3: T008 → T009
- US4: T010/T012 (paralelos) → T011 → validação
- US5: T013 → T014 → T015 (paralelo com T014) → T016
- US6: T017 → T018 (paralelo com T019, ambos após T017) → T019 → T020
- US7: T021 → T022 → T023
- US8: T024 → T025 → T026 (paralelo com T025) → T027

### Parallel Opportunities

- Todas as 8 user stories podem ser trabalhadas em paralelo por pessoas/sessões diferentes (arquivos com sobreposição só em `app/static/app.js`/`styles.css` — cuidado ao integrar mudanças concorrentes no mesmo arquivo, mas sem dependência lógica entre elas).
- Dentro de cada story, tarefas marcadas `[P]` (ex. T002/T003, T005/T006, T010/T012) tocam trechos/arquivos diferentes e podem rodar em paralelo.

---

## Parallel Example: User Story 2

```bash
# T005 e T006 tocam arquivos diferentes (styles.css vs app.js) e são independentes:
Task: "Reescrever .badge-lc-* em app/static/styles.css usando tokens de tema"
Task: "Renomear LIFECYCLE_STATUS.excluir em app/static/app.js"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 3 (US1 — severidade dos KPIs).
2. **PARAR e VALIDAR**: testar US1 isoladamente via `quickstart.md` passo 2.
3. Já é um incremento de valor entregável sozinho.

### Incremental Delivery

1. US1 → valida → entrega (MVP).
2. US2 → valida → entrega (contraste/acessibilidade, mesma prioridade P1).
3. US3 → valida → entrega (fix visual do grid, mesma prioridade P1).
4. US4-US7 (P2) → cada uma valida e entrega independentemente, em qualquer ordem.
5. US8 (P3) → última, menor prioridade, puramente incremental.
6. Phase 11 (Polish) fecha a feature.
