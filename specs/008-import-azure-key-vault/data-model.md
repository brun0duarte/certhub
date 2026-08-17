# Data Model: Importação Completa pro Azure Key Vault

Nenhuma tabela ou coluna nova. Esta feature não introduz uma entidade persistida própria — o resultado continua gravado no mesmo lugar de sempre (`install_runs.output`, texto livre), só o conteúdo do texto passa a ser mais detalhado.

## Resultado de instalação (Key Vault) — estrutura em memória, não persistida como campos separados

Representa o resumo montado a partir da resposta 200 do Key Vault, usado só pra compor a string de `output` (não vira linha/coluna nova em `install_runs`).

| Campo | Origem (resposta do Key Vault) | Tipo | Obrigatório pro resumo detalhado? |
|---|---|---|---|
| `vault_name` | `config.vault_name` (já existente, entrada do usuário) | string | sim (já disponível hoje) |
| `certificate_name` | `config.certificate_name` (já existente, entrada do usuário) | string | sim (já disponível hoje) |
| `version` | último segmento de `id` (path da resposta) | string | não — se ausente/mal formado, cai no fallback genérico (FR-004) |
| `not_after` | `attributes.exp` (epoch, segundos UTC) | data | não — mesmo fallback |
| `x5t` | `x5t` (thumbprint, já em base64url) | string | não — mesmo fallback |

Regra de validação (FR-004): se `version`, `not_after` ou `x5t` não puderem ser extraídos (chave ausente, tipo inesperado), o resumo detalhado não é montado — a instalação permanece `ok: true` com a mensagem genérica já existente hoje (`"Certificado importado no Key Vault '{vault}' como '{cert}'."`). Não é uma entidade com estado próprio — é derivada a cada chamada, a partir da resposta HTTP daquela chamada.

## Entidades existentes referenciadas (sem alteração)

- **`install_locations`** (`app/db.py`): fornece `config_json` (→ `vault_name`, `certificate_name`) e recebe `last_error`/`status` já hoje — sem coluna nova.
- **`install_runs`** (`app/db.py`): recebe o `output` (texto) desta feature — mesma coluna, sem alteração de schema.
- **`reqs.hsm_label`** / **`certificates`**: fonte da chave/certificado via `_resolve_key_material` (providers.py:85) — sem alteração.
