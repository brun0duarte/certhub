# Data Model: Demandas de Revogação de Certificados

## `reqs` — colunas novas

Tabela já existente. `demand_type='revogacao'` já é um valor aceito hoje (sem coluna nova pra isso). Três colunas novas, todas nullable/com default, aditivas:

| Coluna | Tipo | Notas |
|---|---|---|
| `revoke_destination` | TEXT, default `''` | Um de `internacional`, `serpro`, `ac_interna_nprd`, `ac_interna_prd`, `outros`. Obrigatório no nível de aplicação quando `demand_type='revogacao'` (FR-004) — sem CHECK no banco, mesma abordagem já usada pra `demand_type` (validação em Python, não em SQL). |
| `revoke_destination_other` | TEXT, default `''` | Texto livre, preenchido só quando `revoke_destination='outros'` (FR-005). |
| `revoke_cert_id` | INTEGER, nullable, `REFERENCES certificates(id) ON DELETE SET NULL` | Vínculo com o certificado alvo, preenchido quando a demanda nasce do inventário (US1); `NULL` quando aberta do zero (US2/AC3). Mesma convenção de `install_locations.cert_id`. |

**Regras de validação** (nível de aplicação, em `create_req`/`update_req`):
- `demand_type='revogacao'` MUST ter `revoke_destination` preenchido com um dos 5 valores válidos antes de a demanda poder ser salva (FR-004).
- `revoke_destination='outros'` MUST ter `revoke_destination_other` não vazio (FR-005).
- Abrir uma nova demanda de revogação (`demand_type='revogacao'`) quando já existe outra demanda de revogação com `status != 'concluida'` e mesmo `revoke_cert_id` (quando presente) ou mesmo `cn`+`env` (quando `revoke_cert_id` é nulo) MUST gerar um aviso não-bloqueante — mesma ideia de `find_existing_active_req`, mas sem o bloqueio rígido (409) que `geracao`/`recebimento` usam (FR-010): o endpoint retorna a demanda duplicada encontrada; o cliente decide se confirma mesmo assim (reenviando com uma flag, ver `contracts/reqs-revoke-api.md`).

## `certificates` — sem coluna nova, `lifecycle_status` ganha um valor novo

Nenhuma coluna nova. O valor `revogado` passa a ser aceito em `lifecycle_status` (hoje: `pedido`, `instalado`, `em_inventario`, `reservado`, `excluir`, `fim_de_vida`, `em_renovacao`).

**Regra de transição**: quando uma demanda de revogação com `revoke_cert_id` preenchido é marcada como `concluida`, `certificates.lifecycle_status` do certificado referenciado por `revoke_cert_id` MUST ser atualizado pra `revogado` automaticamente (parte do mesmo `PUT /reqs/{id}`, não uma ação separada) — ver `contracts/reqs-revoke-api.md`.

## Novo conceito: Provider de revogação (não persistido — vive só no backend)

Não é uma entidade de banco — é a abstração de serviço que resolve, a partir de `revoke_destination`, qual implementação tratar a ação "solicitar revogação" (US3, FR-009). Um provider por destino:

| `revoke_destination` | Provider |
|---|---|
| `internacional` | `InternacionalRevocationProvider` |
| `serpro` | `SerproRevocationProvider` |
| `ac_interna_nprd` | `AcInternaRevocationProvider(ambiente="nprd")` |
| `ac_interna_prd` | `AcInternaRevocationProvider(ambiente="prd")` |
| `outros` | `OutrosRevocationProvider` |

Todos implementam a mesma interface (`revoke(cn, serial, thumbprint, reason="") -> dict`) e, nesta fase, sempre retornam `{"ok": False, "code": "NOT_CONNECTED", "output": "..."}` — nenhuma persistência própria, nenhuma chamada de rede (FR-008). Ver `research.md` #6.

## Relação entre as entidades

```
reqs (demand_type='revogacao')
  │
  ├─ revoke_destination ──► resolve qual RevocationProvider tratar a ação (não persistido)
  │
  └─ revoke_cert_id ───────► certificates.id (opcional — nulo se aberta sem vínculo com o inventário)
                                │
                                └─ lifecycle_status ──► 'revogado' quando a demanda é concluída
```

Nenhuma relação nova entre `reqs` e `install_locations`/`csrs`/`activity_log` — demandas de revogação usam a mesma tabela `activity_log` já existente pra registrar a ação (mesmo padrão de `log_activity` já usado por toda ação relevante do sistema).
