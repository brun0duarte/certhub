# Data Model: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

Nenhuma tabela SQL nova. Duas mudanças de dado, ambas em estruturas já existentes.

## Demanda (REQ) — sem mudança de schema

Entidade já existente (tabela `reqs`). US1 e US2 não adicionam nem removem campos — apenas expõem `sort`/`dir` na listagem (US2) e reaproveitam `req_number`/`cn`/`env`/`status` já retornados por `GET /reqs` para o filtro client-side do seletor (US1).

**Campos usados pela ordenação (US2)** — mapeados em `SORT_COLUMNS` de `app/routers/reqs.py`, espelhando `app/routers/monitor.py`:

| Chave de ordenação (`sort=`) | Coluna SQL | Notas |
|---|---|---|
| `req_number` | `r.req_number` | ordenação alfanumérica |
| `env` | `r.env` | agrupa por ambiente |
| `status` | `r.status` | agrupa por status |
| `created_at` | `r.created_at` | padrão atual, mantido como default |

**Regra de validação**: valores de `sort` fora da tabela acima caem no default (`created_at`), igual ao comportamento já existente em `monitor.py` (`SORT_COLUMNS.get(sort, SORT_COLUMNS["not_after"])`) — nunca interpolar entrada do usuário direto no `ORDER BY`.

## Perfil de conexão HSM (US4) — nova estrutura dentro do setting `hsm_dinamo_profiles`

Substitui o setting único `hsm_dinamo_config` (mantido apenas como fonte de migração, ver Transição abaixo).

| Campo | Tipo | Obrigatório | Notas |
|---|---|---|---|
| `name` | string | sim | identificador visível do perfil (ex.: "PRD", "NPRD"); único dentro da lista de profiles (FR-011) |
| `host` | string | não* | IP/hostname do HSM |
| `port` | string | não* | porta do HSM |
| `username` | string | não* | usuário da partição |
| `password` | string | não* | senha da partição — mesmo tratamento de armazenamento já usado hoje (texto no JSON de `settings`, sem criptografia adicional; ver Assumptions em `spec.md`) |

\* campos de conexão podem ficar vazios enquanto o perfil está sendo cadastrado, mas operações da aba HSM contra um perfil incompleto falham com o mesmo erro `502`/conexão que já ocorre hoje com `hsm_dinamo_config` vazio.

**Estrutura do setting `hsm_dinamo_profiles`**:

```json
{
  "active": "PRD",
  "profiles": [
    {"name": "PRD", "host": "10.0.0.1", "port": "4433", "username": "master", "password": "..."},
    {"name": "NPRD", "host": "10.0.1.1", "port": "4433", "username": "master", "password": "..."}
  ]
}
```

**Regras de validação**:
- `active` MUST corresponder a um `name` presente em `profiles`, exceto quando `profiles` está vazio (estado inicial antes de qualquer migração/cadastro) — nesse caso `active` é `""` e operações da aba HSM retornam erro claro ("nenhum perfil de HSM configurado") em vez de falha de conexão genérica.
- `name` duplicado é rejeitado na escrita (FR-011).
- Não é permitido remover ou desativar o `profiles[i]` cujo `name == active` sem antes trocar `active` para outro perfil existente (FR-012) — último perfil restante nunca pode ser removido enquanto for o único.

**Transição do formato antigo (`hsm_dinamo_config` → `hsm_dinamo_profiles`)**:

- Na primeira leitura de configuração HSM após o deploy desta funcionalidade, se `hsm_dinamo_profiles.profiles` estiver vazio e `hsm_dinamo_config` tiver `host` não vazio, cria automaticamente `{"name": "Padrão", ...campos de hsm_dinamo_config}`, define como `active`, e persiste em `hsm_dinamo_profiles` (FR-013). `hsm_dinamo_config` continua existindo no banco (não é apagado) apenas como registro legado, mas deixa de ser lido pelas operações da aba HSM.
- Se `hsm_dinamo_config` também estiver vazio (instalação nova), `hsm_dinamo_profiles` nasce com `profiles: []` e `active: ""`.

## Relação entre as entidades

Nenhuma relação nova entre Demanda e Perfil de HSM — são independentes. A demanda vinculada a uma operação de HSM (`req_id` opcional em `POST /hsm/keys/{label}/csr`, já existente) continua sendo apenas uma referência de auditoria/organização de pasta, sem relação com qual perfil de conexão está ativo no momento da chamada.
