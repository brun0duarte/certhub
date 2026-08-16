# Feature Specification: Integração com HSM via API (Dinamo Networks)

**Feature Branch**: `001-integracao-hsm-dinamo`

**Created**: 2026-08-14

**Status**: Draft

**Input**: User description: "Vamos criar uma integração com o hsm via api, essa é a documentação, https://docs.dinamonetworks.io/hsm/api/ devemos ser capaz de criar chaves, criar uma csr, importar um certificado, exportar pfx, p12, realizar uma busca"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gerar chave criptográfica no HSM (Priority: P1)

Um administrador de certificados precisa gerar um novo par de chaves diretamente dentro do HSM (em vez de em software), para que a chave privada nunca saia do equipamento protegido.

**Why this priority**: É a operação fundamental — sem uma chave gerada no HSM, nenhuma das demais operações (CSR, importação de certificado, exportação) faz sentido.

**Independent Test**: Pode ser testado isoladamente solicitando a criação de uma chave com um rótulo e tipo (ex.: RSA 2048) e verificando que a chave passa a existir no HSM e é localizável por busca.

**Acceptance Scenarios**:

1. **Given** o administrador está autenticado e conectado ao HSM, **When** ele solicita a criação de uma chave informando rótulo e tipo de chave, **Then** o sistema cria a chave no HSM e confirma sucesso com o identificador/rótulo da chave.
2. **Given** já existe uma chave com o mesmo rótulo no HSM, **When** o administrador tenta criar outra chave com esse rótulo, **Then** o sistema rejeita a operação e informa que o rótulo já está em uso.

---

### User Story 2 - Gerar CSR a partir de chave do HSM (Priority: P1)

O administrador precisa gerar uma CSR (Certificate Signing Request) usando uma chave que já existe no HSM, informando os dados do certificado (CN, SANs, organização, etc.), para depois submeter essa CSR a uma autoridade certificadora.

**Why this priority**: É o caso de uso central do sistema de certificados — sem gerar CSR a partir da chave do HSM, a integração não substitui o fluxo atual em software.

**Independent Test**: Pode ser testado isoladamente escolhendo uma chave já existente no HSM, preenchendo os dados do certificado e verificando que uma CSR válida (PEM) é retornada, assinada pela chave privada do HSM.

**Acceptance Scenarios**:

1. **Given** uma chave existe no HSM, **When** o administrador solicita a geração de uma CSR para essa chave informando CN e SANs, **Then** o sistema retorna uma CSR em formato PEM assinada pela chave do HSM.
2. **Given** o rótulo de chave informado não existe no HSM, **When** o administrador tenta gerar a CSR, **Then** o sistema informa que a chave não foi encontrada e não gera CSR.

---

### User Story 3 - Importar certificado emitido para o HSM (Priority: P2)

Depois que uma autoridade certificadora emite o certificado correspondente a uma CSR gerada no HSM, o administrador precisa importar esse certificado de volta ao HSM, associando-o à chave privada correspondente.

**Why this priority**: Fecha o ciclo de vida do certificado (chave → CSR → certificado emitido → certificado associado à chave no HSM), necessário antes de exportar ou usar o certificado.

**Independent Test**: Pode ser testado isoladamente importando um arquivo de certificado (PEM/DER) para uma chave existente no HSM e confirmando, via busca, que o certificado aparece associado a essa chave.

**Acceptance Scenarios**:

1. **Given** uma chave sem certificado associado existe no HSM, **When** o administrador importa um certificado compatível com essa chave, **Then** o sistema associa o certificado à chave e confirma sucesso.
2. **Given** o certificado informado não corresponde à chave pública da chave alvo, **When** o administrador tenta importar, **Then** o sistema rejeita a importação e explica a incompatibilidade.

---

### User Story 4 - Exportar certificado e chave como PFX/P12 (Priority: P2)

O administrador precisa exportar o par certificado + chave privada armazenados no HSM em um arquivo PFX/P12 protegido por senha, para uso em sistemas que exigem esse formato (ex.: servidores web, aplicações).

