# Contract: Demandas de revogação — extensão de `POST/PUT /reqs` + nova ação `POST /reqs/{id}/revoke`

Extensões dos endpoints já existentes (`app/routers/reqs.py`), mesma autenticação de sessão. `demand_type='revogacao'` já é aceito hoje por `ReqIn`/`ReqUpdate` (sem mudança de tipo) — os campos abaixo são novos.

## POST /reqs (extensão de `ReqIn`)

**Novos campos** (opcionais exceto quando `demand_type='revogacao'`):

| Campo | Tipo | Obrigatório quando `demand_type='revogacao'` | Notas |
|---|---|---|---|
| `revoke_destination` | string | sim | um de `internacional`, `serpro`, `ac_interna_nprd`, `ac_interna_prd`, `outros` |
| `revoke_destination_other` | string | só se `revoke_destination='outros'` | texto livre |
| `revoke_cert_id` | int, nullable | não | id de `certificates`, quando aberta a partir do inventário |
| `force_duplicate` | bool, default `false` | não | ver seção de duplicidade abaixo |

**Validação**:
- `demand_type='revogacao'` sem `revoke_destination` → `400 "Escolha o destino da revogação."`
- `revoke_destination='outros'` sem `revoke_destination_other` → `400 "Descreva o destino quando escolher 'Outros'."`
- `revoke_destination` fora dos 5 valores válidos → `400 "Destino de revogação inválido."`

**Verificação de duplicidade** (FR-010, não bloqueante):
- Se já existe uma demanda de revogação com `status != 'concluida'` para o mesmo `revoke_cert_id` (ou mesmo `cn`+`env`, se `revoke_cert_id` for nulo) e `force_duplicate` não foi enviado como `true` → `409` com mensagem de texto mencionando o `req_number` da demanda em aberto (mesmo padrão de mensagem já usado pelo bloqueio de `geracao`/`recebimento`, só que aqui o frontend intercepta o `409`, confirma com o usuário, e reenvia a mesma chamada com `force_duplicate: true`).
- Com `force_duplicate: true`, a demanda é criada normalmente mesmo havendo uma duplicada em aberto.

**Response 200**: formato inalterado (linha de `reqs`, agora incluindo os 3 campos novos).

## PUT /reqs/{id} (extensão de `ReqUpdate`)

Mesmos 3 campos (`revoke_destination`, `revoke_destination_other`, `revoke_cert_id`) editáveis via `PATCH`-like update, mesma validação do `POST` quando presentes no corpo.

**Efeito colateral novo**: quando `status` muda para `concluida` numa demanda com `demand_type='revogacao'` **e** `revoke_cert_id` não nulo, o servidor MUST atualizar `certificates.lifecycle_status` desse certificado para `revogado` na mesma transação (data-model.md). Não há guarda de "precisa ter certificado vinculado" pra `revogacao` concluir (diferente de `geracao`/`recebimento`/`renovacao`) — uma demanda de revogação aberta do zero (sem `revoke_cert_id`) pode ser concluída normalmente.

## POST /reqs/{id}/revoke *(novo)*

Aciona o provider de revogação correspondente ao `revoke_destination` da demanda — ação explícita, não automática (US3, FR-007/FR-008/FR-009). Só válido pra demandas com `demand_type='revogacao'`.

**Request**: sem corpo (usa os dados já salvos na demanda — `cn`, e quando disponível `revoke_cert_id` → `certificates.serial`/`thumbprint_sha1`).

**Response 200** (sempre — mesmo sem conexão real):
```json
{
  "ok": false,
  "code": "NOT_CONNECTED",
  "output": "Revogação automática via <destino> ainda não está conectada — confirme manualmente após revogar por fora do sistema.",
  "destination": "serpro"
}
```

**Erros**: `404` se a demanda não existe ou não é do tipo `revogacao`.

**Efeito colateral**: registra em `activity_log` (`hsm`-style, ação `revogacao_solicitada`) que a ação foi acionada e qual foi o resultado — mesmo sendo sempre "não conectado" nesta fase, fica registrado que o usuário tentou/foi lembrado de fazer manualmente.

## GET /reqs (sem mudança de contrato)

Filtros já existentes (`demand_type`, `search`, `env`, `status`, `sort`, `dir` — specs/002) já funcionam com `demand_type=revogacao` sem nenhuma mudança — a nova aba de Revogação (US2) usa exatamente o mesmo endpoint, só filtrando por esse tipo, igual a como `views.instalacao` já filtra por `demand_type='instalacao'`.
