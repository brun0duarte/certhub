# Quickstart: Validar a Importação Completa pro Azure Key Vault

## Pré-requisitos

- Ambiente local do CertHub rodando (`uvicorn app.main:app --reload`, conforme README).
- Credenciais do Azure Key Vault configuradas em Configurações → `installer_credentials.keyvault_azure` (`tenant_id`, `client_id`, `client_secret`) — ou mockadas em teste (ver abaixo).
- Uma REQ com chave gerada via HSM (`reqs.hsm_label` preenchido) ou PFX enviado manualmente no local, associada a um local do tipo `keyvault_azure` com `vault_name`/`certificate_name` configurados.

## Validação automatizada (unit/integration — pytest)

```bash
cd /home/bruno/cert-manager
pytest tests/test_installer_providers.py -k azure -v
```

**Esperado após a implementação**:
- `test_azure_success` (estendido): o mock de resposta do Key Vault passa a incluir `id`/`x5t`/`attributes.nbf`/`attributes.exp` realistas; o assert passa a checar que `result["output"]` contém a validade e o thumbprint, não só o nome do vault.
- Novo teste `test_azure_success_response_missing_fields` (ou nome equivalente): mock retorna 200 com corpo `{}` (sem `id`/`x5t`/`attributes`) → `result["ok"] is True` continua (FR-004), `result["output"]` cai na mensagem genérica.
- Novo teste `test_azure_request_includes_policy`: inspeciona o `json=` passado pro `requests.post` de importação e confirma a presença do bloco `policy` com `key_size: 2048`, `exportable: true`, `reuse_key: false`, `contentType: "application/x-pkcs12"` (FR-001).
- Testes já existentes (`test_azure_missing_credentials`, `test_azure_missing_key_material`, `test_azure_api_error_passed_through`) continuam passando sem alteração de comportamento.

## Validação manual end-to-end (opcional, contra um Key Vault real)

1. Atribuir a role RBAC `Key Vault Certificates Officer` ao principal usado (`az role assignment create ...`, já documentado no histórico desta REQ).
2. No CertHub, acionar "Instalar" no local Azure Key Vault da REQ.
3. **Esperado**: mensagem de sucesso no histórico do local mostra vault, nome do certificado, versão, validade e thumbprint — não mais só "Certificado importado no Key Vault 'X' como 'Y'.".
4. Conferir no portal do Azure (ou `az keyvault certificate show --vault-name {vault} --name {cert}`) que a versão/validade/thumbprint batem com o que foi exibido no CertHub.

## Critério de pronto

- `pytest tests/test_installer_providers.py -k azure` verde.
- Suíte completa (`pytest`) sem regressão.
