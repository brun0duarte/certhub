# Implementation Plan: Tema Institucional CAIXA

**Branch**: `006-tema-marca-caixa` | **Date**: 2026-08-16 (revisado — escopo expandido) | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-tema-marca-caixa/spec.md`

## Summary

Revisão deste plano: a primeira versão (US1-3, já implementada em T001-T013) tratou o Modo CAIXA só como mais uma opção de "cor de destaque". O usuário pediu explicitamente mais: cor, tipografia, logo **e ícones de interface** em toda a aplicação (US4-US7 do spec revisado). Este plano cobre a expansão, reaproveitando 100% do que já existe (mecanismo `data-accent="caixa"`, tokens `--accent`/`--sidebar-*`/`--caixa-orange`, `CAIXA_X_ICON`).

A peça nova de maior risco é a **troca de ~198 ocorrências de emoji-ícone por ícones de linha** sem editar 198 pontos espalhados em 4000+ linhas de `app.js`. A solução adotada (validada lendo o código real) é hookar os dois chokepoints de render que o SPA já tem — `navigate()` (`app.js:325`) e `modal()` (`app.js:141`) — mais ~10 funções de sub-render que escapam desses chokepoints, em vez de tocar cada emoji individualmente ou usar um `MutationObserver` irrestrito (que arriscaria trocar emoji dentro de toasts/texto dinâmico).

As demais mudanças (tipografia Poppins em títulos/marca, `.view-title` com cor institucional, revalidação de contraste do botão primário no azul escuro, Modo CAIXA refletido em `login.html` + favicon dinâmico) são extensões pontuais e de baixo risco sobre a base já existente.

## Technical Context

**Language/Version**: JavaScript vanilla (ES2020+, sem bundler/transpilação) + CSS3; backend Python 3.11 / FastAPI não é tocado (inalterado desde a v1 deste plano).

**Primary Dependencies**: Uma dependência de runtime NOVA — fonte **Poppins** via `@import` do Google Fonts no topo de `styles.css` (SIL OFL, pesos 600/700). Não é um precedente novo no projeto: `index.html:11` já carrega Mermaid via CDN (`https://cdn.jsdelivr.net/npm/mermaid@11/...`), então dependência de rede em runtime já é aceita nesta base de código. Nenhuma outra dependência nova; nenhum build tool.

**Storage**: `localStorage` do navegador, mesma chave `certhub-accent` já usada (sem chave nova) — agora também lida por `login.html` (hoje só `index.html`/`app.js` liam).

**Testing**: Sem framework de teste de frontend no projeto (inalterado). Validação manual via `quickstart.md` revisado, cobrindo os novos pontos (ícones, fonte, login, favicon).

**Target Platform**: Navegador web (mesma SPA estática servida pelo FastAPI).

**Project Type**: Aplicação web single-project (inalterado) — novo arquivo estático `app/static/icons.js`, sem novo diretório/processo.

**Performance Goals**: N/A. Ressalva nova: `applyIconSkin()` roda a cada `navigate()`/`modal()`/sub-render quando Modo CAIXA está ativo — é uma varredura de `querySelectorAll` sobre um seletor fixo dentro de `#main`/`#modal-root` (nunca o documento inteiro), custo desprezível para o volume de elementos por view deste app (dezenas, não milhares).

**Constraints**: Continua proibido introduzir build tooling de frontend. Novo: a substituição de ícone é estritamente opt-in (só sob `data-accent="caixa"`) e estritamente restrita a elementos de interface fixos — **nunca** toasts, nomes/valores de usuário ou badges de status de domínio (`badge-lc-*`), para não arriscar corromper texto dinâmico. Ícones vêm de um conjunto de licença aberta (estilo Lucide/Feather, MIT), auto-hospedado — sem CDN de ícones em runtime.

**Scale/Scope**: ~198 ocorrências de emoji-ícone / ~61 emojis distintos a mapear (não editar 198 pontos — ver Summary). Arquivos tocados: `app/static/app.js`, `app/static/styles.css`, `app/static/index.html`, `app/static/login.html`, mais 1 arquivo novo `app/static/icons.js`. Nenhum arquivo de backend.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

`.specify/memory/constitution.md` continua só com os placeholders do template — nenhum princípio definido pelo projeto. Gate **PASS por ausência de constituição definida** (inalterado desde a v1). Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-tema-marca-caixa/
├── plan.md              # Este arquivo (revisado)
├── research.md          # Revisado — decisões de arquitetura da expansão
├── data-model.md        # Revisado — novas entidades (Conjunto de Ícones, favicon)
├── quickstart.md        # Revisado — cobre US4-US7
├── contracts/           # Revisado — 2 contratos novos (icon-skin, typography/login)
│   ├── caixa-accent-tokens.md     # já existente, sem mudança de conteúdo
│   ├── caixa-brand-icon.md        # já existente, sem mudança de conteúdo
│   ├── caixa-icon-skin.md         # NOVO — mecanismo de troca de ícone
│   └── caixa-typography-login.md  # NOVO — fonte, .view-title, botão primário, login/favicon
└── tasks.md              # Phase 2 (T001-T013 já feitas; T014+ revisadas nesta rodada)
```

### Source Code (repository root)

```text
app/
├── static/
│   ├── icons.js           # NOVO — EMOJI_ICONS (~61), NAV_ICONS, CAIXA_X_ICON (movida de app.js),
│   │                         DEFAULT_FAVICON_HREF/CAIXA_FAVICON_HREF, applyIconSkin(root)
│   ├── index.html          # <script src="/static/icons.js"> antes de app.js; favicon passa a
│   │                         ser trocado via JS (não só hardcoded)
│   ├── login.html          # <script src="/static/icons.js">; script inline novo no <head>
│   │                         lendo certhub-accent antes do primeiro paint; <link rel="icon"> novo
│   ├── styles.css          # @import Poppins; --font-caixa; .view-title/.panel h3/.brand-name
│   │                         usam --font-caixa sob [data-accent="caixa"]; .btn-primary revalidado
│   └── app.js              # navigate()/modal() chamam applyIconSkin(); ~10 sub-renders idem;
│                              NAV_ICONS aplicado aos 18 itens de #nav; CAIXA_X_ICON removida daqui
│                              (agora em icons.js)
├── routers/, services/, db.py, main.py   # NÃO tocados — feature continua 100% frontend
tests/                                     # NÃO tocados
```

**Structure Decision**: Continua projeto único, tudo dentro de `app/static/`. Único elemento novo de estrutura é o arquivo `icons.js` — carregado como `<script>` estático adicional, sem processo de build, mesmo padrão zero-dependência do resto do projeto.

## Complexity Tracking

> Vazio — não há violações de constituição a justificar (constituição não definida). A complexidade real desta expansão (mapear ~61 ícones, hookar 2 chokepoints + ~10 sub-renders) é inerente ao pedido do usuário, não uma escolha de arquitetura evitável; a alternativa mais simples (MutationObserver global) foi avaliada e descartada por risco de corromper texto dinâmico (toasts, nomes de usuário) — ver `research.md`.
