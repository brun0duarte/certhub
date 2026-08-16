# Research: Ajustes de Layout do HSM e Preservação de Estado entre Abas

## 1. Sobreposição do painel "Criar chave" (US1)

**Decision**: A causa raiz não é diferença de altura entre os dois painéis do `grid-2` (o CSS Grid já estica ambos `.panel` filhos pra mesma altura por padrão — `align-items: stretch` implícito). A causa é a ausência de espaçamento entre o container `.grid.grid-2` (que envolve "Criar chave" + "Importar certificado emitido") e o painel seguinte ("📝 Gerar CSR a partir de uma chave do HSM"): a regra `.panel + .panel { margin-top: 16px }` (`styles.css:121`) só se aplica entre dois `.panel` **irmãos diretos consecutivos** — como o elemento entre eles é `.grid.grid-2` (não tem classe `.panel`), a cadeia de seletor adjacente quebra, e o painel "Gerar CSR" não recebe `margin-top`. Resultado: o painel seguinte encosta direto na borda inferior do `grid-2`, lido visualmente como "o painel de cima é maior/sobrepõe".

**Rationale**: Fix mínimo e local — adicionar uma regra específica pro container `.grid-2` seguido de `.panel`, sem alterar a regra geral `.panel + .panel` (que já funciona corretamente em todas as outras abas do sistema) e sem risco de regressão em outras telas que usam `.grid.grid-2` (Decoder, Certificados, Validar cadeia) — o mesmo espaçamento passa a valer ali também, o que é desejável (mesmo bug potencial, só não relatado ainda).

**Alternatives considered**:
- Reduzir conteúdo do painel "Criar chave" pra ficar visualmente menor: rejeitado — não é a causa raiz, e reduzir campos tiraria funcionalidade.
- Tirar o `grid-2` e empilhar os painéis verticalmente: rejeitado — muda o layout de forma desnecessária; o problema é só o espaçamento entre o grid e o painel seguinte, não o grid em si.
- Adicionar `margin-bottom` ao invés de `margin-top`: equivalente, mas `margin-top` no elemento seguinte segue o mesmo padrão já usado por `.panel + .panel` no resto do sistema.

**Verificação pendente**: sem acesso a navegador nesta sessão pra confirmar visualmente antes da implementação — o fix deve ser validado com captura de tela real na aba HSM (1440/1024/768px) assim que houver acesso, conforme `quickstart.md`.

## 2. Exibir perfil de HSM ativo (nome, host, usuário) no topo da aba (US2)

**Decision**: Estender a resposta de `GET /hsm/profiles` (`app/routers/hsm.py`) pra incluir `host` e `username` de cada perfil (mantendo `password` sempre omitida) — hoje o endpoint só retorna `{"name": "..."}` por perfil, criado assim intencionalmente porque a única necessidade anterior (specs/002) era popular um seletor de troca rápida. Adicionar um bloco de texto (não outro `<select>`) próximo ao seletor de perfil já existente, mostrando `"{name} · {host} · {username}"` do perfil atualmente ativo, atualizado a cada troca de perfil.

**Rationale**: `host`/`username` não são segredo (diferente de `password`, que nunca sai do backend em nenhum endpoint) — expor os dois no frontend é seguro e resolve diretamente o requisito. Reaproveita a mesma chamada `GET /hsm/profiles` já feita por `views.hsm` (specs/002) pra montar o seletor — sem chamada de API adicional.

**Alternatives considered**:
- Criar um endpoint novo só pra essa informação: rejeitado — `GET /hsm/profiles` já é chamado nessa view e já tem o formato certo de resposta, só falta 2 campos.
- Mostrar só o nome do perfil (sem host/usuário): rejeitado — não atende ao pedido explícito do usuário ("PRD · host · user"), que é justamente pra evitar confundir dois HSMs com o mesmo nome de ambiente mas configuração diferente.

## 3. Preservar estado de formulário/filtro/paginação entre trocas de aba (US3)

**Decision**: Introduzir um armazenamento em memória, `viewState = {}` (objeto JS simples, vive só durante a sessão da página — nunca gravado em `localStorage`/`sessionStorage`), com uma função `getViewState(name, defaults)` que retorna (criando se necessário) o objeto de estado da aba `name`. Cada view que hoje usa variáveis locais (`let page = 1`, `let sortKey = ...`) e inputs sem estado persistente passa a ler/gravar nesse objeto compartilhado em vez de variáveis locais do closure — como o objeto vive fora da função `view()`, ele sobrevive a `navigate()` recriar `main.innerHTML` e trocar de função de view.

**Rationale**: O roteador atual (`app/static/app.js:305-316`) é uma SPA minimalista sem framework — cada `views.<nome>()` reconstrói `main.innerHTML` do zero a cada navegação, e todo estado local (variáveis `let`, valores de input) é perdido nesse processo porque o closure da função anterior não é mais referenciado. Um objeto de estado por-nome-de-view, mantido no escopo do módulo (fora de qualquer função `views.*`), é a menor mudança estrutural possível que resolve o requisito sem introduzir um framework de estado (Redux-like) ou reescrever o roteador — consistente com o estilo "vanilla JS direto" já usado em todo `app.js`.

**Escopo de aplicação**: views com filtro/busca/paginação (`geracao`, `instalacao`, `historico`, `monitor`, e outras listas paginadas equivalentes) e views com formulário de múltiplos campos ainda não enviados (`csr`, `hsm`, `decoder` — campos de entrada, não o resultado exibido). Views sem estado relevante (ex.: `dashboard`, `docs`) não precisam de mudança. O mapeamento exato view→campos fica em `data-model.md`.

**Persistência de senha (FR-007)**: campos de senha (ex.: senha de perfil de HSM em Configurações) entram no mesmo objeto de estado em memória — isso já satisfaz "não gravar em armazenamento persistente do navegador", já que `viewState` é uma variável JS comum, nunca serializada para `localStorage`/cookies. Nenhum tratamento especial adicional é necessário além de não usar `localStorage.setItem` em lugar nenhum dessa implementação.

**Alternatives considered**:
- `sessionStorage`: rejeitado — sobrevive a F5 (fora do escopo pedido) e gravaria senhas em texto puro no disco/storage do navegador, o que o usuário não pediu e é um risco desnecessário dado que o requisito explícito é "só troca de aba, não precisa sobreviver a F5".
- Manter os elementos DOM das views antigas escondidos (`display:none`) em vez de recriar `innerHTML`: rejeitado — mudança muito maior no roteador (cada view viraria um "componente" persistente), risco alto de regressão em todas as ~17 views existentes, desproporcional ao pedido.
- Estado por view usando `Map` em vez de objeto simples: equivalente; objeto simples (`{}`) é mais consistente com o estilo já usado no restante do arquivo (nenhum outro lugar usa `Map`).

## Resumo (Technical Context)

- Sem novas dependências — tudo em JS vanilla (frontend) e FastAPI/pydantic (backend), consistente com specs/001 e specs/002.
- Sem migração de schema SQL nem novo endpoint — só CSS (US1), campo extra na resposta de `GET /hsm/profiles` já existente (US2), e uma mudança estrutural interna no frontend (`viewState`) sem contrato de API novo (US3).
