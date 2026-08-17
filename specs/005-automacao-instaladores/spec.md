# Feature Specification: Automação Real dos Providers de Instalação

**Feature Branch**: `005-automacao-instaladores`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "Vamos implementar todos os providers de instalação, azure, azion, aws" — mesmo padrão já usado pro HSM (função implementada de verdade, mas sem exigir conexão real disponível agora)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instalação automática nos provedores de nuvem (Priority: P1)

Hoje, ao clicar em "Instalar" num local do tipo Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion ou Akamai, o sistema sempre responde "execução automática ainda não implementada — siga o manual", mesmo já capturando toda a configuração necessária (nome do vault, conta AWS, região, nome do certificado, etc.) no formulário do local. O usuário precisa que essa ação realmente tente instalar o certificado no destino, usando a configuração já cadastrada.

**Why this priority**: São os destinos citados explicitly como prioritários e os mais usados hoje segundo o padrão de dados já existente no sistema (Azure, AWS, Azion aparecem entre os tipos de local mais comuns) — maior volume de trabalho manual evitado.

**Independent Test**: Configurar as credenciais de um dos 5 provedores (ex.: Azure Key Vault) em Configurações, cadastrar um local desse tipo numa demanda, clicar "Instalar", e confirmar que o sistema tenta a operação de verdade — sucesso se as credenciais forem válidas e o certificado existir, ou uma mensagem de erro específica (não mais o texto genérico de "não implementado") se algo faltar ou falhar.

**Acceptance Scenarios**:

1. **Given** um local do tipo Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion ou Akamai está configurado com credenciais válidas em Configurações, **When** o usuário aciona "Instalar", **Then** o sistema tenta de verdade enviar o certificado pro destino e registra o resultado real (sucesso ou falha) no histórico do local.
2. **Given** as credenciais desse provedor não foram configuradas ainda, **When** o usuário aciona "Instalar", **Then** o sistema retorna uma mensagem clara indicando que falta configurar as credenciais daquele provedor específico — não mais a mensagem genérica de "execução automática ainda não implementada".
3. **Given** as credenciais estão configuradas mas o destino está inacessível (rede, credencial expirada, recurso não existe), **When** o usuário aciona "Instalar", **Then** o sistema retorna o motivo real da falha (ex.: erro de autenticação, recurso não encontrado, timeout de rede), permitindo diagnosticar o problema sem sair do sistema.

---

### User Story 2 - Instalação automática em servidores via acesso remoto (Priority: P2)

Locais do tipo Apache, Nginx (via SSH) e IIS (via WinRM/PowerShell Remoting) já têm os campos de configuração certos (host, porta, caminhos remotos, comando de reload, store) capturados no formulário, mas "Instalar" também sempre retorna "não implementado". O usuário quer que essas instalações também sejam tentadas de verdade, usando as credenciais de acesso já referenciadas pela demanda (BeyondTrust) e a configuração do local.

**Why this priority**: Depende de acesso de rede a servidores específicos da organização (diferente de uma API de nuvem pública) — normalmente mais lento de habilitar/testar que os provedores de nuvem da User Story 1, por isso vem em seguida.

**Independent Test**: Configurar um local Apache/Nginx/IIS válido, acionar "Instalar", e confirmar que o sistema tenta a conexão remota de verdade (sucesso se acessível, ou erro específico de conexão/permissão se não).

**Acceptance Scenarios**:

1. **Given** um local do tipo Apache, Nginx ou IIS está configurado com host e caminhos válidos, **When** o usuário aciona "Instalar", **Then** o sistema tenta de verdade conectar no servidor e substituir o certificado, registrando o resultado real.
2. **Given** o servidor de destino está inacessível pela rede, **When** o usuário aciona "Instalar", **Then** o sistema retorna um erro de conexão específico (não a mensagem genérica de "não implementado").

---

### User Story 3 - Instalação automática em destinos especializados (Priority: P3)

Balanceador e Mainframe (RACDCERT) também têm formulário de configuração pronto, mas sem um protocolo de automação tão padronizado quanto os demais (não são APIs REST conhecidas nem acesso remoto genérico como SSH/WinRM). O usuário ainda quer que esses dois também deixem de responder sempre "não implementado", na medida do que for tecnicamente viável para cada um.

**Why this priority**: Menor prioridade porque são os destinos com protocolo de automação menos padronizado — o esforço de viabilizar cada um pode variar bastante, e vale entregar os dois primeiros grupos (mais previsíveis) antes.

**Independent Test**: Configurar um local Balanceador ou Mainframe, acionar "Instalar", e confirmar que o sistema tenta a operação real (ou retorna uma mensagem clara e específica sobre o que falta, se a automação para aquele tipo específico ainda não for tecnicamente viável).

**Acceptance Scenarios**:

