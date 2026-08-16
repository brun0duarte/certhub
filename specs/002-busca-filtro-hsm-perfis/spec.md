# Feature Specification: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

**Feature Branch**: `002-busca-filtro-hsm-perfis`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "vamos implementar algumas mudanças:
1) adicionar busca ao text input que vincula uma CSR a uma demanda, com um número grande de reqs fica inviável procurar 1 a 1
2) melhorar o filtro, poder ordenar, monitor, geração e instalação
3) na aba do HSM, a UI ficou meio quebrada, o espaçamento está estranho
4) normalmente usamos 2 HSM's (PRD e NPRD) com IPs diferentes, deve ser possível salvar esses 2 para alternar mais fácil"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Buscar demanda ao vincular uma CSR (Priority: P1)

Ao gerar uma CSR, decodificar um certificado, importar um certificado no HSM ou definir a referência de credencial de um local de instalação, o usuário precisa escolher a qual demanda (REQ) aquela operação pertence. Hoje essa escolha é uma lista suspensa simples com todas as demandas — com um volume grande de REQs cadastradas, encontrar a demanda certa exige rolar a lista inteira, o que é impraticável.

**Why this priority**: Bloqueia o uso diário do sistema assim que o volume de demandas cresce — é o problema mais citado pelo usuário e afeta múltiplos fluxos (CSR, decoder, HSM, instalação).

**Independent Test**: Com uma base de centenas de demandas cadastradas, abrir qualquer tela que vincula uma operação a uma demanda, digitar parte do número da REQ ou do CN e confirmar que a lista se restringe às demandas correspondentes em tempo real, sem precisar rolar a lista completa.

**Acceptance Scenarios**:

1. **Given** existem centenas de demandas cadastradas, **When** o usuário abre o seletor de demanda em qualquer tela que vincula uma operação a uma REQ e digita parte do número da REQ, **Then** a lista exibida se restringe apenas às demandas cujo número contém o texto digitado.
2. **Given** o usuário não sabe o número exato da REQ, **When** digita parte do CN (nome do certificado) no seletor, **Then** a lista mostra as demandas correspondentes por CN.
3. **Given** o usuário encontrou a demanda desejada na lista filtrada, **When** a seleciona, **Then** a operação em andamento (CSR, decoder, importação HSM, local de instalação) fica vinculada a essa demanda exatamente como acontecia com a lista suspensa anterior.
4. **Given** o campo de busca está vazio, **When** o usuário abre o seletor, **Then** todas as demandas elegíveis continuam disponíveis (comportamento equivalente ao atual, sem busca).

---

### User Story 2 - Filtrar e ordenar demandas em Monitor, Geração e Instalação (Priority: P2)

O usuário acompanha demandas nas abas de Monitor de Vencimentos, Geração e Instalação. Hoje é possível buscar por texto, mas não é possível ordenar as listas por coluna nem aplicar os mesmos filtros de forma consistente entre as três abas, o que dificulta priorizar o que precisa de atenção (ex.: certificados vencendo primeiro, demandas mais antigas primeiro).

**Why this priority**: Trabalho diário de acompanhamento fica mais lento sem ordenação; é o segundo ponto de atrito mais citado.

**Independent Test**: Em cada uma das três abas, aplicar um filtro (ex.: ambiente, status) e alternar a ordenação por uma coluna relevante (ex.: data de vencimento, data de criação) e confirmar que a lista exibida reflete corretamente o filtro e a ordem escolhidos.

**Acceptance Scenarios**:

1. **Given** o usuário está na aba Monitor, Geração ou Instalação, **When** escolhe ordenar por uma coluna (ex.: data de vencimento, número da REQ, ambiente, status), **Then** a lista é reordenada de acordo, com opção de ordem crescente ou decrescente.
2. **Given** o usuário aplica um filtro (ambiente, status, tipo de demanda) em qualquer uma das três abas, **When** o filtro é aplicado, **Then** apenas os itens correspondentes aparecem, e o filtro pode ser combinado com busca por texto e com a ordenação escolhida.
3. **Given** o usuário está na aba Geração ou Instalação (que hoje não oferecem ordenação), **When** acessa a lista, **Then** passa a ter as mesmas opções de ordenação já disponíveis na aba Monitor.
4. **Given** o usuário limpa os filtros aplicados, **When** confirma a limpeza, **Then** a lista volta a exibir todos os itens na ordenação padrão.

---

### User Story 3 - Corrigir layout da aba HSM (Priority: P3)

