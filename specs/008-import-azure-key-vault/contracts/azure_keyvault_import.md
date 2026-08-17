# Contrato: Requisição/Resposta de Importação no Azure Key Vault

Não é uma API exposta pelo CertHub — é o contrato com a API externa do Azure Key Vault que `AzureKeyVaultProvider.install()` passa a seguir. Documentado aqui porque define exatamente o que muda no request/response desta feature.

## Requisição (CertHub → Azure Key Vault)

```
POST https://{vault_name}.vault.azure.net/certificates/{certificate_name}/import?api-version=7.4
Authorization: Bearer {access_token}
Content-Type: application/json
```

```json
{
  "value": "<PFX em base64, montado a partir da chave/certificado resolvidos via HSM ou upload>",
  "pwd": "",
  "policy": {
    "key_props": {
      "exportable": true,
      "kty": "RSA",
      "key_size": 2048,
      "reuse_key": false
    },
    "secret_props": {
      "contentType": "application/x-pkcs12"
    }
  }
}
```

- `value`/`pwd`: sem mudança de comportamento (PFX montado sem senha, `pwd` sempre `""` — comportamento já existente).
- `policy`: **novo nesta feature** (FR-001) — bloco fixo, não vem de `config` nem de setting.

## Resposta de sucesso (200) — campos que o CertHub passa a ler

```json
{
  "id": "https://{vault}.vault.azure.net/certificates/{name}/{version}",
  "x5t": "<thumbprint base64url>",
  "attributes": {
    "nbf": 1786856515,
    "exp": 1788043710
  }
}
```

| Campo lido | Como é usado |
|---|---|
| `id` | Último segmento do path → identificador de versão exibido ao usuário (FR-003). |
| `x5t` | Exibido como thumbprint do certificado importado (FR-002). |
| `attributes.exp` | Convertido de epoch pra data legível → validade exibida (FR-002). |
| `attributes.nbf` | Idem, data de início de validade (FR-002). |

Campos da resposta não usados por esta feature (`kid`, `sid`, `cer`, `policy` ecoado, `attributes.created`/`updated`, `recoveryLevel`) são ignorados — não fazem parte do "informações relevantes" definido no spec (Assumptions).

## Resposta de erro (4xx/5xx) — sem alteração

Continua sendo repassada como está hoje (FR-005): `result["error"] = f"Azure Key Vault retornou erro ({resp.status_code}): {resp.text}"`.

## Resultado retornado pelo provider ao chamador (`install()` → dict)

Sem mudança de forma — mesma interface `InstallProvider.install()` já existente (`app/services/installers/base.py`):

```python
{"ok": True, "output": "<mensagem detalhada ou genérica, ver research.md #3>", "error": ""}
```

`output` continua sendo texto livre — não é um schema novo, só o conteúdo do texto muda quando o parsing dos 3 campos acima tem sucesso.
