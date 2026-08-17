# Data Model: Integração com HSM via API (Dinamo Networks)

Fonte da verdade para chaves e para a associação chave↔certificado é o próprio HSM. O banco local (SQLite, `app/db.py`) só guarda o que já guardava hoje para certificados/CSRs, com uma extensão mínima para rastrear origem HSM.

## Entidades

### Chave HSM (não persistida localmente — vive só no HSM)

Representa um par de chaves gerado e mantido dentro do HSM. Consultada sob demanda via busca (`listObjs`), nunca copiada para o banco local.

| Campo | Tipo | Origem | Notas |
|---|---|---|---|
| `label` | string | HSM | identificador único do objeto na partição; chave de busca/lookup em todas as operações |
| `key_type` | string | HSM | ex.: `rsa2048`, `rsa4096` |
| `exportable` | bool | HSM | determina se `export_pfx` é permitido (FR-008) |
| `has_certificate` | bool | HSM | indica se já há certificado associado |
| `created_at` | datetime | HSM | quando disponibilizado pelo SDK |

**Regras de validação**:
- `label` não pode colidir com um label já existente no HSM (FR-002) — validado pelo próprio HSM; a aplicação repassa o erro.
- Toda operação subsequente (CSR, importação, exportação) exige que `label` exista no HSM (FR-004).

### CSR (persistida — reaproveita tabela `csrs` existente)

Sem mudança de schema. Uma CSR gerada a partir de uma chave HSM é salva exatamente como uma CSR gerada localmente hoje, com `hsm_label` guardado apenas no `detail` do log de auditoria (não há coluna própria — segue o padrão atual, que não distingue engine na tabela `csrs`).

### Certificado importado (persistida — extensão da tabela `certificates` existente)

Extensão mínima da tabela já existente:

| Campo | Tipo | Mudança | Notas |
|---|---|---|---|
| `hsm_label` | TEXT, nullable | **NOVO** | rótulo da chave HSM associada, quando `source='hsm'` |
| `source` | TEXT | já existente | passa a aceitar o valor `'hsm'` além de `'importado'` e demais valores já usados |

Demais campos (`cn`, `sans`, `subject`, `issuer`, `serial`, `thumbprint_sha1`, `not_before`, `not_after`, `key_type`, `file_path`) são preenchidos do mesmo jeito que hoje (parse do certificado via `certparse`), independente da origem ser upload manual ou importação no HSM.

**Regras de validação**:
- Certificado só é aceito se a chave pública do certificado corresponder à chave pública do label alvo no HSM (FR-006) — validação feita pelo provider antes de gravar em `certificates`.

### Pacote exportado (PFX/P12) — não persistido, artefato de download

Gerado sob demanda e devolvido como download; não fica salvo em disco/banco além do log de auditoria (mesmo padrão de outros exports do sistema).

| Campo | Tipo | Notas |
|---|---|---|
| `format` | string | `pfx` ou `p12` (aliases do mesmo formato PKCS#12) |
| `password_ref` | string | referência à senha gerada pelo módulo de senhas (não o valor em texto puro no log) |
| `source_label` | string | label da chave HSM de origem |

### Resultado de busca (não persistido — transitório, resposta de `/hsm/search`)

| Campo | Tipo | Notas |
|---|---|---|
| `label` | string | |
| `key_type` | string | |
| `has_certificate` | bool | |
| `cn` | string, nullable | preenchido quando há certificado associado |
| `not_after` | datetime, nullable | validade do certificado associado, quando houver |

## Alterações de schema resumidas

- `ALTER TABLE certificates ADD COLUMN hsm_label TEXT` (nullable, sem default além de `NULL`).
- Nenhuma tabela nova é criada.
- Nenhuma mudança nas tabelas `csrs`, `activity_log`, `settings` (apenas novos valores dentro delas, não novas colunas).

## Configuração (tabela `settings`, chave-valor já existente)

| Chave | Formato | Notas |
|---|---|---|
| `hsm_dinamo_config` | JSON string | `{"host": "", "port": "", "username": "", "password": ""}` — mesmo padrão de `hsmutil_templates` |