A aba HSM (Dinamo) está com o espaçamento visual quebrado — elementos desalinhados ou com espaçamento inconsistente entre os cartões de ações (buscar, criar chave, importar certificado, gerar CSR, exportar).

**Why this priority**: Impacto visual e de usabilidade, mas não impede o uso funcional da aba — prioridade menor que os problemas que bloqueiam ou atrasam o trabalho.

**Independent Test**: Abrir a aba HSM em resolução de desktop padrão e comparar visualmente o espaçamento e alinhamento dos cartões/campos com o padrão usado nas demais abas do sistema (ex.: Configurações, Certificados).

**Acceptance Scenarios**:

1. **Given** o usuário abre a aba HSM, **When** visualiza os cartões de ações (buscar, criar chave, importar certificado, gerar CSR, exportar), **Then** o espaçamento entre eles e entre os campos internos é consistente com o padrão visual das demais abas do sistema.
2. **Given** o usuário redimensiona a janela para larguras comuns de desktop, **When** observa a aba HSM, **Then** os elementos não se sobrepõem nem ficam com espaçamento excessivo ou insuficiente.

---

### User Story 4 - Salvar e alternar entre perfis de HSM (PRD e NPRD) (Priority: P4)

O usuário opera normalmente com dois HSMs distintos — um de produção (PRD) e um de não produção (NPRD) — cada um com IP e credenciais próprios. Hoje só é possível salvar uma configuração de conexão por vez, então trocar de ambiente exige reescrever host, porta, usuário e senha manualmente toda vez.

**Why this priority**: Melhoria de eficiência operacional recorrente, mas o usuário já consegue operar hoje (com retrabalho manual) — menor urgência que os itens que bloqueiam ou atrasam tarefas diárias.

**Independent Test**: Cadastrar duas configurações de conexão de HSM (uma como PRD, outra como NPRD) com host/porta/usuário/senha diferentes, alternar entre elas e confirmar que as operações da aba HSM (buscar, criar chave, importar, gerar CSR, exportar) passam a usar a configuração selecionada.

**Acceptance Scenarios**:

1. **Given** o usuário está em Configurações, **When** cadastra duas conexões de HSM nomeadas (ex.: "PRD" e "NPRD") com host, porta, usuário e senha próprios, **Then** ambas ficam salvas de forma independente, sem uma sobrescrever a outra.
2. **Given** as duas conexões estão salvas, **When** o usuário alterna qual delas está ativa (a partir da aba HSM ou de Configurações), **Then** todas as operações subsequentes na aba HSM (buscar, criar chave, importar certificado, gerar CSR, exportar) passam a usar a conexão selecionada.
3. **Given** o usuário está no meio de uma sessão de trabalho, **When** troca o perfil ativo, **Then** a troca é imediata e não exige preencher novamente host/porta/usuário/senha.
4. **Given** apenas um perfil está cadastrado (situação atual migrada), **When** o usuário acessa a aba HSM, **Then** o sistema continua funcionando normalmente usando esse único perfil como ativo, sem exigir recadastro.

### Edge Cases

