# Feature Specification: Demandas de Revogação de Certificados

**Feature Branch**: `004-revogacao-certificados`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "muito bem, alguns certificado são emitidos por uma ac interna, temos uma para produção e uma para não produção, atualmente, para emitir um certificado via ac interna, nos precisamos acessar remotamente a maquina e rodar um script, outra coisa, os certificados podem também ser revogados, até então, nos ignoramos essa possibilidade, ou seja, além da demanda de geração e instalação, nós também podemos ter uma de revogação, vamos criar uma aba dessa também, dependendo de onde ele foi emitido, vai depender de onde nos precisamos revogar (internacional, serpro, ac interna nprd e prd, outros), podemos abrir uma demanda de revogação a partir do nosso inventário, além do mais, vamos implementar os providers, não vamos conectar de fato ainda, mas todos as funções devem ser implementadas"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir demanda de revogação a partir do inventário (Priority: P1)

Hoje, quando um certificado do inventário precisa ser revogado, isso acontece de forma manual e sem registro no sistema — a demanda de revogação é ignorada, mesmo já existindo um passo a passo documentado (identificar serial/thumbprint, solicitar revogação à CA correta, confirmar CRL/OCSP, remover dos sistemas, documentar) que hoje só existe como texto de referência, sem nenhuma demanda rastreável por trás. O usuário precisa conseguir, a partir de um certificado já cadastrado, abrir uma demanda de revogação formal, com os dados do certificado (CN, serial, thumbprint, emissor) já preenchidos.

**Why this priority**: É o ponto de entrada mais citado pelo usuário e resolve a lacuna mais concreta hoje — revogação sendo ignorada por falta de rastreamento. Sem isso, a aba de revogação (User Story 2) não teria como ser alimentada de forma prática.

**Independent Test**: Na aba Certificados, abrir o detalhe de um certificado já importado, acionar "Revogar", confirmar que uma nova demanda de revogação é criada com CN, serial, thumbprint e emissor do certificado já preenchidos, e que ela aparece na aba de Revogação.

**Acceptance Scenarios**:

1. **Given** um certificado está cadastrado no inventário, **When** o usuário aciona a opção de revogar esse certificado, **Then** uma nova demanda de revogação é criada, vinculada a esse certificado, com CN, serial, thumbprint e emissor pré-preenchidos a partir dos dados já cadastrados.
2. **Given** o usuário está abrindo uma demanda de revogação a partir de um certificado, **When** a tela de criação é exibida, **Then** o usuário escolhe o destino/canal de revogação (Internacional, Serpro, AC Interna NPRD, AC Interna PRD, Outros) e pode informar um motivo antes de confirmar.
3. **Given** um certificado já tem uma demanda de revogação em andamento (não concluída), **When** o usuário tenta abrir uma segunda demanda de revogação para o mesmo certificado, **Then** o sistema avisa que já existe uma demanda de revogação em andamento para aquele certificado, em vez de criar uma duplicata silenciosa.

---

### User Story 2 - Acompanhar demandas de revogação numa aba própria (Priority: P2)

Hoje não existe nenhum lugar dedicado para ver quais certificados estão em processo de revogação, em qual destino/canal, e em que etapa cada um está — demandas de revogação, se existissem, ficariam misturadas com as de geração. O usuário precisa de uma aba própria, no mesmo padrão das abas de Geração e Instalação já existentes (busca, filtro, ordenação, abrir detalhe), dedicada só a demandas de revogação.

**Why this priority**: Sem uma aba dedicada, a informação criada pela User Story 1 fica sem lugar de acompanhamento — mas a criação da demanda (US1) já entrega valor mínimo sozinha (fica registrada, mesmo que vista hoje via Histórico); por isso essa aba vem em segundo lugar.

**Independent Test**: Acessar a nova aba "Revogação", confirmar que só demandas do tipo revogação aparecem ali, com busca/filtro/ordenação funcionando, e que é possível abrir uma demanda de revogação nova diretamente dali (sem precisar partir de um certificado do inventário).

**Acceptance Scenarios**:

