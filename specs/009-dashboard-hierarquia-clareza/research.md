# Research: Hierarquia e Clareza do Dashboard

Nenhum `NEEDS CLARIFICATION` restou no Technical Context — decisões abaixo validadas contra o código atual (`app/static/app.js`, `app/static/styles.css`, `app/routers/dashboard.py`, `app/routers/monitor.py`).

## 1. Cor dos cards de KPI por severidade

**Decision**: trocar o mapeamento por índice (`alerts.map((a,i) => i===0 ? "stat-red" : i===1 ? "stat-amber" : "stat-green")`, `app.js:349`) por mapeamento pelo **valor** do threshold `a` (dias), em **faixas fixas** (não relativas às janelas configuradas): `a<=30` → vermelho, `a<=60` → âmbar, `a>60` → verde/teal. "Vencidos" (`exp.vencidos`) ganha uma classe adicional `.stat-critical` (borda mais forte) além de `stat-red`. Faixas fixas confirmadas em `/speckit-clarify` (sessão 2026-08-17, ver spec.md FR-001) em vez de faixas relativas às janelas configuradas.

**Rationale**: `alert_days` é configurável (Configurações), hoje pode ter qualquer quantidade de janelas — o mapeamento por índice degrada silenciosamente (4ª+ janela sempre verde, mesmo que seja "≤45 dias", mais urgente que uma 3ª janela "≤90 dias" em outra config). Mapear por valor é robusto a qualquer configuração.

**Alternatives considered**: Gradiente de cor contínuo (vermelho→verde) proporcional ao valor — rejeitado, complexidade desproporcional ao ganho, e foge da paleta discreta já usada em todo o resto do app (badges, etc.).

## 2. Rótulo de "cumulativo"

**Decision**: `<div class="stat-hint">` pequeno (`--text-dim`) nos cards de threshold que não são o primeiro, tipo "inclui os já contados em ≤Nd".

**Rationale**: `ate_30`/`ate_60`/`ate_90` (`app/routers/dashboard.py:18-20`) usam `days_left <= d` — cumulativo por construção da query, não faixas exclusivas. Sem indicação, um usuário soma os 3 números esperando o total de "vencendo nos próximos 90 dias" e conta certificados 2-3x.

**Alternatives considered**: Mudar a query pra faixas exclusivas (`BETWEEN`) — rejeitado, é uma mudança de comportamento/semântica dos dados existentes (outros lugares podem depender do cumulativo), a spec só pede clareza, não mudança de cálculo.

## 3. Agrupamento de "Próximos vencimentos" por data

**Decision**: reduce client-side sobre `d.next_expiring` (já ordenado por `not_after ASC`, `dashboard.py:29-33`) agrupando por data igual, renderizando uma linha-resumo clicável que expande **a partir de 3 certificados na mesma data** — com 1 ou 2, as linhas continuam soltas normalmente (limiar fixado em `/speckit-clarify`, sessão 2026-08-17, ver spec.md FR-009).

**Rationale**: Zero mudança de backend — a ordenação já favorece agrupamento em blocos contíguos. Expansão via toggle de classe CSS é o padrão já usado no resto do app (sem framework reativo). O limiar de 3 evita colapsar coincidências de 2 datas (ainda legíveis soltas) num resumo que economiza pouco espaço.

**Alternatives considered**: Agrupar no backend (SQL `GROUP BY not_after`) — rejeitado, perderia os campos individuais (CN, REQ) que a linha expandida precisa mostrar; mais simples manter a lista plana do jeito que já vem e agrupar na apresentação. Agrupar a partir de 2 — rejeitado na clarificação, prioriza manter linhas isoladas legíveis quando a economia de espaço é mínima.

## 4. Legenda de ambiente

**Decision**: mapa `ENV_LABEL = {PRD:"Produção", HMP:"Homologação", TQS:"Teste de Qualidade", DES:"Desenvolvimento"}` novo, usado tanto no `title` de `envBadge()` (`app.js:255`) quanto numa legenda fixa abaixo do bloco "Demandas por ambiente e status" (`app.js:384`).

**Rationale**: Significados confirmados com o usuário no planejamento anterior. Reaproveita as cores já definidas em `.badge-PRD/-TQS/-HMP/-DES` (`styles.css:220-223`) — a legenda só documenta a lógica já existente (severidade), não introduz cor nova.

**Alternatives considered**: Só tooltip, sem legenda fixa — rejeitado, spec FR-008 pede visibilidade sem precisar de hover (acessibilidade a touch/teclado).

## 5. Contraste dos badges de lifecycle + rename "Excluir"

