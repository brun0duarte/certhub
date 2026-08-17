# Phase 0 Research: Tema Institucional CAIXA

## Parte A — decisões da v1 (US1-3, já implementadas em T001-T013, sem mudança)

### 1. Mecanismo de ativação/persistência

**Decision**: Tratar "Modo CAIXA" como um 7º valor (`"caixa"`) no array `ACCENTS` já existente em `app/static/app.js` (hoje: blue/green/purple/teal/amber/red), reaproveitando `data-accent` no `<html>` e a chave `localStorage.certhub-accent`.

**Rationale**: O picker de "Cor de destaque" já é uma escolha única (single-select) persistida. Ativar/desativar o Modo CAIXA é só trocar o valor selecionado — zero estado novo.

### 2. Cores institucionais (fonte: `manual-de-identidade-visual-caixa.pdf`, seções 1.1.3 e 1.2.1)

| Uso | Cor | CMYK (manual) | RGB/HEX (manual) |
|---|---|---|---|
| Azul CAIXA (base) | Pantone 287C | C100 M60 Y0 K0 | R0 G102 B179 → `#0066B3` |
| Laranja CAIXA | Pantone 151C | C0 M50 Y100 K0 | R247 G148 B30 → `#F7941E` |
| Azul CAIXA (extremo claro do gradiente "volume") | — | C85 M20 Y0 K0 | R0 G151 B215 → `#0097D7` |

`#0066B3` é a base institucional (`--accent` claro); `#0097D7` (extremo claro do gradiente oficial do manual) é usado como `--accent` no escuro — ancorado no manual, não uma derivação arbitrária.

### 3. Tokens que o manual não cobre (soft/text)

Claro: `--accent-soft: #D9E8F4`, `--accent-text: #00508C`. Escuro: `--accent-soft: #0F2A42`, `--accent-text: #4DB8E8`. Segue o mesmo padrão de derivação das 5 paletas de destaque já existentes.

### 4. Fundo da sidebar (identidade fixa, independente de claro/escuro)

`--sidebar-bg: #0066B3` com texto branco em **ambos** os temas do app — o manual (seção 1.1.4) trata qualquer fundo azul CAIXA como "fundo escuro", exigindo a versão negativa/branca da marca, independente do dark mode do app.

### 5. Elemento-síntese "X": SVG inline

Dois paralelogramos sobrepostos (`viewBox="0 0 100 100"`, `#0066B3`/`#F7941E` fixos), sem `currentColor`. Substitui `.brand-icon` via JS quando `data-accent === "caixa"`. Nesta revisão, a constante **muda de arquivo**: sai de `app.js` e vai para `app/static/icons.js` (novo, ver §8), para ficar junto do resto do conjunto de ícones de marca.

### 5b. Contraste com o `--sidebar-bg` azul (WCAG AA) — valores finais já implementados

- Branco `#FFFFFF` sobre `#0066B3`: **5.91:1** — passa AA.
- `--sidebar-text-dim`: ajustado de `rgba(255,255,255,.72)` (3.83:1, reprovado) para `rgba(255,255,255,.85)` (**4.63:1**, aprovado).
- `--caixa-orange-text` sobre `--caixa-orange-soft`: ajustado de `#C67618` (3.10:1, reprovado) para `#945812` (**5.08:1**, aprovado).
- `--accent-text` sobre `--accent-soft`, claro e escuro: 6.65:1 e 6.53:1 — aprovado sem ajuste.

### 5c. Bug de contraste encontrado em uso real (reportado pelo usuário após T001-T032) e corrigido

Ao testar a implementação de verdade, ficou claro que **T004/T006 migraram `.brand-name`/`.brand-sub`/`#nav a` para os tokens `--sidebar-text(-dim)`, mas deixaram de fora outros elementos que também ficam sentados diretamente sobre `--sidebar-bg`**:

- `.btn-ghost` (classe dos 3 botões do rodapé da sidebar — tema/logout/colapsar) usa `color: var(--text-dim)` (`styles.css:238`), não `var(--sidebar-text-dim)`. Medido: `--text-dim` (tema claro, `#66718a`) sobre `--sidebar-bg` (`#0066B3`) = **1.21:1** — praticamente ilegível. No tema escuro, `--text-dim` (`#8b94a8`) sobre o mesmo azul = **1.94:1** — também reprovado.
- `#nav a:hover` usava `background: var(--bg-hover)` (cinza quase branco no tema claro, `#f0f3f9`) com `color: var(--sidebar-text)` (branco) — branco sobre cinza-quase-branco no hover, contraste próximo de 1:1.

