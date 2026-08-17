# Contract: Estrutura DOM do menu lateral

Este contrato existe porque `app/static/icons.js` (spec 006/007, modo CAIXA) e partes de `app/static/app.js` (`applyAccent`, `applyTheme`, `applyLayout`) dependem de seletores específicos dentro da sidebar. A reestruturação desta feature (grupos + bloco fixo) NÃO PODE quebrar esses contratos já existentes.

## Estrutura resultante

```html
<aside class="sidebar">
  <div class="brand">...</div>                          <!-- inalterado -->

  <nav id="nav">
    <div class="nav-group-label">Certificados</div>       <!-- novo, só texto, não é <a> -->
    <a data-view="certs">...</a>
    <a data-view="decoder">...</a>
    <a data-view="validate">...</a>
    <a data-view="monitor">...</a>

    <div class="nav-group-label">Ciclo de vida</div>
    <a data-view="geracao">...</a>
    ... (instalacao, revogacao, historico, csr, kanban)

    <div class="nav-group-label">Segurança</div>
    <a data-view="hsm">...</a>
    <a data-view="passwords">...</a>

    <div class="nav-group-label">Sistema</div>
    <a data-view="users" class="admin-only">...</a>
    <a data-view="auditoria">...</a>
    <a data-view="docs">...</a>
  </nav>

  <div class="sidebar-secondary">                         <!-- novo -->
    <a data-view="appearance">...</a>
    <a data-view="settings">...</a>
  </div>

  <div class="sidebar-footer">                             <!-- theme-toggle removido -->
    <div id="sidebar-user">...</div>
    <button id="btn-logout">...</button>
    <button id="menu-collapse">...</button>
  </div>
</aside>
```

`dashboard` continua como o primeiro `<a>` dentro de `#nav`, **antes** do primeiro `.nav-group-label` (sem cabeçalho de grupo acima dele).

## Invariantes que NÃO podem quebrar

1. **Todo item navegável continua sendo `<a data-view="...">`** — `.nav-group-label` é só um `<div>` de texto, nunca um `data-view`, nunca clicável/focável como item de navegação.
2. **`#nav a[data-view]` sozinho não cobre mais 100% dos itens navegáveis** — Aparência/Configurações saem pra `.sidebar-secondary a[data-view]`. Qualquer código que hoje faz `$$("#nav a[data-view]")` esperando pegar os 18 itens (ex. `applyAccent`, `app.js:4016`; `NAV_DEFAULT_ICONS`, `app.js:4008-4009`) precisa virar `$$("#nav a[data-view], .sidebar-secondary a[data-view]")` pra continuar cobrindo Aparência/Configurações.
3. **`applyIconSkin()` (`icons.js`) continua funcionando sem mudança própria** — ela é chamada explicitamente sobre containers específicos (`main`, `.sidebar-footer`, modais), nunca faz `querySelectorAll` cego sobre `#nav`; não precisa saber da existência de `.sidebar-secondary`.
4. **`navigate()` (`app.js:327-334`)** — o `$$("#nav a")` que aplica `.active` também precisa expandir pra incluir `.sidebar-secondary a`, senão Aparência/Configurações nunca recebem o destaque de item ativo (violaria FR-005 do spec).
5. **`.nav-group-label` nunca recebe `.active` ou estado de foco** — é puramente decorativo/estrutural.
6. **Layout compacto (`[data-layout="compact"]`)**: `.nav-group-label` deve ficar oculta (`display:none`) nesse modo — o espaço é só ícones, cabeçalho de texto não cabe (edge case do spec, US1).
