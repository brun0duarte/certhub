# Feature Specification: Importação Completa pro Azure Key Vault

**Feature Branch**: `008-import-azure-key-vault`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "vamos planejar a instalação de certificados na azure, atraves da api, para isso precisamos fazer essa chamada api para https://kv-certhub.vault.azure.net/certificates/vpn-bancofic-com-br/import?api-version=7.4 com o json no body incluindo o bloco `policy` (key_props/secret_props), similar ao da azion — a resposta do Key Vault (id, kid, sid, x5t, cer, attributes, policy) devemos exibir as informações relevantes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver o resultado real da importação no Key Vault (Priority: P1)

Hoje, quando a instalação automática num local do tipo Azure Key Vault dá certo, o sistema só mostra uma frase genérica ("Certificado importado no Key Vault 'X' como 'Y'."). O usuário responsável pela demanda precisa conferir, sem sair do CertHub, se o certificado que subiu é realmente o esperado: qual a validade retornada pelo Key Vault, a impressão digital (thumbprint) do certificado versionado lá, e o identificador da versão criada — do mesmo jeito que já acontece hoje pra Azion (ID, status, validade, algoritmo da chave aparecem no resultado da instalação).

**Why this priority**: É o pedido central desta feature — sem isso, o usuário segue tendo que abrir o portal do Azure manualmente pra confirmar que a importação funcionou como esperado, o que anula boa parte do ganho da automação.

**Independent Test**: Ter um local Azure Key Vault configurado com credenciais válidas, acionar "Instalar", e confirmar que a mensagem de sucesso mostra thumbprint, validade (não antes de / não depois de) e identificador da versão do certificado — não apenas "importado com sucesso".

**Acceptance Scenarios**:

1. **Given** a importação no Key Vault é aceita (HTTP 200), **When** o sistema processa a resposta, **Then** o resultado exibido ao usuário inclui a validade do certificado (data de início e de expiração) e o thumbprint (x5t) retornados pelo Key Vault.
2. **Given** a importação no Key Vault é aceita, **When** o sistema processa a resposta, **Then** o resultado exibido inclui o identificador da versão do certificado criada no vault (o valor final do campo `id` retornado), permitindo localizar exatamente aquela versão no portal do Azure depois.
3. **Given** a resposta do Key Vault vem em um formato inesperado (campo ausente ou não decodificável), **When** o sistema tenta montar o resumo, **Then** a instalação continua sendo registrada como sucesso (a importação de fato ocorreu) e o sistema mostra a mensagem genérica de sucesso, sem quebrar nem mostrar erro por causa só da formatação do resumo.

---

### User Story 2 - Requisição de importação alinhada com a política real do certificado (Priority: P2)

Hoje a chamada de importação enviada pelo sistema não informa a política do certificado (tipo/tamanho de chave, se a chave pode ser exportada, tipo de conteúdo do segredo) — só manda o PFX e a senha. O usuário quer que a requisição sempre declare essa política explicitamente, do mesmo jeito que já validou manualmente que funciona (chave RSA 2048 exportável, sem reaproveitar chave existente, conteúdo do tipo PKCS#12), pra garantir que o Key Vault trate o certificado importado de forma previsível (ex.: permitir exportar a chave depois, quando necessário).

**Why this priority**: Complementa a User Story 1 — a política correta na requisição é o que garante que os dados mostrados na resposta (tamanho de chave, exportabilidade) reflitam o que o usuário realmente espera; sem isso o Key Vault pode aplicar uma política padrão divergente.

**Independent Test**: Acionar "Instalar" num local Azure Key Vault e inspecionar (via log/depuração) que a requisição enviada ao Key Vault contém o bloco de política com chave RSA 2048 exportável e tipo de conteúdo PKCS#12, igual ao testado manualmente.

**Acceptance Scenarios**:

1. **Given** um local Azure Key Vault configurado, **When** o sistema envia a requisição de importação, **Then** o corpo da requisição inclui a política do certificado (chave RSA 2048, exportável, sem reúso de chave, conteúdo PKCS#12) — não apenas o PFX e a senha.

### Edge Cases

- O Key Vault rejeita a importação por falta de permissão (RBAC não atribuído ao chamador): a mensagem de erro real do Key Vault continua sendo repassada ao usuário sem alteração (comportamento já existente, fora do escopo desta feature).
- A REQ ainda não tem chave gerada via HSM nem PFX enviado manualmente: a instalação falha antes mesmo de montar a requisição, com a mensagem já existente pedindo pra gerar a chave/CSR primeiro (sem mudança).
- O certificado importado já existe no vault com o mesmo nome (nova versão de um certificado existente): a resposta do Key Vault ainda assim deve ser resumida normalmente, mostrando a validade e o thumbprint da nova versão criada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST incluir, no corpo da requisição de importação ao Azure Key Vault, um bloco de política do certificado especificando: chave RSA de 2048 bits, chave exportável, sem reaproveitamento de chave existente, e tipo de conteúdo do segredo como PKCS#12.
- **FR-002**: Quando a importação for aceita pelo Key Vault, o sistema MUST extrair da resposta e exibir ao usuário: a data de início de validade, a data de expiração e o thumbprint (x5t) do certificado importado.
- **FR-003**: Quando a importação for aceita pelo Key Vault, o sistema MUST exibir ao usuário o identificador da versão do certificado criada, de forma que essa versão possa ser localizada no portal do Azure.
- **FR-004**: Se a resposta do Key Vault não puder ser interpretada para montar o resumo (campo ausente, certificado não decodificável), o sistema MUST ainda assim registrar a instalação como bem-sucedida e exibir uma mensagem de sucesso genérica, sem tratar isso como falha da instalação.
- **FR-005**: O sistema MUST continuar repassando ao usuário o erro real retornado pelo Key Vault quando a importação falhar (autenticação, permissão, requisição inválida), sem alterar esse comportamento já existente.

### Key Entities

- **Resultado de instalação (Key Vault)**: resumo mostrado ao usuário após uma importação bem-sucedida — inclui validade (início/expiração), thumbprint e identificador de versão do certificado no vault. É o equivalente, para o destino Azure Key Vault, do resumo hoje já exibido para o destino Azion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Após uma importação bem-sucedida no Azure Key Vault, o usuário consegue confirmar a validade e o thumbprint do certificado importado sem sair do CertHub, em 100% das instalações concluídas com sucesso.
- **SC-002**: Zero instalações que tiveram sucesso real no Key Vault passam a ser exibidas como falha só por causa de uma resposta em formato inesperado ao montar o resumo.

## Assumptions

- A política de chave usada será a mesma já validada manualmente com o Azure (RSA 2048, exportável, sem reúso de chave, conteúdo PKCS#12) — não há necessidade de tornar isso configurável por local nesta etapa.
- A resolução de chave/certificado (via HSM da REQ ou PFX enviado manualmente) e a autenticação no Azure AD já implementadas no provider `AzureKeyVaultProvider` permanecem sem alteração; o escopo aqui é o corpo da requisição de importação e o processamento da resposta.
- "Informações relevantes" da resposta, para o usuário final, são: validade (início/expiração), thumbprint e identificador de versão — replicando o mesmo nível de detalhe já entregue hoje para a Azion (ID, status, validade, algoritmo de chave).
