# Research: Automação Real dos Providers de Instalação

## 1. Infraestrutura de execução já existe por completo — só falta o corpo de cada `install()`

**Decision**: Não mexer em `app/routers/reqs.py::run_install`, `install_runs`, histórico por local, nem na UI de "Instalar"/"🕘 Histórico" já existentes (`app/static/app.js`). Só substituir o corpo de cada `install()` em `app/services/installers/providers.py` (hoje todos retornam `_not_implemented()` incondicionalmente).

**Rationale**: `run_install` já chama `provider.install(...)`, já grava `install_runs` com `status`/`output`/`error`, já atualiza `install_locations.status` pra `instalado`/`falhou`, já loga em `activity_log`. Essa orquestração é agnóstica de provider — nenhuma mudança necessária ali.

## 2. Credenciais de acesso ao ALVO nunca ficam no CertHub — mas isso é sobre credencial do SERVIDOR final, não do provedor de nuvem

**Decision**: Distinguir dois tipos de "credencial" nos 10 providers, tratados de forma diferente:
- **Credencial de conta/API do provedor de nuvem** (ex.: service principal do Azure, access key da AWS, token da Azion, EdgeGrid da Akamai): é uma credencial *compartilhada* da organização pra falar com aquele serviço, não uma credencial de um servidor específico — mesmo nível de confiança já usado hoje pra `hsm_dinamo_profiles`/`hsmutil_templates` (setting JSON, protegido do mesmo jeito). Fica configurável em Configurações, uma vez, reaproveitada por qualquer local daquele tipo.
- **Credencial de acesso ao servidor alvo** (Apache/Nginx/IIS/Mainframe via SSH/WinRM): aqui sim se aplica o princípio já documentado em `app/services/installers/base.py` — "Credenciais de acesso ao alvo NUNCA passam por aqui... o local só guarda uma referência (`credential_ref`)" pro BeyondTrust. **Confirmado por grep no repositório: não existe nenhuma integração com API do BeyondTrust hoje** — `credential_ref` é só um campo de texto livre, de convenção humana (usuário abre o BeyondTrust manualmente e copia a senha).

**Consequência prática**: os 5 providers de nuvem (Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion, Akamai) conseguem ficar **totalmente funcionais** nesta rodada — a credencial é de conta/API, cabe em Configurações. Já os providers de acesso remoto a servidor (Apache, Nginx, IIS) e o Mainframe **não conseguem buscar a senha/chave real de acesso sozinhos** sem uma integração nova com a API do BeyondTrust, que está fora do escopo descrito pelo usuário nesta conversa. Isso é reportado de volta ao usuário como achado de pesquisa, não decidido silenciosamente.

**Decision (US2/US3 nesta rodada)**: para Apache/Nginx/IIS/Mainframe, `install()` passa a ser real até o ponto em que precisa da credencial do alvo — valida a configuração do local (host, caminhos, etc.), tenta resolver o que der (ex.: confirmar que o host responde na porta configurada), e retorna um erro específico e honesto: *"Automação requer buscar a credencial '{credential_ref}' no BeyondTrust — integração ainda não implementada; use o registro indicado manualmente."* Isso já é estritamente melhor que o texto genérico atual (FR-002/FR-003), sem violar o princípio de segurança já estabelecido, e sem inventar uma integração de BeyondTrust não pedida.

**Alternatives considered**: Pedir a senha/chave direto no formulário do local, gravada no CertHub — rejeitado, contradiz um princípio de segurança já documentado explicitamente no código (`base.py`), não é uma decisão pra tomar sem confirmação explícita do usuário. Construir uma integração real com a API do BeyondTrust agora — rejeitado por escopo (não foi pedido, é um projeto à parte, com autenticação própria a descobrir).

## 3. Bibliotecas por provedor — minimizar dependência nova, mas aceitar o necessário

O projeto hoje tem só 5 dependências (`requirements.txt`: fastapi, uvicorn, cryptography, python-multipart, itsdangerous) — filosofia claramente enxuta (a integração HSM usou um bridge Node em vez de puxar SDK Python, por exemplo). Ainda assim, automação de nuvem real exige HTTP/assinatura de request:

