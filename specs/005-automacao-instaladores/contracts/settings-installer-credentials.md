# Contract: `installer_credentials` — extensão de `GET/PUT /settings`

Novo valor em `JSON_KEYS` (`app/routers/settings.py`), mesmo mecanismo já usado por `hsm_dinamo_profiles`/`hsmutil_templates` — sem endpoint novo.

## GET /settings

Resposta ganha a chave `installer_credentials` (string JSON), default `{"keyvault_azure": {}, "aws": {}, "azion": {}, "akamai": {}}` quando nunca configurado (mesmo padrão de `DEFAULT_SETTINGS`).

## PUT /settings

Aceita `values.installer_credentials` como string JSON válida (validação já genérica de `JSON_KEYS` — sem validação de schema por campo nesta fase, mesma política das demais credenciais).

## Consumo pelos providers

`app/services/installers/providers.py` lê `json.loads(get_setting(conn, "installer_credentials"))` e acessa a chave do próprio tipo (`keyvault_azure`, `aws`, `azion`, `akamai`) — mesmo padrão de leitura já usado por `HsmUtilProvider(json.loads(get_setting(conn, "hsmutil_templates")))`.