- Busca de demanda (US1): o que exibir quando nenhuma demanda corresponde ao texto digitado? Deve ficar claro que a busca não encontrou resultados, sem parecer que a lista está vazia por erro.
- Filtro/ordenação (US2): ao combinar filtro + busca + ordenação e nenhum item corresponder, a lista deve indicar claramente "nenhum resultado", distinto de "carregando".
- Perfis de HSM (US4): o que acontece se o usuário tentar excluir o perfil que está atualmente ativo? O sistema deve impedir a exclusão do perfil ativo, ou exigir a seleção de outro perfil como ativo antes de excluir.
- Perfis de HSM (US4): dois perfis não podem ter o mesmo nome — o sistema deve rejeitar ou avisar em caso de nome duplicado.
- Layout HSM (US3): a correção de espaçamento não deve alterar nenhum comportamento funcional dos cartões (buscar, criar chave, importar, gerar CSR, exportar).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST oferecer um campo de busca por texto em todo seletor de demanda usado para vincular uma operação a uma REQ (geração de CSR, decoder de certificado, importação de certificado no HSM, geração de CSR no HSM, referência de credencial de local de instalação), substituindo a lista suspensa simples atual.
- **FR-002**: A busca de demanda MUST filtrar a lista exibida por correspondência parcial no número da REQ e no CN, atualizando os resultados conforme o usuário digita.
- **FR-003**: A busca de demanda MUST preservar o comportamento atual de seleção (a operação continua vinculada ao mesmo `req_id` de antes) — apenas a forma de localizar a demanda muda.
- **FR-004**: As abas Geração e Instalação MUST oferecer ordenação por coluna (incluindo, no mínimo, número da REQ, ambiente, status e data), em ordem crescente ou decrescente, com paridade em relação à ordenação já existente na aba Monitor.
- **FR-005**: As abas Monitor, Geração e Instalação MUST permitir combinar busca por texto, filtros (ambiente, status, tipo de demanda conforme aplicável a cada aba) e ordenação simultaneamente.
- **FR-006**: O sistema MUST manter os filtros e a ordenação aplicados visíveis para o usuário enquanto ele navega dentro da mesma aba (ex.: após aplicar um filtro, o critério escolhido permanece indicado na tela).
- **FR-007**: O layout da aba HSM MUST usar o mesmo padrão de espaçamento entre cartões e entre campos internos adotado nas demais abas do sistema.
- **FR-008**: O sistema MUST permitir salvar múltiplas configurações de conexão de HSM nomeadas (perfis), cada uma com seu próprio host, porta, usuário e senha.
- **FR-009**: O sistema MUST permitir marcar um perfil de HSM como ativo e alternar o perfil ativo a qualquer momento.
- **FR-010**: Toda operação da aba HSM (buscar, criar chave, importar certificado, gerar CSR, exportar) MUST usar a conexão do perfil de HSM atualmente ativo.
- **FR-011**: O sistema MUST impedir o cadastro de dois perfis de HSM com o mesmo nome.
- **FR-012**: O sistema MUST impedir a exclusão do perfil de HSM atualmente ativo enquanto ele for o único perfil ativo disponível.
- **FR-013**: O sistema MUST migrar a configuração de HSM única existente para um perfil ativo por padrão, sem exigir que o usuário recadastre credenciais já salvas.

### Key Entities

- **Demanda (REQ)**: representa uma solicitação de certificado; atributos relevantes para busca incluem número da REQ, CN, ambiente e status. Já existe no sistema — não é criada por esta funcionalidade.
- **Perfil de conexão HSM**: representa uma configuração de acesso a um HSM Dinamo, identificada por um nome (ex.: "PRD", "NPRD") e contendo host, porta, usuário e senha. Um perfil por vez é o "ativo" e é usado pelas operações da aba HSM.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários localizam e selecionam a demanda correta em um seletor com centenas de itens em menos de 10 segundos, digitando parte do número da REQ ou do CN.
- **SC-002**: 100% das telas que hoje vinculam uma operação a uma demanda por lista suspensa passam a oferecer busca por texto.
- **SC-003**: Usuários conseguem ordenar e filtrar as listas de Monitor, Geração e Instalação sem sair da aba, obtendo o resultado reordenado/filtrado em menos de 2 segundos após a ação.
- **SC-004**: A aba HSM apresenta espaçamento visualmente consistente com o restante do sistema, confirmado por revisão visual comparativa (sem elementos sobrepostos ou desalinhados nas larguras de desktop testadas).
- **SC-005**: Usuários alternam entre os perfis de HSM PRD e NPRD em menos de 5 segundos, sem precisar redigitar host, porta, usuário ou senha.
- **SC-006**: Após a migração, 100% dos usuários que já tinham uma configuração de HSM salva continuam operando normalmente sem precisar recadastrar credenciais.

## Assumptions

- A lista de demandas usada nos seletores (US1) já é carregada pela tela correspondente hoje; a busca filtra esse conjunto já disponível, sem exigir uma nova origem de dados.
- "Ordenar" em Geração e Instalação (US2) significa alcançar paridade com as opções de ordenação já existentes na aba Monitor (ex.: por data, REQ, ambiente, status), não a criação de critérios de ordenação inéditos.
- A alternância de perfil de HSM (US4) é global para a aba HSM — ou seja, existe um único perfil "ativo" por vez usado por todas as operações daquela aba, não uma seleção de perfil por operação individual.
- Perfis de HSM adicionais além de PRD/NPRD (ex.: um terceiro ambiente) não são um requisito explícito, mas a solução MUST suportar mais de dois perfis salvos sem alteração estrutural, já que o cadastro é nomeado e não limitado a dois slots fixos.
- Senhas de perfis de HSM seguem o mesmo tratamento de armazenamento já usado para a configuração de HSM existente (nenhuma mudança no nível de proteção é solicitada por este pedido).
