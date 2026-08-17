# Data Model: Tema Institucional CAIXA

Feature continua puramente de frontend (CSS/JS estático); não há entidades de banco de dados, tabela ou schema de API novos. As "entidades" abaixo são estruturas de configuração/estado no navegador, não persistência de backend.

## Entidade: Preferência de Aparência do Usuário

Já existe (não é criada por esta feature), armazenada como três chaves independentes em `localStorage`, escopo por navegador/dispositivo.

| Campo (chave localStorage) | Tipo | Valores válidos | Default | Lido por (revisado) |
|---|---|---|---|---|
| `certhub-theme` | string | `"light"` \| `"dark"` | `"dark"` | `app.js` (inalterado — `login.html` continua com `data-theme="dark"` hardcoded, fora de escopo) |
| `certhub-layout` | string | `"side"` \| `"compact"` \| `"top"` | `"side"` | `app.js` (inalterado) |
| `certhub-accent` | string | `"blue"` \| `"green"` \| `"purple"` \| `"teal"` \| `"amber"` \| `"red"` \| `"caixa"` | `"blue"` | `app.js` **e, a partir desta revisão, `login.html`** (script inline novo, lê antes do primeiro paint — US7) |

Regra de negócio (FR-006/FR-007, inalterada): `certhub-accent` é single-select — escolher `"caixa"` sobrescreve qualquer valor anterior; escolher outro valor sobrescreve `"caixa"`.

## Entidade: Paleta CAIXA (tokens CSS) — inalterada desta revisão

Ver tabela completa em `contracts/caixa-accent-tokens.md` (sem mudança de conteúdo). Resumo: `--accent`/`--accent-soft`/`--accent-text` (claro/escuro), `--sidebar-bg`/`--sidebar-text`/`--sidebar-text-dim`/`--sidebar-border` (fixos em ambos os temas), `--caixa-orange`/`--caixa-orange-soft`/`--caixa-orange-text`.

## Entidade nova: Token de Tipografia de Marca

| Token | Default (`:root`) | `[data-accent="caixa"]` |
|---|---|---|
| `--font-caixa` | não existe fora do Modo CAIXA (seletores fora de `[data-accent="caixa"]` não referenciam esse token) | `"Poppins", "Segoe UI", system-ui, sans-serif` |

Consumido em `.brand-name`, `.view-title`, `.panel h3` (`styles.css`) e replicado no `<style>` inline de `login.html` (`.brand-header h1`). `body` nunca referencia `--font-caixa`.

## Entidade nova: Conjunto de Ícones de Marca (`app/static/icons.js`)

Não é dado em runtime dinâmico — é um módulo estático carregado via `<script>`, análogo em espírito aos tokens CSS fixos, mas em JS porque precisa ser injetado como `innerHTML`/comparado contra texto renderizado.

| Estrutura | Forma | Conteúdo |
|---|---|---|
| `EMOJI_ICONS` | `{ [emoji: string]: string }` | ~61 entradas, chave = caractere emoji usado hoje como ícone de interface fixo (nav, títulos, botões, badges de status conhecidos, opções de Aparência), valor = markup SVG (Lucide-style, `stroke="currentColor"`) |
| `NAV_ICONS` | `{ [dataView: string]: string }` | 18 entradas, chave = valor de `data-view` de cada item de `#nav a`, valor = markup SVG |
| `CAIXA_X_ICON` | `string` | Movida de `app.js` (era `CAIXA_X_ICON` local) — mesmo SVG do elemento-síntese "X", sem mudança de geometria/cor |
| `DEFAULT_FAVICON_HREF` | `string` (data-URI) | O favicon SVG-emoji atual, hoje hardcoded em `index.html:9`, movido para cá |
| `CAIXA_FAVICON_HREF` | `string` (data-URI) | Favicon baseado em `CAIXA_X_ICON`, novo |
| `applyIconSkin(root)` | função | Ver `contracts/caixa-icon-skin.md` — percorre `root`, casa só o primeiro nó de texto de um seletor fixo de elementos contra `EMOJI_ICONS`, substitui se `data-accent==="caixa"` |

**Exclusão explícita de escopo (não faz parte desta entidade)**: conteúdo de `toast(...)`, `.user-name`, e qualquer texto/dado dinâmico de domínio (CN de certificado, SAN, valores de tabela) — nunca são candidatos a troca de ícone, mesmo que contenham um emoji presente em `EMOJI_ICONS`. `applyIconSkin` só varre o seletor fixo listado em `contracts/caixa-icon-skin.md`, que não inclui `.toast`/`.user-name`/células de tabela de dados.

**Exclusão explícita de escopo (cor, não ícone)**: `.badge-lc-*` (6 regras de status de ciclo de vida de "local de instalação") nunca recebe tratamento visual do Modo CAIXA — nem cor, nem ícone.

## Sem entidades de backend/API (inalterado)

- Nenhuma tabela, coluna ou migração em `app/db.py`.
- Nenhuma rota nova em `app/routers/`.
- Nenhum novo modelo/schema Pydantic.
