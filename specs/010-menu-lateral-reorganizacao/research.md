# Research: Reorganização do Menu Lateral

Nenhum `NEEDS CLARIFICATION` restou no Technical Context — todas as decisões abaixo já foram validadas contra o código atual nesta mesma sessão (leitura direta de `app/static/index.html`, `app/static/app.js`, `app/static/styles.css`, `app/db.py`, `app/routers/monitor.py`).

## 1. Categorização dos 16 itens de menu

**Decision**: 4 grupos — Certificados (Certificados, Decoder, Validar cadeia, Monitor), Ciclo de vida (Geração, Instalação, Revogação, Histórico, Gerar CSR, Kanban), Segurança (HSM, Senhas), Sistema (Usuários, Auditoria, Manuais). Dashboard fica fora de qualquer grupo, fixo no topo.

**Rationale**: Agrupamento por função real do item (o que ele faz), não pela ordem histórica em que foi adicionado ao `#nav` (`index.html:25-42`). Dashboard é a home/overview, não uma função de categoria — convenção comum em sidebars de apps internos.

**Alternatives considered**: Agrupar por "frequência de uso" (dados de analytics não existem hoje, exigiria instrumentação nova — fora de escopo); usar as 5 categorias originalmente sugeridas incluindo "Configuração" como grupo dentro do `#nav` — descartado porque Aparência/Configurações saem do `#nav` (decisão da US2/item 12), então uma 5ª categoria vazia não faz sentido.

## 2. Onde Aparência/Configurações vivem

**Decision**: Novo container `.sidebar-secondary` entre `#nav` e `.sidebar-footer`, com os mesmos 2 `<a data-view>` que hoje estão dentro do `#nav` (`index.html:41-42`).

**Rationale**: Mantém os 2 itens sempre visíveis (não é um menu escondido/acordeão) mas fora da lista rolável de uso frequente — resolve a competição por atenção sem esconder funcionalidade.

**Alternatives considered**: Submenu colapsável (rejeitado — esconde itens que precisam ser sempre alcançáveis em 1 clique, conforme SC-002); manter na lista com só um separador visual (rejeitado explicitamente pelo usuário na sessão de planejamento anterior).

## 3. Ícones/accent nos itens movidos

**Decision**: `applyAccent()` (`app.js:4016`, seletor `#nav a[data-view]`) e `NAV_DEFAULT_ICONS`/`applyIconSkin` (`icons.js`, `app.js:4008-4009`) precisam expandir o seletor pra `#nav a[data-view], .sidebar-secondary a[data-view]`.

**Rationale**: Aparência/Configurações continuam precisando do troca-ícone do modo CAIXA (`NAV_ICONS.appearance`/`NAV_ICONS.settings` já existem em `icons.js`) mesmo fora do `#nav` fisicamente — é markup novo, não uma nova função.

**Alternatives considered**: Duplicar a lógica de ícone num container separado — rejeitado, mais código pra manter o mesmo resultado.

## 4. Remoção do botão de tema do rodapé

**Decision**: Remover `<button id="theme-toggle">` de `index.html` e as referências em `app.js` (`const themeBtn`, as 2 linhas `themeBtn.innerHTML` dentro de `applyTheme()`, e `themeBtn.onclick`).

**Rationale**: `views.appearance` (`app.js:3942`) já tem o card "Tema" completo com Claro/Escuro — o botão do rodapé era um atalho duplicado. Com Aparência virando um item fixo sempre visível (decisão 2 acima), o atalho perde a justificativa de existir.

**Alternatives considered**: Manter os dois — rejeitado pelo usuário explicitamente (queria o rodapé mais limpo).

## 5. Rótulo "Manuais & Comandos" quebrando linha

**Decision**: Encurtar o texto visível pra "Manuais" (mantendo `title="Manuais & Comandos"` completo no `<a>`) **e** adicionar `white-space:nowrap; overflow:hidden; text-overflow:ellipsis` em `.nav-txt` como rede de segurança geral.

