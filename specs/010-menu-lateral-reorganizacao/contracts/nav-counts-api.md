# Contract: GET /nav-counts

Endpoint novo, aditivo, em `app/routers/dashboard.py` (mesmo router de `/dashboard` e `/analytics`, mesmo padrão de registro em `app/main.py`, protegido pelo mesmo `require_auth` já aplicado aos demais routers autenticados).

## Request

```
GET /nav-counts
```

Sem parâmetros, sem corpo.

## Response — 200 OK

```json
{
  "revogacao_pendente": 3,
  "kanban_pendente": 7
}
```

| Campo | Tipo | Descrição |
|---|---|---|
| `revogacao_pendente` | integer, ≥ 0 | Demandas com `demand_type='revogacao'` e `status NOT IN ('concluida','cancelada')` |
| `kanban_pendente` | integer, ≥ 0 | Tarefas com `lane != 'concluido'` |

Ambos os campos sempre presentes (nunca `null`, nunca omitidos — mesmo quando 0).

## Erros

Mesmo comportamento padrão dos demais endpoints do router: 401 se não autenticado (via `require_auth`, aplicado no registro do router em `app/main.py` — mesmo padrão de `/dashboard`).

## Consumidores

- `app/static/app.js`: `refreshNavCounts()` — chamada no bootstrap e após ações que mudam a contagem (mover/criar/excluir tarefa Kanban; criar/concluir/cancelar demanda de revogação). Injeta/remove `<span class="nav-badge">` nos itens `data-view="revogacao"` e `data-view="kanban"` do `#nav`.

## Fora de escopo

- Não inclui breakdown por sub-status, por ambiente, ou por usuário — só o total agregado necessário pro badge do menu.
- Não é paginado, não aceita filtros — é um agregado fixo de 2 números.
