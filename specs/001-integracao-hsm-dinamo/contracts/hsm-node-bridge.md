# Contract: bridge Python → Node (`app/services/hsm/node/hsm-helper.js`)

Protocolo interno entre `DinamoJsProvider` (Python) e o script Node que usa o SDK oficial `@dinamonetworks/hsm-dinamo`. Um processo por chamada (`node hsm-helper.js <action>`), request em JSON via **stdin**, response em JSON via **stdout**. Erros de execução vão para **stderr** e não são parseados como JSON.

**Por quê stdin/stdout em vez de argv**: credenciais (usuário/senha da partição) e senha de exportação PFX nunca devem aparecer em `argv` de processo (visível via `ps`) nem em logs de comando — só o nome da `action` é passado como argumento posicional.

## Invocação

```
node hsm-helper.js <action>
```

`<action>` ∈ `{gen-key, gen-csr, import-cert, export-pfx, search}`

## Request (stdin JSON) — comum a todas as ações

```json
{
  "connection": {"host": "string", "port": "number", "username": "string", "password": "string"},
  "params": { }
}
```

`connection` vem de `hsm_dinamo_config` (settings). `params` varia por ação:

| action | params |
|---|---|
| `gen-key` | `{"label": "string", "key_type": "rsa2048\|rsa4096"}` |
| `gen-csr` | `{"label": "string", "cn": "string", "sans": ["string"], "org": "string", "ou": "string", "country": "string", "state": "string", "locality": "string", "email": "string"}` |
| `import-cert` | `{"label": "string", "cert_pem": "string"}` |
| `export-pfx` | `{"label": "string", "password": "string"}` |
| `search` | `{"query": "string"}` |

## Response (stdout JSON) — sucesso

```json
{"ok": true, "data": { }}
```

`data` por ação:

| action | data |
|---|---|
| `gen-key` | `{"label": "string", "key_type": "string"}` |
| `gen-csr` | `{"csr_pem": "string"}` |
| `import-cert` | `{"label": "string", "imported": true}` |
| `export-pfx` | `{"pfx_base64": "string"}` |
| `search` | `{"results": [{"label": "...", "key_type": "...", "has_certificate": bool, "cn": "...", "not_after": "..."}]}` |

## Response (stdout JSON) — falha

```json
{"ok": false, "error": "mensagem legível", "code": "NOT_FOUND | ALREADY_EXISTS | KEY_MISMATCH | NOT_EXPORTABLE | CONN_FAILED | TIMEOUT"}
```

`DinamoJsProvider` mapeia `code` para o `HTTPException` correspondente no router (`hsm-rest-api.md`).

## Limitações confirmadas do SDK real (ver `research.md` #7)

- `gen-csr` aceita `sans` na entrada por compatibilidade com o contrato REST, mas o SDK (`key.generatePKCS10`) só assina o Distinguished Name — **SANs não entram na CSR gerada**.
- O certificado associado a uma chave `label` é armazenado no HSM sob o nome `${label}.cert` (objeto separado — o SDK não tem o conceito nativo de "certificado da chave X").
- `import-cert` valida a correspondência de chave pública (FR-006) no próprio bridge (`node-forge`), não no HSM — a API do SDK não faz essa checagem.

## Timeout e disponibilidade

- O processo Python que invoca o bridge aplica timeout de 30s (criação de chave/CSR/importação/busca) e 60s (exportação PFX, potencialmente mais pesada). Excedido o timeout, o provider mata o processo e retorna `code: "TIMEOUT"` (cobre FR-012 e o edge case de timeout do `spec.md`).
- Falha de conexão com o HSM (host inalcançável, credencial inválida) é normalizada para `code: "CONN_FAILED"`, nunca deixando estado parcial gravado no banco local (o `INSERT`/`UPDATE` em `certificates`/`csrs` só ocorre após `ok: true` do bridge).