**Rationale**: Causa raiz provável é o `font-family: var(--font-caixa)` + `font-weight:600` adicionados ao `#nav a` no modo CAIXA numa sessão anterior — Poppins é mais largo que a fonte padrão, empurrando labels de 2 palavras pro wrap. Encurtar resolve esse caso específico; o `text-overflow:ellipsis` previne qualquer rótulo futuro de quebrar a altura da linha do item (todos os itens do `#nav` têm altura fixa via `padding`, uma quebra de linha desalinha o item vizinho).

**Alternatives considered**: Reduzir só o `font-weight` no modo CAIXA — rejeitado, resolveria o sintoma só nesse modo e manteria o risco de quebra em outros contextos (sidebar mais estreita, zoom do navegador, etc.).

## 6. Badges de contagem — fonte dos números

**Decision**: Novo endpoint `GET /nav-counts` em `app/routers/dashboard.py` (mesmo módulo de `/dashboard` e `/analytics`, sem prefixo, mesmo padrão de registro em `app/main.py`), com 2 queries:
```sql
SELECT COUNT(*) FROM reqs  WHERE demand_type = 'revogacao' AND status NOT IN ('concluida','cancelada')
SELECT COUNT(*) FROM tasks WHERE lane != 'concluido'
```

**Rationale**: Confirmado em `app/db.py:144` que a coluna é `reqs.demand_type` (não `type`) — mesmo campo já usado no filtro `active_req.demand_type IN ('geracao','recebimento')` de `app/routers/monitor.py:49`. `tasks.lane` confirmado em `app/db.py:100-107` (CHECK constraint com os 4 valores incluindo `'concluido'`). Ambas as queries são simples `COUNT(*)` sobre colunas já usadas em filtros existentes — sem necessidade de índice novo pro volume esperado (uso interno).

**Alternatives considered**: Embutir os counts dentro do payload de `/dashboard` já existente — rejeitado porque os badges do menu precisam estar disponíveis em qualquer página, não só quando o usuário está na view Dashboard (que só carrega sob demanda via SPA); um endpoint dedicado e leve pode ser chamado no bootstrap da aplicação independente da view atual.

## 7. Atualização dos badges de contagem

**Decision**: `refreshNavCounts()` chamada (a) uma vez no bootstrap do `app.js` (junto de `applyTheme/applyLayout/applyAccent`), (b) no fim do `load()` de `views.kanban` depois de mover/criar/excluir tarefa, (c) depois de criar/mudar status de uma demanda de revogação.

**Rationale**: Fetch leve (2 `COUNT`), sem necessidade de WebSocket/polling — atualização orientada a ação do próprio usuário é suficiente (spec FR-012, sem requisito de tempo real entre usuários simultâneos, ver Assumptions do spec).

**Alternatives considered**: Polling periódico — rejeitado, complexidade/custo desnecessários pro volume de uso interno; SC-005 do spec já aceita "próxima navegação ou atualização relevante" como critério.

## 8. Contraste do texto/ícone inativo no modo CAIXA

**Decision**: Subir `--sidebar-text-dim` de `rgba(255,255,255,.85)` pra `rgba(255,255,255,.92)` dentro do bloco `[data-accent="caixa"]` em `styles.css`.

**Rationale**: Cálculo WCAG (relative luminance, fórmula padrão sRGB) do texto branco a 85% de opacidade sobre o azul institucional sólido `#006CB5` dá **4.45:1** — abaixo do mínimo AA (4.5:1) pra texto normal. A 92% de opacidade, o cálculo dá **~4.78:1**, dentro da margem. O tema padrão (não-CAIXA) já passa com folga (`--text-dim` sobre `--bg-panel`: 4.90:1 claro / 5.41:1 escuro) — não precisa de mudança.

**Alternatives considered**: Trocar a cor do azul institucional sólido do sidebar — rejeitado, é a cor de marca fixa (manual de identidade visual CAIXA, spec 006), não é ajustável por motivo de contraste; ajustar só a opacidade do texto é a menor mudança que resolve o problema sem tocar a identidade de marca.
