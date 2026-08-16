# Contract: `GET /hsm/profiles` — extensão (US2)

Extensão do endpoint já existente (`app/routers/hsm.py`, introduzido em `specs/002-busca-filtro-hsm-perfis/contracts/hsm-profiles-api.md`). Mesma autenticação de sessão, mesmo caminho, mesmo verbo — só a resposta ganha campos novos, não-sensíveis.

## GET /hsm/profiles

**Response 200 (nova forma)**:
```json
{
  "active": "PRD",
  "profiles": [
    {"name": "PRD", "host": "10.0.0.1", "username": "master"},
    {"name": "NPRD", "host": "10.0.1.1", "username": "master"}
  ]
}
```

Diferença em relação à versão anterior: cada item de `profiles` ganha `host` e `username`. `password` continua **nunca** presente na resposta — nenhuma mudança de comportamento quanto a isso. Compatível com o consumidor existente (seletor de troca rápida em `views.hsm`), que só lia `name`.

**Uso pelo frontend**: `views.hsm` usa `host`/`username` do perfil cujo `name === active` pra montar o texto exibido no topo da aba: `"{name} · {host} · {username}"` (US2, FR-002/FR-003).