1. **Given** existem demandas de revogação em diferentes estágios, **When** o usuário acessa a aba "Revogação", **Then** vê uma lista só com essas demandas, mostrando CN, destino/canal de revogação, status e data.
2. **Given** o usuário está na aba Revogação, **When** aplica busca por texto, filtro (ambiente, status, destino) ou ordena por coluna, **Then** a lista reflete corretamente o filtro/ordenação aplicados — mesmo comportamento já disponível em Geração e Instalação.
3. **Given** o usuário está na aba Revogação, **When** aciona "Nova demanda", **Then** consegue abrir uma demanda de revogação informando os dados do certificado manualmente (sem precisar ter vindo do inventário).
4. **Given** o usuário abre o detalhe de uma demanda de revogação, **When** visualiza a tela, **Then** consegue avançar o status da demanda (ex.: solicitada → confirmada → concluída) e registrar quando a revogação foi efetivamente confirmada (CRL/OCSP), mesmo sem conexão automática com o destino.

---

### User Story 3 - Registrar o destino/canal de revogação por demanda, pronto para automação futura (Priority: P3)

O destino de onde revogar um certificado depende de onde ele foi emitido: Internacional, Serpro, AC Interna (que tem uma instância de produção e outra de não produção, hoje operadas manualmente via acesso remoto e execução de script), ou Outros. Hoje nenhum desses destinos tem qualquer forma de execução automatizada — tudo é feito manualmente fora do sistema. O usuário quer que o sistema já modele esses destinos e registre qual foi usado em cada demanda, preparando o terreno para que cada destino ganhe, no futuro, uma execução automatizada própria — sem exigir uma conexão real com nenhum desses destinos agora.

**Why this priority**: É a base estrutural que dá suporte às outras duas stories (o campo de destino é usado tanto ao abrir a demanda quanto ao listar/filtrar na aba), mas sozinha não entrega uma tela nova — por isso vem por último em prioridade de entrega, mesmo sendo tocada pelas outras duas.

**Independent Test**: Abrir demandas de revogação com destinos diferentes (ex.: uma para "Serpro", outra para "AC Interna PRD") e confirmar que cada uma guarda e exibe corretamente o destino escolhido, mesmo sem nenhuma automação real rodando por trás.

**Acceptance Scenarios**:

1. **Given** o usuário está criando uma demanda de revogação, **When** escolhe o destino "AC Interna PRD" (ou qualquer um dos 5 destinos), **Then** esse destino fica registrado na demanda e é exibido em qualquer tela que mostre a demanda depois.
2. **Given** um destino de revogação ainda não tem execução automatizada real, **When** o usuário avança essa demanda até a conclusão, **Then** o sistema permite registrar a conclusão manualmente (o usuário confirma que revogou por fora do sistema), sem exigir nem tentar nenhuma conexão de rede com o destino.
3. **Given** o destino escolhido é "Outros", **When** o usuário registra a demanda, **Then** consegue descrever em texto livre qual é esse destino, já que não é um dos 4 destinos nomeados.

### Edge Cases