**Decision**: reescrever as 6 regras `.badge-lc-*` (`styles.css:626-631`, hoje hex fixo tipo `#fdcb6e33`/`#ffeaa7`) usando os tokens de tema (`--purple/-soft`, `--green/-soft`, `--accent/-soft`, `--amber/-soft`, `--red/-soft`, `--gray/-soft`), mesmo padrão de `.badge-prio-*`. `LIFECYCLE_STATUS.excluir` (`app.js:230`) muda de `"Excluir"` pra `"Baixado do inventário"` — só o label, a chave `excluir` do dicionário/dados não muda.

**Rationale**: Contraste calculado (WCAG relative luminance) do par atual mais crítico (`#ffeaa7` sobre fundo quase-branco no tema claro) fica bem abaixo de 4.5:1 — falha AA. Os tokens `-soft`/cor já são usados em `.badge-prio-*` e outros badges do sistema nos dois temas, com contraste validado. "Excluir" como status (não ação) ao lado de um botão real de exclusionar (ex. modal de tarefa) cria ambiguidade — renomear resolve sem tocar lógica.

**Alternatives considered**: Só ajustar a opacidade dos hex atuais — rejeitado, manteria uma paleta paralela (hex fixo) desalinhada do resto do sistema (tokens `var(--cor)`), que já resolve automaticamente claro/escuro.

## 6. Compressão e agrupamento da "Atividade Recente"

**Decision**: comprimir cada evento de `d.activity` (`app.js:376-379`) de 3 linhas pra 2 (ação numa linha, detalhe+timestamp/usuário na outra), e agrupar via reduce client-side **sequências de 3 ou mais eventos consecutivos** com mesma `action`+`req_number` numa única entrada com sufixo "×N" — sequências de 1 ou 2 eventos idênticos permanecem soltas (limiar fixado em `/speckit-clarify`, sessão 2026-08-17, ver spec.md FR-013).

**Rationale**: Sem mudança de backend — `d.activity` já vem pronto (`LIMIT 10`). O limiar de 3 é consistente com o mesmo critério adotado pro agrupamento de "Próximos vencimentos" (decisão 3 acima): evita agrupar cedo demais (2 eventos iguais seguidos ainda são fáceis de ler soltos) e some informação real só quando a repetição já é ruído de fato.

**Alternatives considered**: Agrupar a partir de 2 — rejeitado na clarificação, mesmo raciocínio da decisão 3 (economia de espaço marginal, risco de esconder eventos individuais relevantes).

## 7. Linha de média + mês atual no gráfico

**Decision**: `chartVBars(items, {avg, currentLabel})` — `avg` desenhado como `<div class="vbar-avg-line">` posicionado via `top` calculado (mesma escala das barras, `Math.round(n/max*120)`), `currentLabel` comparado a cada `item.label` pra aplicar `.vbar-current` na barra do mês corrente.

**Rationale**: `chartVBars` (`app.js:3748-3755`) é puro/sem estado — estender via parâmetros opcionais mantém compatibilidade com as outras 2 chamadas do mesmo helper que não precisam desse overlay.

**Alternatives considered**: SVG dedicado para o gráfico — rejeitado, todo o resto do dashboard usa `div`s com CSS (sem canvas/SVG de terceiros), manter consistência de abordagem.

## 8. Grid vazio na linha de análise

**Decision**: trocar `class="grid grid-2 mt"` por `class="grid grid-3 mt"` na linha que envolve `reqs_by_month`/`key_types`/`cert_health` (`app.js:390-408`).

**Rationale**: Achado direto — `.grid-3` já existe em `styles.css:194` (`1fr 1fr 1fr`, com fallback responsivo pra 1 coluna em `styles.css:195`), só não estava sendo usada nessa linha que tem até 3 painéis condicionais. Correção de 1 palavra, sem CSS novo.

**Alternatives considered**: Grid dinâmico via JS contando quantos painéis vão renderizar — rejeitado, desnecessário já que `.grid-3` com `auto`/`1fr 1fr 1fr` + `min-width:0` (`styles.css:191`) já se comporta bem com 1, 2 ou 3 itens presentes.

## 9. Ação rápida "Renovar" no Dashboard

**Decision**: estender `next_expiring` (`app/routers/dashboard.py:29-33`) com `c.ownership, c.external_partner, c.partner_email` + o mesmo `LEFT JOIN reqs active_req ON active_req.cn = c.cn AND active_req.demand_type IN ('geracao','recebimento') AND active_req.status NOT IN ('concluida','cancelada')` e `has_active_demand` já usado em `app/routers/monitor.py:47-63`. No front, reaproveitar o handler `data-renew` existente (`app.js:614-619`, `newDemandModal('renovacao', {...}, load)`).

**Rationale**: Padrão idêntico já implementado e testado em produção (Monitor) — replicar a mesma subquery evita reinventar a lógica de "tem demanda ativa" em dois lugares com potencial de divergir.

**Alternatives considered**: Link "Ver no Monitor" em vez de ação inline — rejeitado, spec FR-010 pede início rápido sem trocar de view; o padrão do Monitor já resolve isso com uma única linha de JOIN a mais.
