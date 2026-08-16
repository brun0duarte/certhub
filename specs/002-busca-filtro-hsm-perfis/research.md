# Research: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

## 1. Seletor de demanda com busca (US1)

**Decision**: Substituir os `<select><option>` estáticos que listam todas as REQs (`app.js`: geração de CSR L.1854-1855, decoder L.2089, CSR via HSM L.2523, referência de credencial de local de instalação L.1276, avanço para instalação L.2396) por um componente combobox reutilizável: `<input type="text">` com uma lista de sugestões filtrada em tempo real (`datalist`-like custom dropdown, já que `<datalist>` nativo tem suporte inconsistente de estilização e de exibição de mais de um campo por item como "REQ0012345 · CN (env)").

**Rationale**: Todas as telas já carregam a lista completa de REQs abertas via `GET /reqs` antes de montar o formulário (ex.: `const { items: reqs } = await api("/reqs")` em `views.hsm`). O problema é puramente de apresentação — não há necessidade de busca no servidor. Um componente client-side filtra por substring em `req_number` e `cn`, reaproveitando o array já em memória, sem round-trip adicional e sem mudança de contrato de API.

**Alternatives considered**:
- `<datalist>` nativo do HTML: rejeitado — não permite estilizar a lista de sugestões no tema da aplicação, some sem interação de teclado consistente entre navegadores, e mistura mal com o padrão visual `.input` já usado.
- Busca no servidor (`GET /reqs?search=...`) a cada tecla digitada: rejeitado — adiciona latência de rede e complexidade (debounce, cancelamento de requisição) para um conjunto de dados que já está inteiramente carregado na tela; útil só se o volume de REQs abertas crescesse para dezenas de milhares, o que foge do escopo atual (SC-001 assume centenas).
- Reescrever cada tela individualmente: rejeitado — os 5 pontos de uso têm o mesmo formato de opção (`req_number · cn (env)`) e o mesmo comportamento esperado; um helper único (`reqPicker(containerEl, reqs, opts)`) evita duplicação e garante consistência (FR-003).

## 2. Ordenação/filtro em Geração e Instalação (US2)

**Decision**: Estender `GET /reqs` (`app/routers/reqs.py:98`) com os mesmos parâmetros `sort`/`dir` já usados em `GET /monitor/expiring` (`app/routers/monitor.py:8-22`), usando uma tabela `SORT_COLUMNS` própria mapeando nomes de ordenação aceitos pelo frontend para colunas SQL válidas (evita SQL injection via `ORDER BY` dinâmico).

**Rationale**: `list_reqs` já filtra por `search`, `env`, `status`, `demand_type`, `exclude_status` — falta apenas ordenação, hoje fixa em `ORDER BY r.created_at DESC`. Replicar o padrão de `SORT_COLUMNS` do Monitor mantém consistência de implementação entre os três endpoints e evita interpolar a coluna de ordenação diretamente a partir da entrada do usuário.

**Alternatives considered**:
- Ordenação client-side (frontend ordena o array já recebido): rejeitado para paridade com Monitor — Monitor pagina no servidor (`LIMIT`/`OFFSET`), então ordenar só a página atual no cliente produziria resultado incorreto ao paginar. Ordenar no servidor mantém o comportamento correto independente de paginação futura.
- Adicionar `ORDER BY` livre (aceitar nome de coluna arbitrário do cliente): rejeitado — risco de SQL injection e de expor nomes de coluna internos.

## 3. Layout quebrado da aba HSM (US3)

**Decision**: Alinhar o painel "🔎 Buscar no HSM" ao padrão já usado no resto do sistema — trocar o `<div style="display:flex;gap:8px">` ad-hoc (único ponto da aba HSM sem usar as classes utilitárias) por `.form-row` com o input dentro de um `.field` com `label`, igual aos demais painéis da mesma aba (`h3.form-row`, `.field`).

**Rationale**: Inspeção de `app.js` (views.hsm, L.2456-2536) e `styles.css` (`.panel`, `.grid-2`, `.form-row`, `.field`, L.117-209) mostra que todos os outros campos da aba HSM já seguem `.field`/`.form-row`; o painel de busca é o único que usa estilo inline solto, sem `label` acima do botão e sem o espaçamento vertical de `.field { margin-bottom: 13px }` — essa é a causa concreta do desalinhamento relatado.

**Alternatives considered**:
- Reescrever CSS global do `.panel`/`.grid`: rejeitado — os demais painéis já renderizam corretamente; o problema é local a um trecho específico, não uma regressão de CSS global.

## 4. Perfis de HSM nomeados e alternáveis (US4)

**Decision**: Substituir a configuração única `hsm_dinamo_config` (setting `{"host","port","username","password"}`) por uma nova configuração `hsm_dinamo_profiles`: `{"active": "string", "profiles": [{"name","host","port","username","password"}, ...]}`, guardada como JSON na mesma tabela `settings` (mesmo padrão de `hsmutil_templates`). Migração automática: na primeira leitura após o deploy, se `hsm_dinamo_profiles` estiver vazio e o `hsm_dinamo_config` legado tiver algum campo preenchido, gera um profile `"Padrão"` a partir dele e marca como ativo (FR-013).

**Rationale**: Mantém o mesmo mecanismo de armazenamento (`settings` key/value, JSON validado em `PUT /settings`) já usado para toda configuração da aplicação — sem introduzir tabela nova nem migração de schema SQL. `_provider()` em `app/routers/hsm.py:21-23` passa a resolver a conexão a partir do profile ativo em vez do objeto único.

**Alternatives considered**:
- Tabela SQL dedicada (`hsm_profiles`): rejeitado — todo o resto da configuração da aplicação (incluindo a config HSM atual) já vive em `settings` como JSON; criar uma tabela só para isso quebra o padrão existente sem ganho, já que não há necessidade de query relacional sobre profiles.
- Um `hsm_dinamo_config` por variável de ambiente/arquivo `.env`: rejeitado — o app já centraliza toda configuração editável em runtime via UI de Configurações; mover para env quebraria a possibilidade de alternar perfil sem reiniciar o processo (SC-005 exige troca em segundos, sem redeploy).
- Alternância "por operação" (escolher perfil a cada ação na aba HSM): rejeitado — não é o que o usuário pediu ("alternar mais fácil" entre dois ambientes de uso contínuo) e complicaria a UI sem necessidade; assumido em `spec.md` como alternância global de perfil ativo.

## Resumo das decisões técnicas (Technical Context)

- Sem novas dependências de biblioteca — tudo reaproveita FastAPI/pydantic (backend) e o JS vanilla já usado em `app/static/app.js` (frontend), consistente com o restante do projeto.
- Sem migração de schema SQL — mudanças em `GET /reqs` (parâmetros de query) e em `settings` (novo formato de JSON em `hsm_dinamo_profiles`), ambos já são mecanismos existentes.
- Sem novos testes de integração externos — cobertura via `pytest` nos endpoints (`tests/test_hsm_routes.py`, novo `tests/test_reqs_lifecycle.py` ou similar para os parâmetros `sort`/`dir`).
