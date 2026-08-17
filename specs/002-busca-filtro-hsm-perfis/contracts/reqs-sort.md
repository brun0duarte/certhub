# Contract: `GET /reqs` — parâmetros de ordenação (US2)

Extensão do endpoint já existente (`app/routers/reqs.py:98`), consumido pelas abas Geração, Instalação (e reaproveitável por qualquer outra lista de demandas). Mesma autenticação de sessão já usada no router. Compatível com versões anteriores: sem `sort`/`dir`, comportamento é idêntico ao atual (`ORDER BY r.created_at DESC`).

## GET /reqs

**Novos query params** (além de `search`, `env`, `status`, `demand_type`, `exclude_status`, `page`, `page_size` já existentes):

| Param | Tipo | Default | Notas |
|---|---|---|---|
| `sort` | string | `created_at` | um de `req_number`, `env`, `status`, `created_at`; valor desconhecido cai no default, sem erro |
| `dir` | string | `desc` | `asc` ou `desc`; qualquer outro valor cai em `asc`, espelhando `monitor.py` |

**Response 200**: formato inalterado — `{"items": [...], "total": int}`. A ordem dos itens em `items` reflete `sort`/`dir`.

**Exemplo**:

```
GET /reqs?demand_type=geracao&sort=env&dir=asc
```

```json
{
  "items": [
    {"id": 12, "req_number": "REQ0000012", "env": "HMP", "status": "aberta", "...": "..."},
    {"id": 7,  "req_number": "REQ0000007", "env": "PRD", "status": "aberta", "...": "..."}
  ],
  "total": 2
}
```