- Certificado sem emissor identificado no inventário: o sistema não consegue sugerir automaticamente um destino de revogação — o usuário escolhe manualmente entre os 5 destinos, sem bloquear a abertura da demanda.
- Certificado que nunca foi instalado em lugar nenhum (ex.: gerado e nunca usado): ainda deve ser possível abrir uma demanda de revogação pra ele — revogar não depende de o certificado estar instalado.
- Usuário tenta abrir uma demanda de revogação sem escolher nenhum destino: o sistema exige a escolha de um destino (um dos 5) antes de permitir salvar a demanda.
- Certificado já marcado como revogado (demanda de revogação anterior concluída): abrir uma nova demanda de revogação para o mesmo certificado é permitido mas com aviso, já que pode ser um caso legítimo raro (ex.: erro no processo anterior).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer uma nova aba dedicada a demandas de revogação, separada das abas de Geração e Instalação já existentes, seguindo o mesmo padrão de busca, filtro e ordenação já disponível nelas.
- **FR-002**: O sistema MUST permitir abrir uma demanda de revogação a partir de um certificado já cadastrado no inventário, pré-preenchendo CN, serial, thumbprint e emissor a partir dos dados desse certificado.
- **FR-003**: O sistema MUST também permitir abrir uma demanda de revogação diretamente pela aba de Revogação, sem exigir que o usuário parta de um certificado do inventário.
- **FR-004**: Ao abrir uma demanda de revogação, o sistema MUST exigir a escolha de um destino/canal de revogação entre: Internacional, Serpro, AC Interna NPRD, AC Interna PRD, e Outros.
- **FR-005**: Quando o destino escolhido for "Outros", o sistema MUST permitir descrever em texto livre qual é o destino real.
- **FR-006**: O sistema MUST permitir registrar um motivo (texto livre, opcional) para a revogação ao abrir a demanda.
- **FR-007**: O sistema MUST permitir acompanhar e avançar o status de uma demanda de revogação (da abertura até a conclusão), inclusive registrar manualmente que a revogação foi confirmada, já que nenhum destino tem execução automatizada real nesta fase.
- **FR-008**: O sistema MUST NOT tentar nenhuma conexão de rede real com os destinos de revogação nesta fase — toda confirmação de conclusão é feita manualmente pelo usuário.
- **FR-009**: O sistema MUST estruturar o tratamento de cada destino de revogação (Internacional, Serpro, AC Interna NPRD, AC Interna PRD, Outros) de forma que uma execução automatizada possa ser adicionada por destino no futuro, sem exigir uma reformulação do fluxo de demanda de revogação já em uso.
- **FR-010**: O sistema MUST avisar o usuário ao tentar abrir uma nova demanda de revogação para um certificado que já tem uma demanda de revogação em andamento (não concluída), sem bloquear a criação caso o usuário confirme mesmo assim.
- **FR-011**: O sistema MUST exibir, na aba de Revogação e no detalhe da demanda, qual destino/canal foi escolhido para cada demanda de revogação.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir de um certificado do inventário, o usuário consegue abrir uma demanda de revogação com os dados do certificado já preenchidos em menos de 30 segundos.
- **SC-002**: 100% das demandas de revogação abertas registram um destino/canal válido — nenhuma demanda de revogação fica sem destino definido.
- **SC-003**: Usuários conseguem encontrar, na aba de Revogação, qualquer demanda de revogação em andamento sem precisar procurar em outras abas (Geração, Histórico) — validado por não haver mais demandas de revogação implicitamente escondidas fora de uma aba dedicada.
- **SC-004**: Adicionar execução automatizada real para um destino de revogação no futuro não exige mudar como o usuário abre, acompanha ou conclui uma demanda de revogação hoje — validado revisando que a estrutura de destino já existe e é só a execução por trás que muda.

## Assumptions

- "AC Interna" tem duas instâncias operacionais distintas (produção e não produção), tratadas como dois destinos de revogação separados ("AC Interna NPRD" e "AC Interna PRD"), consistente com o que já existe hoje pra outras integrações internas do sistema (ex.: perfis de HSM separados por ambiente).
- O processo de revogação (identificar serial/thumbprint, solicitar à CA, confirmar CRL/OCSP, remover dos sistemas, documentar) já documentado informalmente no sistema como guia de referência é a base do fluxo de demanda modelado aqui — a demanda de revogação formaliza esse processo já conhecido, não inventa um novo.
- Sem conexão real com nenhum destino nesta fase, a confirmação de que a revogação foi mesmo efetivada (CRL/OCSP) é uma etapa manual registrada pelo usuário, não uma verificação automática do sistema.
- Nenhum SLA/prazo específico de revogação foi informado — segue o mesmo tratamento de prazos já usado pelas demais demandas do sistema (sem alerta de vencimento dedicado nesta fase).
- Certificados podem ser revogados independente de estarem instalados ou não, e independente de já terem sido usados numa demanda de geração no sistema (ex.: um certificado importado manualmente também pode ser alvo de revogação).