**Fix**: novo token `--sidebar-hover-bg` (mesmo padrão indireto de `--sidebar-bg`/`--sidebar-text`: passa por `var(--bg-hover)` fora do Modo CAIXA, vira `rgba(255,255,255,.12)` sob `[data-accent="caixa"]` — branco sobre esse overlay translúcido no azul dá **4.70:1**, aprovado). `#nav a:hover` passou a consumir `var(--sidebar-hover-bg)` em vez de `var(--bg-hover)` diretamente. `.btn-ghost` ganhou override escopado `[data-accent="caixa"] .sidebar-footer .btn-ghost { color: var(--sidebar-text-dim); }` (mesmo `rgba(255,255,255,.85)` já validado em 5b, 4.63:1) e hover correspondente usando `--sidebar-text`/`--sidebar-hover-bg`.

**Lição para revisões futuras**: qualquer elemento novo que fique dentro de `.sidebar` precisa ser auditado contra `--sidebar-bg`/`--sidebar-hover-bg`, não contra `--bg`/`--bg-hover` — a sidebar é a única superfície da interface cuja cor de fundo não segue o tema claro/escuro padrão (ver §4), então os tokens genéricos de texto/hover do resto do app não são seguros lá dentro.

### 6. Laranja institucional (`--caixa-orange`)

Token único `#F7941E`, usado só em `.badge.k-cat` (destaque neutro não-semântico) sob Modo CAIXA — nunca sobrescreve `--green`/`--red`/`--amber`.

---

## Parte B — decisões da expansão (US4-US7, escopo revisado)

Baseadas em leitura direta do código atual: `app/static/app.js` (4039 linhas), `app/static/styles.css` (582 linhas), `app/static/login.html`, `app/static/index.html`, e em 2 agentes de levantamento (inventário de emoji + footprint de cor/tipografia) rodados nesta sessão.

### 7. Mecanismo de troca de ícone

**Levantamento**: ~198 ocorrências de emoji-ícone / ~61 emojis distintos em `app.js` (155 linhas) + `index.html` (23 linhas) + `login.html` (1 linha). Categorias: marca (2), nav lateral (18 itens), toggle tema/layout (~7), títulos de view (~8+), botões de ação (~25-30), badges/status (~20-25), opções da aba Aparência (3+), toasts/decorativos/texto livre (~30+). Nenhum sistema de ícone/SVG existia antes desta feature.

**Descoberta chave**: o SPA já tem exatamente 2 chokepoints de render:
- `navigate()` (`app.js:325-330`) — único ponto que popula `#main` (`main.innerHTML = ...; try { await view(); }`) a cada troca de view. Comentário no próprio código (`app.js:316-318`) confirma: "SPA reconstrói main.innerHTML do zero a cada navegação".
- `modal(title, bodyHtml, ...)` (`app.js:141-153`) — único ponto que popula `#modal-root` para todo modal.

Fora desses dois, ~10 funções fazem `.innerHTML =` diretamente por conta própria (chamadas por `oninput`/`onclick`, não por `navigate()`/`modal()` de novo): `renderList`, `renderSearchResults`, `renderActiveProfileInfo`, `renderHsmProfiles`, `renderResult`/`renderCsrResult`, `renderLocConfigFields`, badges atualizados via `data-loc-automation-badge`.

**Decision**: hookar os 2 chokepoints + instrumentar as ~10 funções de sub-render com uma chamada a `applyIconSkin(container)`. **Não** editar os ~198 call sites individualmente, **não** usar `MutationObserver` irrestrito no documento inteiro.

**Rationale (por que não as alternativas)**:
- Editar 198 pontos espalhados em 4000+ linhas: risco alto de esquecer casos, diff enorme e difícil de revisar, sem ganho sobre a abordagem de chokepoint.
- `MutationObserver` global: evidência real no código mostra por que é perigoso sem escopo — `toast(\`✅ Certificado ${cert.cn} importado no HSM\`)` (`app.js:2796`) e `toast(\`⚠️ ATENÇÃO: O certificado ${cert.cn} NÃO corresponde...\`)` (`app.js:2859`) misturam emoji-prefixo com dado dinâmico no mesmo nó de texto — um scanner genérico correria o risco de reprocessar/corromper strings que mudam a cada render. `<span class="user-name">${esc(me.display_name||me.username)}</span>` (`app.js:4021`) é texto livre de usuário, nunca deve ser tocado.

**Decisão de escopo (FR-012)**: toasts e texto livre (nomes de usuário, valores de CN/SAN em tabela) **permanecem emoji sempre, mesmo sob Modo CAIXA** — não fazem parte de nenhuma categoria de "ícone de interface fixo".

