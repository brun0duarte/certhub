# Contract: Armazenamento de estado por view (US3)

Contrato interno de frontend — não é uma API de rede. Define a interface que toda view coberta (ver `data-model.md`) usa pra ler/gravar seu estado em `app/static/app.js`, garantindo que o mesmo padrão seja aplicado de forma consistente nas ~10 views afetadas.

## Interface

```js
// Objeto de módulo, criado uma vez, fora de qualquer função views.*
const viewState = {};

// Retorna o estado da view `name`, criando com `defaults` na primeira chamada.
// Chamadas seguintes retornam a MESMA referência de objeto (mutável).
function getViewState(name, defaults) {
  if (!viewState[name]) viewState[name] = { ...defaults };
  return viewState[name];
}
```

## Convenção de uso em cada `views.<nome>`

1. No início da função da view, obter o estado: `const state = getViewState("geracao", { search: "", env: "", status: "", page: 1, sortKey: "created_at", sortDir: "desc" });`
2. Ao montar o HTML inicial, usar `state.<campo>` como `value`/`selected` dos inputs/selects (em vez de string vazia fixa).
3. Em todo handler de evento que hoje só lia o valor do DOM (ex.: `$("#g-search").oninput`), também gravar no estado: `state.search = $("#g-search").value;` antes ou junto de disparar a busca/render.
4. Variáveis locais que hoje guardavam `page`/`sortKey`/`sortDir` (`let page = 1`) são substituídas por leitura/escrita direta em `state.page`/`state.sortKey`/`state.sortDir`.

## Regras

- `viewState` nunca é serializado (sem `JSON.stringify` pra `localStorage`/`sessionStorage`/cookie) — mora só na memória do processo do navegador, perdido em F5 (FR-007).
- Campos de arquivo (`<input type="file">`) nunca entram em `state` — não há como reatribuir um `FileList` programaticamente; a view lida com isso não tentando restaurar esse campo específico.
- Resultado de ações concluídas (áreas como `#h-csr-result`, `#dc-result`, `#c-result`) não fazem parte de `state` — só campos de entrada ainda não enviados (FR-011).
- Views sem filtro/formulário relevante (`dashboard`, `docs`, `appearance`, etc.) não chamam `getViewState` — nada muda nelas.
