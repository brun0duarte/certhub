# Contract: `InstallProvider.install()` por tipo (app/services/installers/providers.py)

Interface já existente (`app/services/installers/base.py::InstallProvider`), sem mudança de assinatura — só o comportamento interno de cada classe muda. Consumido por `POST /reqs/locations/{loc_id}/run` (`run_install`, `app/routers/reqs.py`), que já trata `{"ok", "output", "error"}` de forma genérica.

## Providers com implementação real completa (US1)

### `AzureKeyVaultProvider` (`keyvault_azure`)
1. Lê `settings["installer_credentials"]["keyvault_azure"]` (`tenant_id`, `client_id`, `client_secret`).
2. Sem credencial configurada → `{"ok": False, "error": "Credenciais do Azure Key Vault não configuradas em Configurações."}`.
3. Com credencial: obtém token OAuth2 (client-credentials, `login.microsoftonline.com`), faz upload do certificado (arquivo PFX já capturado no local, `requires_file=True`) pro vault (`config["vault_name"]`, `config["certificate_name"]`) via REST.
4. Erro de autenticação/rede/recurso → repassa a mensagem real da API do Azure em `error`.

### `AwsAcmProvider` (`aws_cert_manager`) / `AwsSecretsManagerProvider` (`secrets_manager`)
1. Lê `settings["installer_credentials"]["aws"]` (`access_key_id`, `secret_access_key`, `region` — `config["region"]` do local sobrepõe o padrão se vier preenchido).
2. Sem credencial → mesmo padrão de erro específico acima, mencionando "AWS".
3. Com credencial: `boto3` client (`acm`/`secretsmanager`) — ACM usa `import_certificate`; Secrets Manager usa `put_secret_value` com as 3 chaves fixas já documentadas no `config_fields` (`tls.crt`/`tls.key`/`ca.crt`).
4. Exceções do `boto3` (`ClientError`, credencial inválida, timeout) → mensagem real repassada em `error`.

### `AzionProvider` (`azion`)
1. Lê `settings["installer_credentials"]["azion"]["api_token"]`.
2. Sem token → erro específico "Azion".
3. Com token: `POST /v4/edge_certificates` (cert+chave em texto, já documentado no provider) com header `Authorization: Token {api_token}`.
4. Erro HTTP/rede → repassa status/corpo real da resposta da Azion.

### `AkamaiProvider` (`akamai`)
1. Lê `settings["installer_credentials"]["akamai"]` (4 campos EdgeGrid).
2. Sem credencial → erro específico "Akamai".
3. Com credencial: chamada à API CPS (`enrollment_id` do `config_fields`) assinada via EdgeGrid (`edgegrid-python`).
4. Erro de assinatura/rede/API → repassa mensagem real.

## Providers com validação real + bloqueio honesto documentado (US2/US3)

### `ApacheSshProvider` (`apache`) / `NginxSshProvider` (`nginx`) / `IisWinrmProvider` (`iis`) / `MainframeRacdcertProvider` (`mainframe`)
1. Valida que os campos obrigatórios do `config_fields` estão presentes (host, caminhos, etc.) — erro específico se faltar algo.
2. Retorna: `{"ok": False, "error": "Automação requer buscar a credencial '{credential_ref}' no BeyondTrust para acessar {host} — integração com a API do BeyondTrust ainda não implementada; use o registro indicado manualmente."}` (research.md #2).
3. **Não** tenta nenhuma conexão SSH/WinRM real nesta rodada — a mensagem já deixa claro o motivo específico, sem fingir uma tentativa que não pode ser autenticada.

### `BalanceadorProvider` (`balanceador`)
1. Valida presença dos campos do `config_fields`.
2. Retorna: `{"ok": False, "error": "Automação para balanceador tipo {tipo} ainda não tem integração definida — nenhuma API conhecida associada a esse tipo."}` (research.md #5).

## Resposta a `GET /install-providers`

Sem mudança de contrato de resposta (`{label, config_fields, available, requires_file}` por tipo) — `available` continua `true` pra todos os 10 (todos têm classe registrada), sem mudança de significado dessa flag nesta feature.