**Implementação de `applyIconSkin`**: percorre um seletor fixo dentro do container passado (`.btn, .badge, .view-title, .tab-btn, .rtab-btn, .subtab-btn, .opt-icon, .wizard-step, .stat-label` — `.opt-icon`, não `.app-opt`: o emoji fica no `<div class="opt-icon">` interno, casar contra `.app-opt` pegaria o texto do rótulo ao lado em vez do emoji), casa **só o primeiro nó de texto** de cada elemento contra o mapa `EMOJI_ICONS`, substitui apenas o emoji líder por SVG. Roda incondicionalmente mas só age quando `document.documentElement.dataset.accent === "caixa"` — sai de imediato caso contrário, então nenhum custo extra fora do Modo CAIXA.

**Nav lateral e ícones de marca — implementados fora de `applyIconSkin`, sem corte pendente**: `NAV_ICONS` (18/18 itens, `data-view` mapeado 1:1) é aplicado dentro de `applyAccent()`, com reversão via `NAV_DEFAULT_ICONS` (snapshot do emoji original, capturado uma vez no boot). Os 3 botões de `.sidebar-footer` (`theme-toggle`/`btn-logout`/`menu-collapse`) ficaram fora do escopo implementado — seu conteúdo é regenerado por `applyTheme()`/`applyLayout()`, não por `applyAccent()`; tocar neles exigiria alterar essas duas funções também. SC-006 (spec) só exige os 18 itens de nav, então esse corte não compromete nenhum critério de sucesso.

**Nav lateral e sidebar-footer**: em vez da heurística de texto, usam um mapa determinístico por `data-view`/id (`NAV_ICONS`) — a estrutura desses 18 itens + 3 botões é fixa e conhecida, não precisa de heurística.

**Reversão ao sair do Modo CAIXA**: não precisa de lógica de "desfazer" — toda troca de view/modal já reconstrói `innerHTML` do zero (comportamento pré-existente do SPA), então o próximo `navigate()`/render após trocar de accent já sai sem swap de ícone.

### 8. Conjunto de ícones — armazenamento e amostra de mapeamento

**Armazenamento**: novo arquivo `app/static/icons.js`, carregado via `<script src="/static/icons.js">` **antes** de `app.js` em `index.html`, e antes do script inline em `login.html` — mesmo padrão zero-build do projeto (sem CDN de ícones em runtime, ao contrário da fonte — ver §9). Contém:
- `EMOJI_ICONS` — mapa `{emoji: svgString}`, ~61 entradas, formato Lucide (`stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"`, MIT), normalizado (sem `id`/`class` residual).
- `NAV_ICONS` — mapa `{dataView: svgString}` para os 18 itens de nav.
- `CAIXA_X_ICON` — movida de `app.js` (ver §5).
- `DEFAULT_FAVICON_HREF` / `CAIXA_FAVICON_HREF` — data-URIs para o favicon dinâmico (ver §11).
- `applyIconSkin(root)` — função descrita em §7.

**Amostra representativa** (mapa completo com ~61 entradas fica em `icons.js`, não replicado aqui):

| Emoji | Conceito | Ícone Lucide |
|---|---|---|
| 📊 | Dashboard | `layout-dashboard` |
| 📡 | Monitor de Vencimentos | `radio` |
| 📋 | Geração / Copiar | `clipboard-list` / `copy` |
| 🔧 | Instalação | `wrench` |
| 🚫 | Revogação | `ban` |
| 🗄️ | Histórico | `archive` |
| 🗂️ | Kanban | `columns` |
| 🔍 | Decoder / buscar | `search` |
| 🔗 | Validar cadeia | `link` |
| 🔑 | Senhas | `key` |
| 📖 | Manuais | `book-open` |
| 👥 | Usuários | `users` |
| 🕵️ | Auditoria | `search-check` |
| 🎨 | Aparência | `palette` |
| ⚙️ | Configurações | `settings` |
| ✅ | Sucesso/OK | `check-circle` |
| ⚠️ | Aviso | `alert-triangle` |
| 🌐 / 🔒 | Público/Privado | `globe` / `lock` |
| 🚪 | Sair | `log-out` |
| 🌙/☀️ | Tema escuro/claro | `moon` / `sun` |

**Alternativas consideradas**: desenhar um conjunto próprio inspirado no X CAIXA — rejeitado (decisão já tomada com o usuário: biblioteca open-source de linha, não desenho exclusivo, dado o volume de ~61 conceitos).

### 9. Tipografia

**Decision**: **Poppins** (Google Fonts, SIL OFL, pesos 600/700), via `@import` no topo de `styles.css` — mesmo padrão de dependência de runtime já aceito no projeto (Mermaid via CDN, `index.html:11`).

