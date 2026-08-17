# Contract: Troca de emoji por ícone de linha (`applyIconSkin`)

## Gatilho

Mesmo das outras stories: `document.documentElement.dataset.accent === "caixa"`. `applyIconSkin(root)` pode ser chamada sempre (após qualquer render), mas só produz efeito quando essa condição é verdadeira — caso contrário retorna imediatamente sem tocar `root`.

## Contrato de comportamento

1. `applyIconSkin(root)` (definida em `app/static/icons.js`) recebe um elemento DOM (`root`) e:
   - Se `data-accent !== "caixa"`: retorna sem nenhuma mutação.
   - Se `data-accent === "caixa"`: percorre `root.querySelectorAll(ICON_SKIN_SELECTORS)`, onde `ICON_SKIN_SELECTORS = ".btn, .badge, .view-title, .tab-btn, .rtab-btn, .subtab-btn, .opt-icon, .wizard-step, .stat-label"` (`.opt-icon`, não `.app-opt` — o emoji está no `<div class="opt-icon">`, filho de `.app-opt`, não em `.app-opt` diretamente; usar `.app-opt` faria o código casar contra o texto do rótulo ao lado, ex. "Claro"/"Escuro", não contra o emoji). Para cada elemento encontrado, localiza o **primeiro nó de texto filho direto não-vazio**, verifica se o texto começa com algum emoji presente em `EMOJI_ICONS`; se sim, remove o emoji do texto e insere o SVG correspondente (`insertAdjacentHTML("afterbegin", ...)`) no início do elemento.
2. `applyIconSkin` é chamada em exatamente 2 chokepoints do SPA, mais ~10 pontos de sub-render:
   - Ao final de `navigate()` (`app.js`, logo após `await view()` popular `main.innerHTML`), chamada como `applyIconSkin(main)`.
   - Ao final de `modal(...)` (`app.js`, logo após `root.innerHTML` ser setado), chamada como `applyIconSkin(root)`.
   - Em cada uma das ~10 funções de sub-render identificadas em `research.md` §7 (`renderList`, `renderSearchResults`, `renderActiveProfileInfo`, `renderHsmProfiles`, `renderResult`, `renderCsrResult`, `renderLocConfigFields`, atualizações de badge via `data-loc-automation-badge`), chamada com o container que a função acabou de popular.
3. `NAV_ICONS` é aplicado separadamente, **não** via `applyIconSkin`: uma função dedicada percorre os 18 `<a data-view>` de `#nav` (uma vez, não a cada navegação — o nav não é re-renderizado por `navigate()`) e troca o ícone de cada item conforme `NAV_ICONS[a.dataset.view]`, chamada em `applyAccent(a)` quando `a === "caixa"` (e revertida quando `a !== "caixa"`).

## Contrato de exclusão (NUNCA tocado, em nenhuma circunstância)

- Conteúdo produzido por `toast(...)` — qualquer notificação temporária.
- `.user-name` e qualquer elemento que renderize `display_name`/`username`/dado de conta.
- Células de tabela com dado de domínio (CN, SAN, nomes de certificado/CA/local), mesmo que comecem com um caractere presente em `EMOJI_ICONS`.
- Qualquer elemento fora do seletor fixo `ICON_SKIN_SELECTORS` listado acima — a função nunca varre `document` inteiro nem usa `MutationObserver`.

Isso é validado pela ausência estrutural: `.toast`, `.user-name` e células de tabela de dados não pertencem a `ICON_SKIN_SELECTORS`, então mesmo com Modo CAIXA ativo, `applyIconSkin` nunca os visita.

## Contrato de reversão

Não existe uma função "desfazer troca de ícone". Ao sair do Modo CAIXA (escolher outro `data-accent`), o próximo `navigate()` (troca de view) já reconstrói `main.innerHTML` do zero (comportamento pré-existente do SPA — ver comentário em `app.js:316-318`) e `applyIconSkin` já retorna sem agir na condição `data-accent !== "caixa"`, então o emoji original aparece naturalmente no próximo render. Elementos que não passam por um novo `navigate()` (ex. o usuário troca de accent sem sair da view atual) podem manter o ícone SVG até a próxima navegação — comportamento aceito, documentado como limitação conhecida, não como bug (a store de nav/`.brand-icon` é revertida imediatamente por serem tratadas fora do `applyIconSkin`, ver `caixa-brand-icon.md`).

## Não-regressão

- Fora do Modo CAIXA, `ICON_SKIN_SELECTORS` nunca é varrido — nenhum emoji muda em nenhuma tela, em nenhuma circunstância, para nenhum outro valor de `data-accent`.
- `applyIconSkin` nunca lança exceção se `EMOJI_ICONS` não tiver uma entrada para o emoji encontrado — nesse caso, o elemento é deixado como está (fallback seguro).
