# Contract: GET /dashboard (extensão de `next_expiring`)

Endpoint já existente (`app/routers/dashboard.py`) — esta feature só **amplia** o array `next_expiring` do payload, de forma aditiva e retrocompatível (nenhum campo existente é removido/renomeado).

## Request

```
GET /dashboard
```

Sem mudança — mesmos parâmetros (nenhum) de hoje.

## Response — 200 OK (trecho relevante)

```json
{
  "expiring": { "vencidos": 2, "ate_30": 5, "ate_60": 9, "ate_90": 14 },
  "next_expiring": [
    {
      "id": 42,
      "cn": "vpn.exemplo.com.br",
      "not_after": "2026-09-01",
      "days_left": 15,
      "req_number": "REQ-1234",
      "env": "PRD",
      "ownership": "interno",
      "external_partner": null,
      "partner_email": null,
      "has_active_demand": 0
    }
  ],
  "activity": ["... inalterado ..."],
  "totals": ["... inalterado ..."]
}
```

### Campos novos em cada item de `next_expiring`

| Campo | Tipo | Descrição |
|---|---|---|
| `ownership` | string (`"interno"` \| `"externo"`) | copiado de `certificates.ownership` |
| `external_partner` | string \| null | copiado de `certificates.external_partner` |
| `partner_email` | string \| null | copiado de `certificates.partner_email` |
| `has_active_demand` | 0 \| 1 | `1` quando existe uma REQ de geração/recebimento aberta pro mesmo CN — mesmo cálculo de `app/routers/monitor.py:47-63` |

Todos os campos já existentes (`id`, `cn`, `not_after`, `days_left`, `req_number`, `env`) permanecem exatamente como estão.

## Consumidores

- `app/static/app.js` `views.dashboard`: usa os 4 campos novos pra (a) decidir se mostra a ação "Renovar" numa linha (`has_active_demand === 0`) e (b) pré-preencher `newDemandModal('renovacao', {...})` com `ownership`/`external_partner`/`partner_email` — mesmo padrão já usado em `views.monitor`.

## Compatibilidade

Puramente aditivo — qualquer consumidor que hoje lê `next_expiring` e ignora campos desconhecidos continua funcionando sem alteração.