1. **Given** um local do tipo Balanceador ou Mainframe está configurado, **When** o usuário aciona "Instalar", **Then** o sistema tenta a operação real na medida do que for tecnicamente viável, ou explica claramente e especificamente por que não é possível ainda (não mais o texto genérico único usado por todos os tipos hoje).

### Edge Cases

- Um local já foi instalado manualmente antes dessa automação existir: acionar "Instalar" nele depois da automação pronta deve funcionar normalmente (reinstala/atualiza), sem exigir nenhuma migração de dados do local existente.
- Credenciais de um provedor configuradas errado (ex.: chave de API revogada): o sistema deve mostrar o erro real retornado pelo destino, não travar nem mostrar uma mensagem genérica.
- Dois usuários acionam "Instalar" no mesmo local ao mesmo tempo: cada tentativa é registrada como uma execução própria no histórico do local (comportamento já existente, sem mudança).
- Um provedor específico (ex.: Balanceador) não tiver um jeito técnico viável de automação total: o sistema deve deixar isso explícito pro usuário em vez de fingir que tentou, mantendo o botão "Instalar" disponível apenas onde a tentativa real faz sentido.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Para os 5 tipos de local de nuvem (Azure Key Vault, AWS Certificate Manager, AWS Secrets Manager, Azion, Akamai), o sistema MUST substituir a resposta genérica "execução automática ainda não implementada" por uma tentativa real de instalação usando a configuração já capturada no formulário do local.
- **FR-002**: Para os 3 tipos de local via acesso remoto a servidor (Apache, Nginx, IIS), o sistema MUST também substituir a resposta genérica por uma tentativa real de conexão e substituição do certificado.
- **FR-003**: Para Balanceador e Mainframe, o sistema MUST tentar automação real na medida do tecnicamente viável, e quando não for possível, MUST retornar uma explicação específica daquele tipo (não a mensagem genérica hoje compartilhada por todos os 10 tipos).
- **FR-004**: O sistema MUST permitir configurar, por tipo de provedor, as credenciais/dados de acesso necessários pra automação real funcionar (ex.: credenciais de API do provedor de nuvem, ou credencial de acesso remoto ao servidor).
- **FR-005**: Quando as credenciais de um provedor não estiverem configuradas, o sistema MUST informar isso de forma clara e específica ao tentar "Instalar", em vez de tentar a operação e falhar de forma genérica.
- **FR-006**: Quando a tentativa real falhar (rede, autenticação, recurso inexistente, etc.), o sistema MUST registrar o motivo real da falha no histórico do local — mesmo mecanismo de histórico já existente, sem necessidade de tela nova.
- **FR-007**: Quando a tentativa real tiver sucesso, o sistema MUST marcar o local como instalado e registrar a execução — mesmo comportamento já existente pra qualquer instalação bem-sucedida.
- **FR-008**: O sistema MUST NOT expor nem registrar em log as credenciais de acesso de nenhum provedor em texto legível fora da tela de configuração — mesmo princípio de segurança já aplicado às demais credenciais do sistema (senha de partição do HSM, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários deixam de precisar seguir o manual passo a passo pra instalar certificados nos 5 provedores de nuvem (Azure, AWS×2, Azion, Akamai) quando as credenciais já estão configuradas — a ação "Instalar" resolve sozinha.
- **SC-002**: 100% das tentativas de instalação nos 10 tipos de local retornam uma mensagem específica daquele provedor/erro real — nenhuma tentativa retorna mais o texto genérico único "execução automática ainda não implementada" (exceto onde FR-003 explicitamente permite, pros casos tecnicamente inviáveis de Balanceador/Mainframe).
- **SC-003**: O tempo entre acionar "Instalar" e saber se funcionou ou não (e por quê) cai pra segundos, sem precisar abrir uma sessão remota manual pra verificar.

## Assumptions

- Nesta fase, a automação real é validada sem exigir que credenciais/acesso de rede de produção estejam disponíveis agora — mesmo padrão já usado pro HSM (a lógica real existe e é chamada de verdade; sem credencial configurada, o erro é "faltam credenciais", e com uma credencial inválida/destino inacessível, o erro é o erro real de conexão — nunca um sucesso fingido).
- Balanceador e Mainframe podem não ter automação 100% completa nesta rodada, dado que não têm um protocolo/API tão padronizado quanto os demais 8 tipos — o sistema deve ser honesto sobre essa limitação por tipo, em vez de bloquear a entrega dos outros 8 até resolver esses dois.
- A infraestrutura de execução, histórico e status de instalação (aba Instalação, histórico por local, `install_runs`) já existe e não precisa de nenhuma mudança — só o comportamento interno de cada provider passa de "sempre nega" pra "tenta de verdade".
- Credenciais de cada provedor seguem o mesmo padrão de proteção já usado no resto do sistema (nunca expostas em log ou na resposta da API) — sem novo requisito de criptografia além do que já existe.
