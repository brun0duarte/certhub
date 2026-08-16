# Data Model: Automação Real dos Providers de Instalação

Nenhuma tabela SQL nova. Um novo setting (JSON), reaproveitando o mecanismo já existente (`settings` key/value).

## Setting `installer_credentials` (novo)

| Campo | Tipo | Notas |
|---|---|---|
| `keyvault_azure` | objeto `{tenant_id, client_id, client_secret}` | Service principal do Azure AD, usado pro fluxo OAuth2 client-credentials. |
| `aws` | objeto `{access_key_id, secret_access_key, region}` | Compartilhado por `aws_cert_manager` e `secrets_manager` (mesma conta AWS, ver `research.md` #4). |
| `azion` | objeto `{api_token}` | Token Bearer da API da Azion. |
| `akamai` | objeto `{client_token, client_secret, access_token, host}` | Credencial EdgeGrid (4 campos, padrão Akamai). |

**Regras de validação**: mesmo tratamento já usado por `hsm_dinamo_profiles`/`hsmutil_templates` — `PUT /settings` valida que o valor é JSON bem-formado (`JSON_KEYS`); sem validação de conteúdo por campo (mesma política já aplicada às demais credenciais do sistema — a validação real acontece na tentativa de uso, não no cadastro).

## `install_locations` / `PROVIDERS` — sem mudança de schema

Nenhum campo novo em `install_locations` — `config_json` (já existente, capturado pelo formulário via `config_fields` de cada provider) e `credential_ref` (já existente, referência ao BeyondTrust) continuam suficientes. A mudança é inteiramente no comportamento de `install()` de cada classe em `app/services/installers/providers.py`.

## Resultado de `install()` — formato inalterado

Contrato já existente (`InstallProvider.install()`, `app/services/installers/base.py`): `{"ok": bool, "output": str, "error": str}`. Nenhuma mudança de forma — só o conteúdo passa a refletir uma tentativa real (ou uma explicação específica de bloqueio, quando aplicável — ver `research.md` #2 e #5) em vez do texto genérico único usado por todos os 10 tipos hoje.

## Relação entre as entidades

```
settings["installer_credentials"]  ──► resolve credencial de conta/API por tipo de provider
                                         (Azure/AWS/Azion/Akamai)

install_locations.config_json      ──► dados específicos do local (vault name, ARN, host, etc.)
install_locations.credential_ref   ──► referência ao BeyondTrust (não resolvida automaticamente
                                         nesta rodada — ver research.md #2)

PROVIDERS[location_type].install(location, req, config, credential_ref)
                                    ──► combina os três acima pra tentar a operação real
```
