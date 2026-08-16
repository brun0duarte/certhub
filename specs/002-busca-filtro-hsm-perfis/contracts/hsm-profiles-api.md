# Contract: Perfis de HSM (US4)

CRUD dos perfis nomeados continua via `PUT /settings` genérico já existente (chave `hsm_dinamo_profiles`, validado como JSON igual às demais chaves em `JSON_KEYS`). Um endpoint novo, dedicado, cobre a troca rápida do perfil ativo direto da aba HSM (sem reescrever o JSON inteiro pela tela de Configurações).

## PUT /settings (existente, sem mudança de assinatura)

Body inclui `values.hsm_dinamo_profiles` como string JSON no formato descrito em `data-model.md`. Validações adicionais aplicadas nesta chave (além do "precisa ser JSON válido" já existente):

- `name` duplicado entre `profiles` → `400`.
- `active` não vazio e sem correspondência em `profiles[].name` → `400`.
- Remoção do profile cujo `name == active` sem troca simultânea de `active` para outro nome existente → `400` (FR-012).

## PUT /hsm/active-profile *(novo)*

Troca o perfil ativo. Usado pelo seletor rápido exibido na própria aba HSM (FR-009, SC-005).

**Request body**:
```json
{"name": "string, obrigatório — deve existir em hsm_dinamo_profiles.profiles"}
```

**Response 200**:
```json
{"ok": true, "active": "string"}
```

**Erros**: `404` se `name` não corresponde a nenhum perfil cadastrado.

## GET /hsm/profiles *(novo)*

Lista os perfis cadastrados e qual está ativo — usado para popular o seletor rápido na aba HSM sem duplicar o parse do JSON de `settings` no frontend.

**Response 200**:
```json
{
  "active": "PRD",
  "profiles": [
    {"name": "PRD"},
    {"name": "NPRD"}
  ]
}
```

Nota: a resposta **omite** `host`/`port`/`username`/`password` — a edição de credenciais continua exclusiva da tela de Configurações (`PUT /settings`), já protegida pela mesma autenticação de sessão do restante do app. Este endpoint existe só para popular o seletor de troca rápida.

## Impacto em `app/routers/hsm.py`

`_provider(conn)` (linhas 21-23) passa a resolver a conexão assim:

```
config = json.loads(get_setting(conn, "hsm_dinamo_profiles"))
active = next(p for p in config["profiles"] if p["name"] == config["active"])
return DinamoJsProvider(active)
```

Se `config["profiles"]` estiver vazio ou `active` não corresponder a nenhum perfil, todas as rotas de `/hsm/*` que dependem de `_provider` retornam `400` com mensagem "Nenhum perfil de HSM configurado — cadastre um em Configurações." em vez de tentar conectar com dados vazios.
