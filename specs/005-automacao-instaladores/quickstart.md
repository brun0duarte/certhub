# Quickstart: Automação Real dos Providers de Instalação

Guia de validação manual das 3 user stories. Assume app rodando localmente com usuário autenticado.

## US1 — Provedores de nuvem (Azure, AWS×2, Azion, Akamai)

1. Sem nenhuma credencial configurada, cadastre um local do tipo "Azure Key Vault" numa demanda e acione "Instalar".
2. **Esperado**: erro específico "Credenciais do Azure Key Vault não configuradas em Configurações" (não mais o texto genérico único).
3. Em Configurações, preencha `installer_credentials.keyvault_azure` com um service principal real (tenant/client id/secret) de um Key Vault de teste.
4. Acione "Instalar" de novo.
5. **Esperado**: tentativa real — sucesso se o vault/certificado existirem e a credencial for válida; senão, o erro real da API do Azure (não mais o texto genérico).
6. Repita os passos 1-5 pros outros 4 tipos (AWS Certificate Manager, AWS Secrets Manager, Azion, Akamai), cada um com sua própria credencial em `installer_credentials`.

## US2 — Servidores via acesso remoto (Apache, Nginx, IIS)

1. Cadastre um local do tipo Apache (ou Nginx/IIS) com host/caminhos preenchidos e acione "Instalar".
2. **Esperado**: mensagem específica mencionando que a automação depende de buscar a credencial (`credential_ref`) no BeyondTrust, e que essa integração ainda não existe — não mais o texto genérico único, mas também não uma tentativa de conexão sem credencial real (research.md #2).
3. Repita sem preencher os campos obrigatórios do local (ex.: sem host).
4. **Esperado**: erro específico de configuração faltando, antes mesmo de chegar na explicação sobre BeyondTrust.

## US3 — Balanceador e Mainframe

1. Cadastre um local do tipo Balanceador e acione "Instalar".
2. **Esperado**: mensagem específica explicando que não há integração conhecida pro tipo informado (research.md #5) — não mais o texto genérico único.
3. Cadastre um local do tipo Mainframe e acione "Instalar".
4. **Esperado**: mesma explicação de bloqueio por credencial (BeyondTrust) usada em US2, já que Mainframe também depende de acesso remoto ao host USS.

## Testes automatizados de referência

- Novo `tests/test_installer_providers.py`: para cada um dos 5 providers de nuvem — sem credencial configurada (erro específico), com credencial + chamada HTTP/boto3 mockada com sucesso (ok=True), com credencial + chamada mockada com erro (mensagem real repassada). Para Apache/Nginx/IIS/Mainframe/Balanceador — confirma a mensagem de bloqueio específica por tipo, e que nenhuma tentativa de conexão real é feita.
- Extensão de `tests/test_settings.py` (se aplicável): validação de `installer_credentials` como JSON.
