---

description: "Task list for feature implementation"
---

# Tasks: Demandas de Revogação de Certificados

**Input**: Design documents from `/specs/004-revogacao-certificados/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluídas, seguindo o padrão já existente no repositório (cada feature anterior adicionou testes pytest junto da implementação).

**Organization**: Tarefas agrupadas por user story (spec.md) para permitir implementação e teste independentes de cada uma.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivo diferente, sem dependência de tarefa incompleta)
- **[Story]**: US1, US2, US3 (spec.md)

## Path Conventions

Projeto único (`app/` backend FastAPI + frontend estático em `app/static/`) — ver `plan.md` → Project Structure.

## Phase 1: Setup

Nenhuma tarefa de setup necessária — projeto, dependências e estrutura já existem; nenhuma dependência nova é introduzida por esta feature (ver `plan.md` → Technical Context).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Colunas de banco e validação básica de destino — sem isso nenhuma das 3 user stories consegue salvar/exibir uma demanda de revogação corretamente.

**⚠️ CRITICAL**: Nenhuma user story pode ser dada como concluída antes desta fase.

- [X] T001 Adicionar colunas `reqs.revoke_destination`, `reqs.revoke_destination_other`, `reqs.revoke_cert_id` (migração aditiva, próximo bloco `version >= N and version < N+1`) e o valor `'revogado'` em `LIFECYCLE_STATUSES` em `app/db.py`, conforme `data-model.md`
- [X] T002 Adicionar `revoke_destination`, `revoke_destination_other`, `revoke_cert_id`, `force_duplicate` (só em `ReqIn`) aos modelos `ReqIn`/`ReqUpdate` em `app/routers/reqs.py`, conforme `contracts/reqs-revoke-api.md`
- [X] T003 Em `create_req`/`update_req` (`app/routers/reqs.py`): validar que `demand_type='revogacao'` exige `revoke_destination` (um dos 5 valores válidos) e que `revoke_destination='outros'` exige `revoke_destination_other`; implementar a checagem de duplicidade não-bloqueante (409 com `{"duplicate": {...}}` quando já existe demanda de revogação em aberto pro mesmo `revoke_cert_id`/`cn`+`env`, ignorada se `force_duplicate=true`), conforme `contracts/reqs-revoke-api.md`
- [X] T004 Em `update_req` (`app/routers/reqs.py`): quando `status` muda para `concluida` numa demanda `demand_type='revogacao'` com `revoke_cert_id` preenchido, atualizar `certificates.lifecycle_status='revogado'` na mesma transação, conforme `data-model.md`
- [X] T005 [P] Adicionar `revogado: 'Revogado'` ao mapa `LIFECYCLE_STATUS` em `app/static/app.js`

**Checkpoint**: Backend aceita e valida demandas de revogação com destino; conclusão de demanda já atualiza o lifecycle do certificado vinculado.

---

## Phase 3: User Story 1 - Abrir demanda de revogação a partir do inventário (Priority: P1) 🎯 MVP

**Goal**: A partir de um certificado já cadastrado, abrir uma demanda de revogação com CN/serial/thumbprint/emissor pré-preenchidos e destino obrigatório.

**Independent Test**: No detalhe de um certificado em Certificados, acionar "Revogar", confirmar que a demanda nasce com os dados do certificado preenchidos e um destino escolhido; tentar abrir uma segunda pro mesmo certificado sem concluir a primeira e confirmar o aviso de duplicidade.

### Implementation for User Story 1

- [X] T006 [US1] Em `newDemandModal()` (`app/static/app.js`): adicionar bloco de "Destino da revogação" (5 opções + campo de texto livre quando `outros`), visível só quando o tipo selecionado é `revogacao`, e incluir `revoke_destination`/`revoke_destination_other`/`revoke_cert_id` (via `opts`) no `POST /reqs`
- [X] T007 [US1] Em `newDemandModal()` (`app/static/app.js`): tratar resposta `409` de duplicidade — exibir confirmação com os dados da demanda já em aberto e, se confirmado, reenviar com `force_duplicate: true`
- [X] T008 [US1] Em `certDetail()` (`app/static/app.js`): adicionar botão "🚫 Revogar" (ao lado de "📜 Histórico") que abre `newDemandModal('revogacao', {...})` com CN, serial, thumbprint, emissor e `revoke_cert_id: c.id` pré-preenchidos
- [X] T009 [US1] Validar manualmente conforme `quickstart.md` → seção US1

**Checkpoint**: Qualquer certificado do inventário pode virar uma demanda de revogação rastreada, com destino e aviso de duplicidade funcionando.

---

## Phase 4: User Story 2 - Acompanhar demandas de revogação numa aba própria (Priority: P2)

**Goal**: Aba "Revogação" dedicada, no mesmo padrão de Geração/Instalação (busca, filtro, ordenação, "+ Nova demanda").

**Independent Test**: Acessar a aba Revogação, confirmar que só demandas desse tipo aparecem, com busca/filtro/ordenação funcionando, e que dá pra abrir uma demanda nova direto dali (sem vir do inventário).

### Implementation for User Story 2

- [X] T010 [US2] Criar `views.revogacao` em `app/static/app.js` (mesmo padrão de `views.instalacao`: `getViewState`, busca, filtro por ambiente/status/destino, ordenação, paginação, botão "+ Nova demanda" chamando `newDemandModal('revogacao', {}, load)`)
- [X] T011 [US2] Registrar a rota `views.revogacao` e o item de navegação "🚫 Revogação" em `app/static/app.js`/`app/static/index.html`
- [X] T012 [US2] No detalhe da demanda (`openReq()`, `app/static/app.js`): exibir o destino de revogação (e o texto livre quando `outros`) quando `demand_type='revogacao'`
- [X] T013 [US2] Validar manualmente conforme `quickstart.md` → seção US2

**Checkpoint**: Aba Revogação lista, filtra e ordena demandas de revogação; conclusão de uma demanda reflete `lifecycle_status='revogado'` no certificado vinculado (herdado da Fase 2).

---

## Phase 5: User Story 3 - Destino/canal por demanda, pronto para automação futura (Priority: P3)

**Goal**: Um provider real por destino (Internacional, Serpro, AC Interna NPRD, AC Interna PRD, Outros), acionável por uma ação explícita na demanda, sempre retornando "não conectado" nesta fase — sem nenhuma chamada de rede real.

**Independent Test**: Numa demanda de revogação em aberto, acionar "solicitar revogação" e confirmar que a resposta menciona o destino escolhido e deixa claro que não há conexão automática ainda — repetir pros 5 destinos e confirmar que cada um responde com seu próprio texto (não um stub genérico único).

### Implementation for User Story 3

- [X] T014 [P] [US3] Criar `app/services/revocation/base.py` (`RevocationProvider`, ABC com `revoke(cn, serial="", thumbprint="", reason="") -> dict`) e as 5 implementações (`internacional.py`, `serpro.py`, `ac_interna.py` com `AcInternaRevocationProvider(ambiente="nprd"|"prd")`, `outros.py`), todas retornando `{"ok": False, "code": "NOT_CONNECTED", "output": "..."}` sem nenhum I/O externo, conforme `contracts/revocation-provider.md`
- [X] T015 [US3] Adicionar `POST /reqs/{id}/revoke` em `app/routers/reqs.py`: valida `demand_type='revogacao'`, resolve o provider pelo `revoke_destination` da demanda, chama `revoke()`, registra em `activity_log`, retorna o resultado, conforme `contracts/reqs-revoke-api.md`
- [X] T016 [US3] Em `openReq()` (`app/static/app.js`): adicionar ação "Solicitar revogação" (visível quando `demand_type='revogacao'`) que chama `POST /reqs/{id}/revoke` e exibe a mensagem retornada
- [X] T017 [US3] Validar manualmente conforme `quickstart.md` → seção US3 (5 destinos, cada um com sua própria mensagem)

**Checkpoint**: Cada demanda de revogação tem uma ação real que resolve e chama o provider correto, sempre honesta sobre não ter conexão real — pronta pra virar automação de verdade trocando só o provider.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T018 [P] Criar `tests/test_revocation_providers.py`: um teste por provider confirmando `ok=False`, `code="NOT_CONNECTED"`, mensagem menciona o destino
- [X] T019 Estender `tests/test_reqs_lifecycle.py`: destino obrigatório (e `outros` exigindo texto livre), duplicidade não-bloqueante (`409` sem `force_duplicate`, sucesso com), atualização de `certificates.lifecycle_status` ao concluir demanda com `revoke_cert_id`
- [X] T020 [P] Rodar a suíte completa `pytest` (`tests/`) e corrigir qualquer regressão

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: vazia
- **Foundational (Phase 2)**: bloqueia as 3 user stories — nenhuma delas funciona sem as colunas/validação de destino
- **User Stories (Phase 3-5)**: US1 e US2 compartilham o bloco de destino em `newDemandModal()` (T006) — US2 depende de US1 estar pronta pra que seu próprio "+ Nova demanda" já tenha o seletor de destino funcionando; US3 é estruturalmente independente das outras duas (só precisa da Fase 2) mas entrega menos valor sozinha, por isso vem por último
- **Polish (Phase 6)**: depende de todas as user stories desejadas estarem completas

### Dentro de cada User Story

- US1: T006 antes de T007 (tratamento de duplicidade depende do formulário existir) e de T008 (botão Revogar abre o mesmo modal); T009 por último
- US2: T010 antes de T011 (registro de rota depende da view existir); T012 é independente, pode ser feita em paralelo; T013 por último
- US3: T014 (providers, sem dependência de banco) pode começar em paralelo com a Fase 2; T015 depende de T014 e da Fase 2 (colunas `revoke_destination`); T016 depende de T015; T017 por último

### Parallel Opportunities

- T005 (Fase 2) e T014 (US3, providers) não dependem de nenhuma outra tarefa — podem começar imediatamente, em paralelo com o resto da Fase 2
- T012 (US2) pode ser feita em paralelo com T010/T011 (mesma view, mas função diferente — `openReq()` vs `views.revogacao`)
- T018 (Polish) não tem dependente subsequente

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 2 (Foundational) — T001-T005
2. Completar Phase 3 (US1) — T006-T009
3. **VALIDAR**: abrir uma demanda de revogação a partir de um certificado real do inventário, com destino e aviso de duplicidade funcionando
4. Entregar/demonstrar

### Incremental Delivery

1. Foundational → US1 (P1) → validar → entregar (resolve a lacuna mais citada: revogação sendo ignorada)
2. US2 (P2) → validar → entregar (aba própria de acompanhamento)
3. US3 (P3) → validar → entregar (providers reais, prontos pra automação futura)
4. Phase 6 (Polish) → suíte de testes completa

Cada story soma valor sem quebrar as anteriores — US2 reaproveita o formulário que US1 já deixou pronto; US3 não muda nada do que US1/US2 já entregaram, só adiciona uma ação nova na demanda.
