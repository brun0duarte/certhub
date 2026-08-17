# Contract: REST API `/hsm/*` (app/routers/hsm.py)

Endpoints internos da aplicação (mesma autenticação por sessão já usada nos demais routers — `Depends(require_auth)`). Consumidos pelo frontend estático (`app/static/app.js`). Todas as respostas de erro seguem o padrão já usado no projeto: `HTTPException(status_code, "mensagem em pt-BR")`.

## POST /hsm/keys

Cria uma chave no HSM (US1 / FR-001, FR-002).

**Request body**:
```json
{
  "label": "string, obrigatório, único no HSM",
  "key_type": "rsa2048 | rsa4096"
}
```

**Response 200**:
```json
{
  "ok": true,
  "label": "string",
  "key_type": "string"
}
```

**Erros**: `409` se o label já existe no HSM; `502` se o HSM estiver indisponível (FR-012).

---

## POST /hsm/keys/{label}/csr

Gera uma CSR a partir de uma chave já existente no HSM (US2 / FR-003, FR-004).

**Request body**:
```json
{
  "cn": "string, obrigatório",
  "sans": ["string"],
  "org": "string",
  "ou": "string",
  "country": "string",
  "state": "string",
  "locality": "string",
  "email": "string",
  "req_id": "int, opcional — vincula a uma demanda existente, mesmo padrão de /csr/generate"
}
```

**Response 200**: mesmo formato hoje devolvido por `POST /csr/generate` (`{"engine": "dinamo_js", "cn": ..., "csr_pem": "...", "ok": true, ...}`), reaproveitando a gravação em `csrs` já existente.

**Erros**: `404` se `label` não existe no HSM.

---

## POST /hsm/keys/{label}/certificate

Importa um certificado emitido por uma CA e o associa à chave `label` no HSM (US3 / FR-005, FR-006).

**Request**: multipart/form-data com o arquivo do certificado (PEM ou DER), mesmo padrão de upload já usado em `POST /certs` (`app/routers/certs.py`).

**Response 200**: registro criado em `certificates` (mesmo formato hoje devolvido por `POST /certs`), com `source="hsm"` e `hsm_label=label`.

**Erros**: `404` se `label` não existe; `422` se a chave pública do certificado não corresponde à chave `label` (FR-006).

---

## GET /hsm/keys/{label}/export?format=pfx|p12

Exporta certificado + chave privada da entrada `label` em PKCS#12 (US4 / FR-007, FR-008).

**Response 200**: `application/x-pkcs12`, corpo binário do arquivo. Senha do pacote é gerada pela política de senhas existente e devolvida uma única vez no header `X-Export-Password` (nunca logada em texto puro).

**Erros**: `404` se `label` não existe ou não tem certificado associado; `403` se a chave está marcada como não exportável (FR-008).

---

## GET /hsm/search?q={termo}

Busca chaves/certificados na partição do HSM por rótulo ou CN (US5 / FR-009, FR-010, FR-015).

**Response 200**:
```json
{
  "results": [
    {"label": "string", "key_type": "string", "has_certificate": true, "cn": "string|null", "not_after": "ISO8601|null"}
  ]
}
```
`results: []` quando nada é encontrado (não é erro — FR-010).

**Erros**: `502` se o HSM estiver indisponível.