| Provider | Mecanismo | Biblioteca | Por quê |
|---|---|---|---|
| Azure Key Vault | REST + OAuth2 client-credentials (Azure AD) | `requests` | Fluxo simples de token + REST — não precisa do SDK pesado da Azure pra isso. |
| AWS Certificate Manager | API AWS (SigV4) | `boto3` | Assinatura SigV4 é complexa e sensível pra reimplementar à mão — a própria AWS não oferece alternativa REST simples sem SDK. Mesma lib cobre ACM e Secrets Manager. |
| AWS Secrets Manager | API AWS (SigV4) | `boto3` (mesma dependência acima) | — |
| Azion | REST + token Bearer | `requests` | API simples, token fixo, sem necessidade de SDK. |
| Akamai (CPS) | REST + assinatura EdgeGrid (HMAC) | `edgegrid-python` | Assinatura HMAC própria da Akamai — lib pequena e dedicada, mais seguro que reimplementar a mão. |

**Decision**: adicionar `requests`, `boto3`, `edgegrid-python` a `requirements.txt` — as três dependências mínimas cobrindo os 5 providers de nuvem. Nenhuma dependência nova pra Apache/Nginx/IIS/Mainframe nesta rodada (ver #2 — ficam parcialmente implementados, sem executar a parte que dependeria de SSH/WinRM real).

**Alternatives considered**: usar `httpx` no lugar de `requests` — equivalente, mas o resto do projeto já é 100% síncrono (FastAPI com rotas `def`, não `async def`) e `requests` é a escolha mais direta nesse estilo, sem trazer complexidade assíncrona nova.

## 4. Onde ficam as credenciais de conta/API dos 5 providers de nuvem

**Decision**: um novo setting `installer_credentials` (JSON), mesmo padrão de `hsm_dinamo_profiles`/`hsmutil_templates` — validado como JSON em `PUT /settings` (`JSON_KEYS`), editado numa nova seção em Configurações. AWS Certificate Manager e AWS Secrets Manager compartilham o mesmo bloco de credencial (`aws`), já que normalmente são a mesma conta AWS — evita duplicar campo de access key/secret key.

```json
{
  "keyvault_azure": {"tenant_id": "", "client_id": "", "client_secret": ""},
  "aws": {"access_key_id": "", "secret_access_key": "", "region": "sa-east-1"},
  "azion": {"api_token": ""},
  "akamai": {"client_token": "", "client_secret": "", "access_token": "", "host": ""}
}
```

**Rationale**: mesmo mecanismo já usado e testado pelo resto do sistema — sem tabela nova, sem novo padrão de proteção a inventar.

## 5. Balanceador e Mainframe — protocolo pouco padronizado

**Decision**: Balanceador (`config_fields`: tipo CTC/DTD, certificate_name, host) não tem nenhuma API/SDK referenciada em nenhum lugar do sistema — "CTC"/"DTD" parecem ser identificadores internos de tipo de balanceador da organização, não um padrão de mercado reconhecível (ex.: F5 iControl, Citrix ADC NITRO). Sem informação adicional, `install()` passa a validar a configuração de verdade e retornar um erro específico: *"Automação para balanceador tipo {tipo} ainda não tem integração definida — nenhuma API conhecida associada a esse tipo. Descreva o mecanismo de gestão desse balanceador pra viabilizar."* Mainframe (RACDCERT) reaproveita a mesma limitação de credencial de acesso ao alvo do item #2 (host USS via SSH) — mesmo tratamento honesto de "bloqueado por credencial", já que RACDCERT em si é um comando REXX/USS rodável via SSH uma vez a sessão exista.

**Rationale**: consistente com FR-003 (explicar especificamente por que não é possível ainda, por tipo) — evita inventar uma integração sem protocolo conhecido.

## Resumo (Technical Context)

- Novas dependências: `requests`, `boto3`, `edgegrid-python` (só pros 5 providers de nuvem).
- Novo setting `installer_credentials` (JSON), mesmo padrão de settings já existente — sem tabela nova.
- Apache/Nginx/IIS/Mainframe ficam com validação real de configuração + erro honesto e específico sobre a lacuna de integração com BeyondTrust — não é uma regressão de escopo, é a mesma pesquisa reportada de volta ao usuário antes de inventar uma integração não pedida.
- Balanceador fica com erro honesto sobre a falta de protocolo conhecido.
