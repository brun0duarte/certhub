---

description: "Task list template for feature implementation"
---

# Tasks: Integração com HSM via API (Dinamo Networks)

**Input**: Design documents from `/specs/001-integracao-hsm-dinamo/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (todos presentes)

**Tests**: incluídas — `plan.md` já compromete a feature com testes do `DinamoJsProvider` via bridge Node fake (research.md #6), seguindo o estilo leve de `tests/test_reqs_lifecycle.py` (funções isoladas, sem infraestrutura externa).

**Organization**: tasks agrupadas por user story (US1..US5, prioridades de `spec.md`), habilitando entrega incremental.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência de tarefa incompleta)
- **[Story]**: US1..US5, conforme `spec.md`
- Caminhos de arquivo exatos em cada descrição

## Path Conventions

Projeto único (`app/` como backend FastAPI + estático), conforme `plan.md` → Project Structure. Sem split `backend/`/`frontend/`.

---

## Phase 1: Setup

**Purpose**: preparar dependência do bridge Node e os novos pontos de configuração, sem ainda tocar lógica de HSM.

- [X] T001 [P] Criar `app/services/hsm/node/package.json` declarando a dependência `@dinamonetworks/hsm-dinamo` (nome, versão mínima, script `"start": "node hsm-helper.js"`), conforme decisão em `research.md` #1. Rodar `npm install` dentro de `app/services/hsm/node/` para gerar `node_modules`/`package-lock.json`.
- [X] T002 [P] Adicionar a chave `hsm_dinamo_config` a `DEFAULT_SETTINGS` em `app/db.py`, com valor default `json.dumps({"host": "", "port": "", "username": "", "password": ""})`, conforme `data-model.md` → Configuração.
- [X] T003 [P] Adicionar `"hsm_dinamo_config"` ao conjunto `JSON_KEYS` em `app/routers/settings.py` (linha com `JSON_KEYS = {"password_policy", "hsmutil_templates"}`) para que `PUT /settings` valide o valor como JSON.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: bridge Node, provider Dinamo real e schema local — tudo que as 5 user stories dependem.

**⚠️ CRITICAL**: nenhuma user story pode começar antes desta fase estar completa.

- [X] T004 Adicionar migração `ALTER TABLE certificates ADD COLUMN hsm_label TEXT` em `app/db.py`, seguindo o padrão de migração incremental já usado no arquivo (ex.: bloco de `certificates_temp` / funções `_seed_vN`). Coluna nullable, sem afetar registros existentes.
- [X] T005 Implementar `app/services/hsm/node/hsm-helper.js`: dispatcher por `process.argv[2]` (ações `gen-key`, `gen-csr`, `import-cert`, `export-pfx`, `search`), lendo o request JSON via stdin, conectando ao HSM com `@dinamonetworks/hsm-dinamo` (`hsm.connect({host, port, username, password})`, padrão `authUsernamePassword`), executando a operação correspondente e escrevendo a resposta JSON (`{"ok": true, "data": {...}}` ou `{"ok": false, "error": ..., "code": ...}`) em stdout, exatamente conforme `contracts/hsm-node-bridge.md`. `search` usa `conn.management.listObjs()` (já confirmado em `research.md` #1/#2) filtrando por `query` no label/CN.
- [X] T006 Implementar `app/services/hsm/dinamo_js.py` (substituindo o stub atual): classe `DinamoJsProvider` que (a) implementa o contrato `KeyProvider` (`gen_key`, `gen_csr`, `export_key`) chamando `hsm-helper.js` via `subprocess.run(["node", ".../hsm-helper.js", action], input=json.dumps(...), timeout=30, capture_output=True, text=True)`; (b) adiciona os métodos específicos de HSM `import_cert(label, cert_pem)`, `export_pfx(label, password)` (timeout 60s) e `search_objects(query)`, todos parseando o stdout JSON do bridge e propagando `code` (`NOT_FOUND`, `ALREADY_EXISTS`, `KEY_MISMATCH`, `NOT_EXPORTABLE`, `CONN_FAILED`, `TIMEOUT`) no dict de retorno. Credenciais e senha do PFX nunca entram em `argv` (só via stdin), conforme `contracts/hsm-node-bridge.md`.
- [X] T007 [P] Criar `tests/test_hsm_dinamo_provider.py`: testes de `DinamoJsProvider` com `subprocess.run` mockado (monkeypatch), cobrindo pelo menos um caminho de sucesso e um de cada `code` de erro (`NOT_FOUND`, `ALREADY_EXISTS`, `KEY_MISMATCH`, `NOT_EXPORTABLE`, `CONN_FAILED`, `TIMEOUT`), verificando que o provider nunca inclui credencial/senha no `argv` capturado pelo mock.
- [X] T008 Criar `app/routers/hsm.py` (esqueleto): `APIRouter(tags=["hsm"])`, função auxiliar `_provider(conn)` que lê `hsm_dinamo_config` via `get_setting` e instancia `DinamoJsProvider`, e um helper `_map_error(result)` que traduz `code` → `HTTPException` (`409`/`404`/`422`/`403`/`502`), conforme `contracts/hsm-rest-api.md`. Registrar o router em `app/main.py`, adicionando `hsm` ao import de `.routers` (linha 9-10) e `hsm.router` à tupla de `app.include_router(...)` (linha 19-22), mesmo padrão dos demais routers (prefixo `/api`, `Depends(require_auth)`).

**Checkpoint**: bridge Node, provider e router-esqueleto prontos — user stories podem começar.

---

## Phase 3: User Story 1 - Gerar chave criptográfica no HSM (Priority: P1) 🎯 MVP

**Goal**: administrador cria uma chave no HSM informando rótulo e tipo.

**Independent Test**: `POST /api/hsm/keys` com rótulo novo retorna sucesso; repetir o mesmo rótulo retorna `409`.

- [X] T009 [US1] Implementar `POST /hsm/keys` em `app/routers/hsm.py`: body `{label, key_type}`, chama `provider.gen_key(label, key_type)` (ação `gen-key` do bridge), mapeia `ALREADY_EXISTS`→409 e `CONN_FAILED`→502 via `_map_error`, grava `log_activity(conn, "hsm_chave_criada", f"{label} · {key_type}", None, user["id"])` em caso de sucesso, conforme `contracts/hsm-rest-api.md`.
- [X] T010 [P] [US1] Testes de `POST /hsm/keys` em `tests/test_hsm_routes.py` (novo arquivo): caso de sucesso e caso de rótulo duplicado (`409`), usando um `DinamoJsProvider` fake/injetado (mesma técnica de mock de T007) — sem exigir HSM real.

**Checkpoint**: US1 funcional e testável de forma independente.

---

## Phase 4: User Story 2 - Gerar CSR a partir de chave do HSM (Priority: P1)

**Goal**: administrador gera uma CSR usando uma chave já existente no HSM.

**Independent Test**: `POST /api/hsm/keys/{label}/csr` para um rótulo existente retorna CSR PEM válida; para rótulo inexistente retorna `404`.

- [X] T011 [US2] Implementar `POST /hsm/keys/{label}/csr` em `app/routers/hsm.py`: body `{cn, sans, org, ou, country, state, locality, email, req_id?}`, chama `provider.gen_csr(label, cn, sans, ...)` (ação `gen-csr`), mapeia `NOT_FOUND`→404, reaproveita `_req_and_folder` (padrão de `app/routers/csr.py`) quando `req_id` é informado para salvar `csr_pem`/atualizar `reqs.status`, insere em `csrs` (mesmo formato de `POST /csr/generate`), `log_activity(conn, "csr_gerada", f"CSR HSM · {cn} · label {label}", req_id, user["id"])`.
- [X] T012 [P] [US2] Testes de `POST /hsm/keys/{label}/csr` em `tests/test_hsm_routes.py`: sucesso (CSR PEM contém `BEGIN CERTIFICATE REQUEST`) e rótulo inexistente (`404`).

**Checkpoint**: US1 + US2 juntas cobrem chave → CSR ponta a ponta.

---

## Phase 5: User Story 3 - Importar certificado emitido para o HSM (Priority: P2)

**Goal**: administrador importa o certificado emitido por uma CA e o associa à chave no HSM.

**Independent Test**: importar certificado compatível com uma chave existente retorna sucesso e o registro aparece em `GET /api/hsm/search`; importar certificado de chave pública diferente retorna `422`.

- [X] T013 [US3] Implementar `POST /hsm/keys/{label}/certificate` em `app/routers/hsm.py`: upload multipart (mesmo padrão de `POST /certs` em `app/routers/certs.py`), parseia o certificado via `app/services/certparse.py`, chama `provider.import_cert(label, cert_pem)`, mapeia `NOT_FOUND`→404 e `KEY_MISMATCH`→422, em sucesso insere em `certificates` com `source="hsm"` e `hsm_label=label` (coluna de T004), `log_activity(conn, "certificado_importado_hsm", f"{label} · {cn}", None, user["id"])`.
- [X] T014 [P] [US3] Testes de `POST /hsm/keys/{label}/certificate` em `tests/test_hsm_routes.py`: importação compatível (sucesso, `source="hsm"`) e incompatível (`422`).

**Checkpoint**: US1, US2, US3 cobrem o ciclo completo até certificado associado no HSM.

---

## Phase 6: User Story 4 - Exportar certificado e chave como PFX/P12 (Priority: P2)

**Goal**: administrador exporta o par certificado + chave privada de uma entrada do HSM em PFX/P12 protegido por senha.

**Independent Test**: exportar uma chave exportável com certificado associado retorna arquivo binário válido (abre com a senha do header); exportar uma chave não exportável retorna `403`.

- [X] T015 [US4] Implementar `GET /hsm/keys/{label}/export` em `app/routers/hsm.py`: query `format=pfx|p12`, gera senha via `app/services/passwordgen.py` usando `password_policy` (setting já existente, conforme `research.md` #4), chama `provider.export_pfx(label, password)`, mapeia `NOT_FOUND`→404 e `NOT_EXPORTABLE`→403, decodifica `pfx_base64` e devolve `Response(content=..., media_type="application/x-pkcs12", headers={"X-Export-Password": password})`, `log_activity(conn, "certificado_exportado_hsm", f"{label} · {format}", None, user["id"])` (sem logar a senha).
- [X] T016 [P] [US4] Testes de `GET /hsm/keys/{label}/export` em `tests/test_hsm_routes.py`: sucesso (resposta binária + header `X-Export-Password` presente) e chave não exportável (`403`).

**Checkpoint**: US1-US4 cobrem chave → CSR → certificado → PFX/P12 exportado.

---

## Phase 7: User Story 5 - Buscar chaves e certificados no HSM (Priority: P3)

**Goal**: administrador localiza chaves/certificados no HSM por rótulo ou CN.

**Independent Test**: buscar por rótulo/CN conhecido retorna os itens esperados; buscar termo inexistente retorna `200` com lista vazia (não erro).

- [X] T017 [US5] Implementar `GET /hsm/search` em `app/routers/hsm.py`: query `q`, chama `provider.search_objects(q)` (ação `search`), mapeia `CONN_FAILED`→502, devolve `{"results": [...]}` (lista vazia em `200` quando nada encontrado, conforme FR-010), formato de item por `contracts/hsm-rest-api.md`.
- [X] T018 [P] [US5] Testes de `GET /hsm/search` em `tests/test_hsm_routes.py`: resultados encontrados e busca sem resultados (`200`, `results: []`).

**Checkpoint**: todas as 5 user stories funcionais e testáveis independentemente.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: UI, configuração visível ao usuário e validação fim-a-fim.

- [ ] T019 [P] Adicionar seção "HSM (Dinamo)" na aba Configurações em `app/static/index.html` + `app/static/app.js` (campos host/porta/usuário/senha mapeados para a setting `hsm_dinamo_config`), reaproveitando o padrão visual já usado pela seção de templates do `hsmutil`.
- [ ] T020 [P] Adicionar UI de operações HSM em `app/static/app.js` + `app/static/index.html` + `app/static/styles.css` (criar chave, gerar CSR, importar certificado, exportar PFX/P12 com download, busca), consumindo os endpoints `/api/hsm/*` implementados em T009-T017.
- [ ] T021 Atualizar `README.md` (seção `## HSM (Dinamo Networks)`, linhas ~82-87): substituir a descrição "está planejada" pela descrição do provider `dinamo_js` implementado (bridge Node, endpoints `/api/hsm/*`, configuração em Configurações).
- [ ] T022 Rodar a validação de `quickstart.md` ponta a ponta contra um HSM Dinamo real (ou homologação), confirmando os 7 passos e o cenário de indisponibilidade.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências — pode começar imediatamente.
- **Foundational (Phase 2)**: depende do Setup — bloqueia todas as user stories.
- **User Stories (Phase 3-7)**: todas dependem do Foundational. US1→US2 têm dependência sequencial leve (US2 assume uma chave já criada por US1 para ser testada ponta-a-ponta, mas o código de US2 não depende do código de US1). US3, US4 e US5 são independentes entre si e de US2 no nível de código (todas usam apenas `DinamoJsProvider`, já pronto na Foundational).
- **Polish (Phase 8)**: depende de todas as user stories desejadas estarem completas (T019/T020 tocam os mesmos arquivos estáticos das 5 stories, então devem vir depois delas).

### User Story Dependencies

- **US1 (P1)**: após Foundational — sem dependência de outra story.
- **US2 (P1)**: após Foundational — código independente; teste de ponta-a-ponta mais realista assume uma chave criada via US1.
- **US3 (P2)**: após Foundational — independente.
- **US4 (P2)**: após Foundational — independente (teste de ponta-a-ponta realista assume um certificado importado via US3).
- **US5 (P3)**: após Foundational — totalmente independente (`search_objects` não depende de nenhuma outra operação ter sido feita pela aplicação, só do conteúdo já existente no HSM).

### Dentro de cada User Story

- Implementação do endpoint antes do teste correspondente ser considerado "verde" (mas o teste pode ser escrito em paralelo, arquivo `tests/test_hsm_routes.py` é compartilhado entre todas as stories — ver nota de paralelismo abaixo).

### Parallel Opportunities

- T001, T002, T003 (Setup) em paralelo — arquivos diferentes.
- T007 (Foundational, teste do provider) em paralelo com T008 (router-esqueleto) — arquivos diferentes; ambos dependem de T005+T006 já implementados.
- Dentro de cada user story, a tarefa de teste (`T010`, `T012`, `T014`, `T016`, `T018`) pode ser escrita em paralelo com a tarefa de implementação da story seguinte, mas **todas escrevem no mesmo arquivo** `tests/test_hsm_routes.py` — rodar em paralelo dentro da mesma story é seguro (blocos de teste diferentes), entre stories diferentes só se coordenado para evitar conflito de merge no mesmo arquivo.
- T019 e T020 em paralelo entre si não recomendado (ambos tocam `app/static/app.js`/`index.html`) — tratar como sequenciais apesar do marcador `[P]` indicar arquivos parcialmente sobrepostos; preferir T019 → T020.

---

## Parallel Example: User Story 1

```bash
# T009 (implementação) e T010 (teste) tocam arquivos diferentes — paralelizável:
Task: "Implementar POST /hsm/keys em app/routers/hsm.py"
Task: "Testes de POST /hsm/keys em tests/test_hsm_routes.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Completar Phase 1 (Setup) + Phase 2 (Foundational — bridge Node, provider, router-esqueleto, coluna `hsm_label`).
2. Completar Phase 3 (US1 — criar chave no HSM).
3. Validar US1 isoladamente (T010 + passo 2 do `quickstart.md`).
4. Já é um incremento demonstrável: administrador cria chaves reais no HSM pela aplicação.

### Incremental Delivery

1. Setup + Foundational → base pronta.
2. US1 (criar chave) → testar → demo.
3. US2 (gerar CSR) → testar → demo (fecha o caso de uso central: chave HSM → CSR).
4. US3 (importar certificado) → testar → demo.
5. US4 (exportar PFX/P12) → testar → demo.
6. US5 (busca) → testar → demo.
7. Polish (UI completa + README + validação real via quickstart).

---

## Notes

- `[P]` = arquivos diferentes, sem dependência de tarefa incompleta.
- `[Story]` mapeia a tarefa à user story correspondente (rastreabilidade com `spec.md`).
- Nenhuma story depende de código de outra story para funcionar — apenas os testes de ponta-a-ponta mais realistas assumem dados criados por uma story anterior (chave por US1, certificado por US3).
- Commitar após cada tarefa ou grupo lógico.
- `app/services/hsm/base.py` (interface `KeyProvider` usada por `local`/`hsmutil`) **não é alterada** — os métodos novos (`import_cert`, `export_pfx`, `search_objects`) existem só em `DinamoJsProvider`, pois só fazem sentido para um HSM real; evita forçar `LocalProvider`/`HsmUtilProvider` a implementar operações que não suportam.
