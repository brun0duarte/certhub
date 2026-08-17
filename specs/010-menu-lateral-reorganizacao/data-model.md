# Data Model: Reorganização do Menu Lateral

Nenhuma migração de schema — todas as entidades abaixo são derivadas de dados/markup já existentes (`app/db.py`, `app/static/index.html`). O único dado novo é o payload agregado do endpoint `/nav-counts` (ver `contracts/nav-counts-api.md`), que não persiste nada, só lê.

## Item de menu

Representação (markup, não tabela de banco) de um destino de navegação da SPA.

| Campo | Origem | Observações |
|---|---|---|
| `data-view` | atributo do `<a>` (`index.html`) | chave usada por `navigate()`, `applyAccent()`, `NAV_ICONS` (`icons.js`) — inalterada por esta feature |
| rótulo (`nav-txt`) | texto do `<span class="nav-txt">` | "Manuais & Comandos" → "Manuais" (item 11); demais inalterados |
| `title` | atributo do `<a>` | tooltip completo — mantido/expandido (ex. Manuais mantém título completo mesmo com rótulo curto) |
| ícone | `<span>` filho, trocado por `applyAccent()`/`applyIconSkin()` | inalterado — só o seletor que os alcança muda (grupo 3 do research.md) |
| categoria | **novo** — não é atributo HTML, é posição estrutural (dentro de qual bloco `<div class="nav-group">` o `<a>` está) | 1 de 4 valores fixos: Certificados / Ciclo de vida / Segurança / Sistema, ou nenhuma (Dashboard) |
| localização | **novo** — `#nav` (lista rolável) vs `.sidebar-secondary` (bloco fixo) | Aparência/Configurações migram de `#nav` pra `.sidebar-secondary` |
| indicador de pendência | **novo** — `<span class="nav-badge">` opcional, injetado por JS | só em `data-view="revogacao"` e `data-view="kanban"`; ausente quando contagem = 0 |

## Categoria funcional

Puramente estrutural — não é uma entidade de dados, é um agrupamento visual fixo definido em `index.html` via `<div class="nav-group-label">Nome</div>` antes de cada conjunto de `<a>`.

| Categoria | Itens (data-view) |
|---|---|
| *(sem cabeçalho)* | `dashboard` |
| Certificados | `certs`, `decoder`, `validate`, `monitor` |
| Ciclo de vida | `geracao`, `instalacao`, `revogacao`, `historico`, `csr`, `kanban` |
| Segurança | `hsm`, `passwords` |
| Sistema | `users`, `auditoria`, `docs` |
| *(bloco fixo separado)* | `appearance`, `settings` |

## Indicador de pendência (nav-counts)

Não é uma tabela — é um payload agregado calculado sob demanda a partir de `reqs` e `tasks` (schema existente, `app/db.py`).

| Campo | Tipo | Cálculo |
|---|---|---|
| `revogacao_pendente` | inteiro ≥ 0 | `COUNT(*) FROM reqs WHERE demand_type='revogacao' AND status NOT IN ('concluida','cancelada')` |
| `kanban_pendente` | inteiro ≥ 0 | `COUNT(*) FROM tasks WHERE lane != 'concluido'` |

Sem estado próprio, sem histórico — recalculado a cada chamada do endpoint (ver `contracts/nav-counts-api.md`).

## Regras de validação (derivadas dos Functional Requirements do spec)

- Um item de menu pertence a exatamente 0 ou 1 categoria (FR-001, FR-002) — nunca mais de uma.
- `revogacao_pendente`/`kanban_pendente` nunca são negativos (contagem simples, não pode ser < 0 por construção da query).
- O indicador de pendência só é renderizado no DOM quando o valor correspondente é > 0 (FR-011) — não existe estado "badge com zero visível".