**Why this priority**: É um requisito de distribuição explícito do usuário; depende das etapas anteriores (chave + certificado já existentes no HSM).

**Independent Test**: Pode ser testado isoladamente selecionando uma chave com certificado associado no HSM, solicitando exportação em PFX/P12 e verificando que o arquivo gerado abre corretamente com a senha definida e contém o certificado e a chave esperados.

**Acceptance Scenarios**:

1. **Given** uma chave com certificado associado existe no HSM e é exportável, **When** o administrador solicita a exportação em PFX/P12, **Then** o sistema gera um arquivo protegido por senha contendo o certificado e a chave privada.
2. **Given** a chave está marcada como não exportável no HSM, **When** o administrador tenta exportar, **Then** o sistema informa que a exportação não é permitida para essa chave.

---

### User Story 5 - Buscar chaves e certificados no HSM (Priority: P3)

O administrador precisa localizar rapidamente chaves e certificados existentes no HSM, filtrando por critérios como rótulo, CN ou status (com/sem certificado associado), para acompanhar o inventário sem depender de ferramentas externas.

**Why this priority**: É uma funcionalidade de apoio às demais (evita duplicidade de rótulos, ajuda a localizar o alvo de importação/exportação), mas o sistema pode operar de forma limitada sem ela.

**Independent Test**: Pode ser testado isoladamente realizando uma busca por um termo conhecido (rótulo ou CN) e verificando que os resultados retornados correspondem ao que existe no HSM.

**Acceptance Scenarios**:

1. **Given** existem chaves e certificados no HSM, **When** o administrador busca por um rótulo ou CN parcial, **Then** o sistema retorna a lista de itens correspondentes com seus principais atributos (rótulo, tipo, status do certificado).
2. **Given** nenhum item corresponde ao critério de busca, **When** o administrador executa a busca, **Then** o sistema informa que nenhum resultado foi encontrado, sem erro.

---

### Edge Cases

- O que acontece quando o HSM está indisponível ou a conexão falha durante qualquer operação (criação de chave, CSR, importação, exportação, busca)? O sistema deve informar claramente a falha de comunicação, sem deixar o registro local em estado inconsistente.
- Como o sistema trata timeout de uma operação no HSM (ex.: geração de chave demorada)?
- O que acontece se o usuário tentar importar um certificado expirado ou já revogado?
- Como o sistema se comporta se a busca retornar um volume muito grande de resultados (paginação/limite)?
- O que acontece se duas operações tentarem usar o mesmo rótulo de chave simultaneamente (condição de corrida)?
- Como o sistema trata a perda de conexão no meio de uma exportação de PFX/P12 (arquivo parcial)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir a criação de uma chave criptográfica diretamente no HSM, informando rótulo e tipo de chave (ex.: RSA 2048, RSA 4096), sem que a chave privada seja exposta fora do HSM.
- **FR-002**: O sistema DEVE impedir a criação de uma chave com rótulo já existente no HSM, apresentando mensagem de erro clara.
- **FR-003**: O sistema DEVE permitir a geração de uma CSR usando uma chave já existente no HSM, informando CN, SANs e demais atributos do certificado (organização, país, etc.), retornando a CSR em formato PEM.
- **FR-004**: O sistema DEVE impedir a geração de CSR para um rótulo de chave inexistente no HSM, informando o erro ao usuário.
- **FR-005**: O sistema DEVE permitir a importação de um certificado (emitido por uma CA) para o HSM, associando-o à chave privada correspondente já existente.
- **FR-006**: O sistema DEVE validar que o certificado importado corresponde à chave pública da chave alvo antes de concluir a importação, rejeitando importações incompatíveis.
- **FR-007**: O sistema DEVE permitir a exportação do par certificado + chave privada de uma entrada do HSM em formato PFX/P12, protegido por senha.
- **FR-008**: O sistema DEVE impedir a exportação de chaves marcadas como não exportáveis no HSM, informando o motivo ao usuário.
- **FR-009**: O sistema DEVE permitir a busca de chaves e certificados armazenados no HSM por critérios como rótulo e/ou CN, retornando os principais atributos de cada resultado (rótulo, tipo de chave, presença ou não de certificado associado, validade do certificado quando houver).
- **FR-010**: O sistema DEVE informar de forma clara quando uma busca não retorna resultados, sem tratar isso como erro.
- **FR-011**: O sistema DEVE registrar (log/auditoria) toda operação realizada no HSM (criação de chave, geração de CSR, importação, exportação, busca), incluindo usuário responsável e resultado (sucesso/falha), consistente com o padrão de auditoria já usado nas demais operações de certificado do sistema.
- **FR-012**: O sistema DEVE apresentar mensagem de erro compreensível ao usuário quando o HSM estiver indisponível ou a comunicação falhar, sem persistir informação inconsistente no restante do sistema.
- **FR-013**: O sistema DEVE autenticar-se junto ao HSM usando host/endereço do HSM e usuário/senha da partição configurados nas telas de administração já existentes (padrão de conexão do cliente Dinamo — sem certificado mTLS nem token de API nesta fase).
- **FR-014**: Ao exportar em PFX/P12, o sistema DEVE seguir a política de senhas já existente no módulo de senhas do sistema para gerar/gerenciar a senha de proteção do arquivo, mantendo consistência com o restante do app.
- **FR-015**: A busca de chaves e certificados DEVE retornar apenas objetos da partição do HSM associada à conexão configurada para este sistema (a conexão já é escopada por partição; não há acesso a objetos de outras partições/sistemas).

