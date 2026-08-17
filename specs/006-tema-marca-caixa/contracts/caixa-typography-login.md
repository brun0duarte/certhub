# Contract: Tipografia, cor de título/botão e Modo CAIXA em `login.html`

## 1. Tipografia (`--font-caixa`)

Dado `data-accent="caixa"` no `<html>`:

1. `--font-caixa` DEVE resolver para `"Poppins", "Segoe UI", system-ui, sans-serif`.
2. `.brand-name`, `.view-title` e `.panel h3` DEVEM consumir `font-family: var(--font-caixa)`.
3. `body` (e, por herança, qualquer elemento que não declare `font-family` própria) NÃO MUDA — continua `"Segoe UI", system-ui, -apple-system, sans-serif` em qualquer tema, inclusive CAIXA.
4. `styles.css` DEVE carregar a fonte via `@import url(...)` do Google Fonts, no topo do arquivo, antes de qualquer regra de token — carregamento é incondicional (não dentro de `[data-accent="caixa"]`), mas o `font-family` só é *aplicado* sob esse seletor; isso é aceitável porque o `@import` sozinho não renderiza nada, só disponibiliza a fonte.

Dado `data-accent` diferente de `"caixa"`: `.brand-name`/`.view-title`/`.panel h3` continuam com a `font-family` herdada de `body` (sem mudança).

## 2. Cor de título de página

Dado `data-accent="caixa"`:

1. `.view-title` DEVE consumir `color: var(--accent-text)` — resolve para `#00508C` no tema claro e `#4DB8E8` no escuro (mesmos valores já usados em outros elementos, `data-model.md`).

Dado `data-accent` diferente: `.view-title` continua sem `color` declarado (herda `--text` neutro, comportamento atual).

## 3. Botão primário — revalidação de contraste

1. `.btn-primary` continua com texto `#fff` sobre `background: var(--accent)`.
2. Contraste DEVE ser validado (fórmula WCAG) para as duas variantes de `--accent` sob Modo CAIXA: `#0066B3` (claro) e `#0097D7` (escuro). Se a razão calculada for `< 4.5:1`, o texto do botão sob Modo CAIXA DEVE usar uma cor diferente de `#fff` (token novo, ex. `--caixa-btn-text`) só nesse contexto — branco genérico não é assumido como seguro sem cálculo.
3. Esse cálculo e o valor final resultante DEVEM ser registrados em `research.md` (mesmo padrão já usado para os outros pares de contraste desta feature).

## 4. `login.html` reflete o Modo CAIXA

1. `login.html` DEVE incluir `<script src="/static/icons.js"></script>` antes de qualquer script inline que dependa de `CAIXA_X_ICON`/`DEFAULT_FAVICON_HREF`/`CAIXA_FAVICON_HREF`.
2. Um script inline no `<head>`, executado antes do primeiro paint, DEVE setar `document.documentElement.dataset.accent = localStorage.getItem('certhub-accent') || 'blue'` — sem tocar em `certhub-theme` (que continua hardcoded `data-theme="dark"` em `login.html`, comportamento pré-existente fora de escopo).
3. Se `data-accent === "caixa"` após o DOM montar: `.brand-header h1` DEVE trocar seu conteúdo (hoje `🔐 CertHub`) para usar `CAIXA_X_ICON` no lugar do emoji, mantendo o texto "CertHub".
4. `login.html` DEVE ganhar um `<link rel="icon">` (hoje ausente) cujo `href` é definido dinamicamente pelo mesmo script: `DEFAULT_FAVICON_HREF` por padrão, `CAIXA_FAVICON_HREF` se `data-accent === "caixa"`.
5. Se `certhub-accent` nunca foi salvo neste navegador (`localStorage.getItem` retorna `null`): comportamento default é `"blue"` — tela de login aparece exatamente como hoje, sem nenhuma mudança visual.

## 5. Favicon dinâmico em `index.html`

1. O favicon hoje hardcoded em `index.html:9` (`<link rel="icon" href="data:image/svg+xml,...🔐...">`) DEVE ser substituído por `DEFAULT_FAVICON_HREF` (mesmo conteúdo, agora vindo de `icons.js`) como valor inicial.
2. `applyAccent(a)` (`app.js`) DEVE, além do que já faz hoje (trocar `.brand-icon`, persistir em `localStorage`), também setar `document.querySelector('link[rel="icon"]').href` para `CAIXA_FAVICON_HREF` quando `a === "caixa"`, e para `DEFAULT_FAVICON_HREF` caso contrário.
3. Limitação aceita (não é bug a corrigir nesta feature): navegadores podem cachear favicon entre navegações/reloads — a troca reflete de forma best-effort, sem cache-busting adicional.

## Não-regressão

- Fora do Modo CAIXA, `.view-title`, `.brand-name`, `.panel h3`, `.btn-primary` e o favicon continuam byte-a-byte como estão hoje.
- `login.html` sem `certhub-accent` salvo (usuário nunca usou este navegador) aparece exatamente como antes desta feature.
