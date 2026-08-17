# Contract: Tokens CSS do Modo CAIXA

Este contrato descreve o comportamento observável (não a implementação linha a linha) que `app/static/styles.css` e `app/static/app.js` devem satisfazer.

## Gatilho

`document.documentElement.dataset.accent === "caixa"` (equivalente a `<html data-accent="caixa">`), setado por `applyAccent("caixa")` quando o usuário clica o swatch "caixa" na aba Aparência, ou restaurado no carregamento da página a partir de `localStorage.getItem("certhub-accent")`.

## Contrato de tokens

Dado `data-accent="caixa"` no `<html>`:

1. `--accent` DEVE resolver para `#0066B3` se `data-theme` for `"light"` (ou ausente), e para `#0097D7` se `data-theme="dark"`.
2. `--accent-soft` e `--accent-text` DEVEM resolver para os pares claro/escuro definidos em `data-model.md` (Tokens de destaque).
3. `--sidebar-bg` DEVE resolver para `#0066B3` **independente** do valor de `data-theme` (claro ou escuro) — este é o único conjunto de tokens desta feature que não varia por tema, ver `research.md` §4.
4. `--sidebar-text` DEVE resolver para `#FFFFFF` e `--sidebar-text-dim` para `rgba(255,255,255,.85)`, também independente de `data-theme`.
5. `--sidebar-border` DEVE resolver para `rgba(255,255,255,.18)`.
6. `--sidebar-hover-bg` DEVE resolver para `rgba(255,255,255,.12)`, também independente de `data-theme` (token adicionado após bug de contraste reportado em uso real — ver `research.md` §5c).
7. `--caixa-orange` DEVE resolver para `#F7941E`.

Dado `data-accent` com qualquer outro valor (ou ausente): todos os tokens acima DEVEM se comportar exatamente como hoje (sem regressão) — em particular `--sidebar-bg`/`--sidebar-text`/`--sidebar-text-dim`/`--sidebar-border`/`--sidebar-hover-bg`, que são tokens novos, DEVEM resolver para os valores atuais (`var(--bg-panel)`, `var(--text)`, `var(--text-dim)`, `var(--border)`, `var(--bg-hover)`) para que nenhuma tela existente mude visualmente.

## Contrato de consumo (onde os tokens são usados)

- `.sidebar` (regra `background`) DEVE consumir `var(--sidebar-bg)` em vez de `var(--bg-panel)` diretamente.
- `.sidebar` (regra `border-right`) e a variante `[data-layout="top"] .sidebar` (`border-bottom`) DEVEM consumir `var(--sidebar-border)` em vez de `var(--border)` diretamente.
- `.brand-name`, `.brand-sub`, `#nav a` (cor de texto/ícone dentro da sidebar) DEVEM consumir `var(--sidebar-text)` / `var(--sidebar-text-dim)` em vez de `var(--text)` / `var(--text-dim)` diretamente.
- `#nav a:hover` DEVE consumir `var(--sidebar-hover-bg)` em vez de `var(--bg-hover)` diretamente.
- `.sidebar-footer .btn-ghost` (botões de tema/logout/colapsar) DEVE consumir `var(--sidebar-text-dim)` (e `var(--sidebar-text)`/`var(--sidebar-hover-bg)` no `:hover`) sob `[data-accent="caixa"]`, em vez de herdar `var(--text-dim)` da regra genérica `.btn-ghost`.
- **Regra geral para qualquer elemento futuro dentro de `.sidebar`**: NUNCA usar `var(--text)`/`var(--text-dim)`/`var(--bg-hover)` diretamente — sempre os equivalentes `--sidebar-*`, porque a sidebar é a única superfície cuja cor de fundo não segue claro/escuro sob Modo CAIXA (ver `research.md` §4/§5c).
- `#nav a.active` continua consumindo `var(--accent-soft)`/`var(--accent-text)` (já é assim hoje) — sem mudança de regra, só o valor resolvido muda quando `data-accent="caixa"`.
- `--caixa-orange` é consumido apenas por seletores explicitamente marcados como "destaque neutro" (ex. uma classe `.badge-caixa-highlight`, a ser aplicada nos pontos identificados na fase de implementação) — NUNCA nos seletores que hoje usam `--green`/`--red`/--amber` para status semânticos.

## Não-regressão

- Nenhum dos 36 usos existentes de `var(--accent...)` em `styles.css` deve ser removido ou ter sua lógica alterada — só o range de valores possíveis cresce (mais uma opção de cor).
- As 5 opções de destaque existentes (`green`/`purple`/`teal`/`amber`/`red`) e a opção `blue` (default) continuam funcionando byte-a-byte como hoje.