### Key Entities

- **Chave HSM**: Par de chaves criptográficas gerado e mantido dentro do HSM. Atributos principais: rótulo, tipo/algoritmo, se é exportável, se possui certificado associado, data de criação.
- **CSR**: Solicitação de assinatura de certificado gerada a partir de uma chave do HSM. Atributos: CN, SANs, organização, país, conteúdo PEM, chave HSM de origem.
- **Certificado importado**: Certificado emitido por uma CA e associado a uma chave do HSM. Atributos: CN, emissor, validade, número de série, chave HSM associada.
- **Pacote exportado (PFX/P12)**: Arquivo contendo certificado e chave privada extraídos do HSM, protegido por senha. Atributos: formato, data de exportação, chave/certificado de origem.
- **Resultado de busca**: Item retornado por uma consulta ao inventário do HSM (chave e/ou certificado), com atributos resumidos para exibição em lista.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um administrador consegue criar uma chave no HSM e obter confirmação em até 10 segundos em condições normais de rede.
- **SC-002**: Um administrador consegue gerar uma CSR a partir de uma chave do HSM, do início ao fim, em menos de 2 minutos.
- **SC-003**: 100% dos certificados importados com chave pública incompatível são rejeitados antes da conclusão, sem deixar associação inválida no HSM ou no sistema.
- **SC-004**: Um administrador consegue exportar um PFX/P12 válido (abrível com a senha definida, contendo certificado e chave corretos) em até 1 minuto após localizar o item desejado.
- **SC-005**: Uma busca por rótulo ou CN retorna resultados relevantes em até 3 segundos para um inventário de até 10.000 objetos no HSM.
- **SC-006**: Toda operação realizada no HSM (sucesso ou falha) fica visível no histórico/auditoria do sistema em até 1 minuto após sua execução.
- **SC-007**: Em caso de indisponibilidade do HSM, 100% das tentativas de operação exibem mensagem de erro compreensível ao usuário, sem travar a interface.

## Assumptions

- A integração é feita com um único HSM/partição Dinamo por ambiente (produção, homologação etc.), configurado nas telas de administração já existentes no sistema.
- Os tipos de chave suportados inicialmente são os já usados hoje pelo sistema em software (RSA 2048 e RSA 4096); suporte a curvas elípticas pode ser avaliado posteriormente se o HSM oferecer.
- O administrador que opera as telas de HSM já possui permissão equivalente à de administrador de certificados no sistema atual — não há novo nível de permissão específico para HSM nesta fase.
- O volume de chaves/certificados no HSM é compatível com uma listagem paginada (não é necessário suporte a exportação em massa nesta fase).
- Certificados são importados em formato PEM ou DER, os formatos já manipulados pelo restante do sistema.