**Alternativas consideradas**:
- **Century Gothic** — visualmente a mais próxima de Futura, mas é fonte proprietária (Monotype), sem licença livre. Rejeitada.
- **Jost** — alternativa OFL desenhada explicitamente como substituto livre de Futura, geometricamente mais fiel. Fica registrada como alternativa futura se se quiser mais fidelidade; Poppins escolhida por maturidade/robustez de suporte e ampla adoção, incluindo bom suporte a acentos pt-BR.

**Onde aplicar**: token novo `--font-caixa: "Poppins", "Segoe UI", system-ui, sans-serif;` dentro de `[data-accent="caixa"]`, consumido em `.brand-name`, `.view-title`, `.panel h3`, e replicado no `<style>` inline de `login.html`. `body` (`styles.css:74`) **não muda** em nenhum tema — corpo de texto (tabelas, formulários, parágrafos) continua "Segoe UI"/system-ui sempre.

### 10. Extensão de cor além da sidebar

Com `--accent`/`--accent-soft`/`--accent-text` já usados em 36 regras de `styles.css`, a maior parte do reskin de cor já se propaga sozinha quando o accent muda: `#nav a.active`, `.btn-primary` (background), `.input:focus`, `.checkbox-row input` (`accent-color`), estados `.active` de tabs/wizard/kanban, `.timeline li::before`, `.md blockquote`.

**O que falta (gaps reais, confirmados lendo `styles.css`)**:
- `.view-title` (`styles.css:131`) não tem `color` declarado hoje (herda `--text` neutro) — ganha `color: var(--accent-text); font-family: var(--font-caixa);` sob Modo CAIXA (FR-015).
- `.btn-primary` (`styles.css:232`) usa `#fff` hardcoded sobre `var(--accent)`. A variante clara (`#0066B3`) já foi validada AA (5.91:1, §5b). A **escura (`#0097D7`) foi testada nesta fase e reprovou** (`#fff` sobre `#0097D7` = **3.28:1**, abaixo do mínimo 4.5:1) — corrigido com um token dedicado `[data-theme="dark"][data-accent="caixa"] .btn-primary { color: #00293D; }` (`#00293D` sobre `#0097D7` = **4.63:1**, aprovado).
- `.view-title` (cor `var(--accent-text)`, fundo `var(--bg)` da página — não `--accent-soft`, já que o título não é um chip): claro `#00508C` sobre `#f4f6fa` = **7.68:1**; escuro `#4DB8E8` sobre `#12151c` = **8.12:1** — ambos aprovados com folga.
- Não existe componente de spinner/progress bar no projeto — fora de escopo por inexistência do componente, não por omissão.

**Decisão de exclusão (FR-018)**: `.badge-lc-*` (`styles.css:574-579`, 6 regras, cores hardcoded de ciclo de vida de "local de instalação" — pedido/instalado/em_inventario/reservado/excluir/fim_de_vida) fica **fora de escopo**, mesma lógica já aplicada a sucesso/erro/aviso (FR-004): são status semânticos de domínio, não elementos de marca. Documentado para não ser reaberto como "esquecimento".

### 11. `login.html` + favicon dinâmico

**Estado atual**: `login.html` importa `styles.css` (tokens `var(--bg)` etc já funcionam) mas tem `<html data-theme="dark">` **hardcoded** (comportamento pré-existente, fora de escopo — não lê `certhub-theme`). Não carrega `app.js`. Tem `<h1>🔐 CertHub</h1>` em `.brand-header`. Não tem `<link rel="icon">` próprio (diferente de `index.html:9`, que tem favicon hardcoded como SVG-emoji estático).

**Decision**:
1. Adicionar `<script src="/static/icons.js"></script>` em `login.html` (reaproveita o mesmo arquivo, sem duplicar o SVG do X).
2. Script inline no `<head>`, **antes** do CSS aplicar (evita flash), lendo só `certhub-accent`:
   ```html
   <script>document.documentElement.dataset.accent = localStorage.getItem('certhub-accent') || 'blue';</script>
   ```
   Não mexe em `certhub-theme` (permanece hardcoded, fora de escopo desta feature).
3. Depois do DOM montado: se `data-accent === "caixa"`, trocar `.brand-header h1` para usar `CAIXA_X_ICON` em vez do emoji.
4. Favicon dinâmico: mover a definição hoje hardcoded em `index.html:9` para `DEFAULT_FAVICON_HREF`/`CAIXA_FAVICON_HREF` em `icons.js`; trocar `document.querySelector('link[rel="icon"]').href` dentro de `applyAccent()` (`app.js`, cobre `index.html`) e no script novo de `login.html` (que ganha um `<link rel="icon">` que hoje não existe).

**Limitação conhecida (não é bug)**: alguns navegadores cacheiam favicon de forma agressiva entre navegações — documentar como limitação aceita, não perseguir workaround (ex. cache-busting de favicon) nesta feature.
