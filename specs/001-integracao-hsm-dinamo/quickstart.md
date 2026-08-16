# Quickstart: validar a integração HSM (Dinamo)

## Pré-requisitos

- Backend rodando localmente (`uvicorn app.main:app --reload`, conforme já documentado no projeto).
- Node.js ≥ 18 instalado e no `PATH` (`node -v`).
- Dependência `@dinamonetworks/hsm-dinamo` instalada em `app/services/hsm/node/` (`npm install` dentro dessa pasta).
- Acesso de rede a um HSM Dinamo real (ou ambiente de homologação da Dinamo) com uma partição de teste e usuário/senha válidos.
- Login na aplicação como usuário com o mesmo nível de permissão de administrador de certificados já usado hoje (ver `Assumptions` do `spec.md`).

## 1. Configurar a conexão com o HSM

Na aba **Configurações** já existente na aplicação, preencher a nova seção **HSM (Dinamo)**:

```
Host: <ip/hostname do HSM>
Porta: <porta>
Usuário: <usuário da partição>
Senha: <senha da partição>
```

Equivalente via API (`PUT /settings`), reaproveitando o padrão já usado por `hsmutil_templates`:

```bash
curl -X PUT http://localhost:8000/settings \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{"values": {"hsm_dinamo_config": "{\"host\":\"<ip>\",\"port\":\"<porta>\",\"username\":\"<user>\",\"password\":\"<senha>\"}"}}'
```

## 2. Criar uma chave no HSM (US1)

```bash
curl -X POST http://localhost:8000/hsm/keys \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"label": "quickstart-test-01", "key_type": "rsa2048"}'
```

**Esperado**: `200` com `{"ok": true, "label": "quickstart-test-01", ...}`. Repetir a chamada deve dar `409` (rótulo em uso — FR-002).

## 3. Gerar CSR a partir dessa chave (US2)

```bash
curl -X POST http://localhost:8000/hsm/keys/quickstart-test-01/csr \
  -H "Content-Type: application/json" -b cookies.txt \
  -d '{"cn": "quickstart.example.com", "sans": ["quickstart.example.com"]}'
```

**Esperado**: `200` com `csr_pem` contendo `-----BEGIN CERTIFICATE REQUEST-----`. Testar também com um `label` inexistente e confirmar `404` (FR-004).

## 4. Importar o certificado emitido (US3)

Assinar a CSR gerada acima em qualquer CA de teste (ex.: `openssl ca` local) e importar o certificado resultante:

```bash
curl -X POST http://localhost:8000/hsm/keys/quickstart-test-01/certificate \
  -b cookies.txt -F "file=@quickstart-test-01.crt"
```

**Esperado**: `200` com o registro de certificado (`source: "hsm"`, `hsm_label: "quickstart-test-01"`). Testar importar um certificado de chave diferente e confirmar `422` (FR-006).

## 5. Exportar PFX/P12 (US4)

```bash
curl -X GET "http://localhost:8000/hsm/keys/quickstart-test-01/export?format=pfx" \
  -b cookies.txt -D headers.txt -o quickstart-test-01.pfx
grep -i x-export-password headers.txt
openssl pkcs12 -info -in quickstart-test-01.pfx -passin pass:"<senha do header>" -noout
```

**Esperado**: `openssl pkcs12 -info` roda sem erro, confirmando que o PFX é válido e abre com a senha devolvida.

## 6. Buscar no HSM (US5)

```bash
curl "http://localhost:8000/hsm/search?q=quickstart" -b cookies.txt
```

**Esperado**: `results` inclui `quickstart-test-01` com `has_certificate: true`. Buscar por um termo inexistente deve devolver `{"results": []}` com `200` (FR-010), não erro.

## 7. Conferir auditoria (FR-011)

```bash
curl "http://localhost:8000/activity" -b cookies.txt | grep -i quickstart-test-01
```

**Esperado**: uma entrada de log para cada uma das 4 operações acima (criação de chave, CSR, importação, exportação), visível em até 1 minuto (SC-006).

## Cenário de indisponibilidade (edge case)

Apontar `hsm_dinamo_config.host` para um endereço inválido e repetir o passo 2. **Esperado**: `502` com mensagem compreensível, sem registro parcial criado em `certificates`/`csrs` (FR-012, SC-007).
