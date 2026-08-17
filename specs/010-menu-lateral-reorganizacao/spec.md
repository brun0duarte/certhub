# Feature Specification: Reorganização do Menu Lateral

**Feature Branch**: `010-menu-lateral-reorganizacao`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Revisão de UX do menu lateral (pontos 9-16 do levantamento): agrupar os 18 itens em categorias funcionais, mover Aparência/Configurações pra um bloco fixo separado dos itens de uso diário, remover o botão de tema do rodapé (já existe em Aparência), corrigir a quebra de linha do rótulo 'Manuais & Comandos', adicionar badges de contagem em itens com pendências acionáveis (Revogação, Kanban), garantir tooltip no botão de recolher, e corrigir o contraste dos ícones/rótulos inativos no modo CAIXA."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Encontrar uma função pela categoria, não por posição decorada (Priority: P1)

Um usuário olha os 18 itens do menu lateral, hoje numa lista plana sem agrupamento, e precisa varrer item por item pra achar o que procura porque a ordem não segue nenhuma lógica visível.

**Why this priority**: É a mudança estrutural que todas as outras (footer, badges, contraste) dependem — reorganizar categorias depois de implementar badges/footer geraria retrabalho.

**Independent Test**: Abrir o menu lateral e verificar que os itens estão visualmente divididos em grupos com cabeçalho (Certificados, Ciclo de vida, Segurança, Sistema), sem precisar abrir nenhuma view.

**Acceptance Scenarios**:

1. **Given** o menu lateral aberto, **When** o usuário olha a lista de navegação, **Then** os itens aparecem divididos em grupos rotulados por função (Certificados, Ciclo de vida, Segurança, Sistema).
2. **Given** um grupo de itens, **When** o usuário olha o item Dashboard, **Then** ele aparece isolado no topo, fora de qualquer categoria (é a página inicial, não uma função de categoria).
3. **Given** os grupos definidos, **When** o usuário procura por qualquer um dos 16 itens de uso frequente, **Then** ele o encontra dentro do grupo correspondente à sua função (ex.: Revogação em "Ciclo de vida", HSM em "Segurança").

---

### User Story 2 - Não competir por atenção com itens raros (Priority: P1)

Um usuário que usa o sistema diariamente não quer que "Aparência" e "Configurações" — itens que ele abre raramente — ocupem posição misturada entre os itens que usa toda hora.

**Why this priority**: Junto com a US1, define a nova estrutura do menu — precisa estar pronta antes das mudanças menores (badges, tooltip).

**Independent Test**: Abrir o menu lateral e confirmar que Aparência e Configurações não aparecem na lista rolável principal, mas continuam acessíveis num bloco fixo separado, sempre visível.

**Acceptance Scenarios**:

1. **Given** o menu lateral, **When** o usuário olha a lista principal de navegação, **Then** Aparência e Configurações não estão nela.
2. **Given** o menu lateral, **When** o usuário olha abaixo da lista principal, **Then** encontra Aparência e Configurações num bloco fixo, visualmente separado, sempre acessível sem rolar.
3. **Given** o bloco fixo de Aparência/Configurações, **When** o usuário clica em qualquer um dos dois, **Then** navega pra view correspondente normalmente, com o mesmo destaque de item ativo que os demais itens do menu.

---

### User Story 3 - Rodapé do menu sem controle duplicado (Priority: P2)

Um usuário olha o rodapé do menu lateral (usuário logado, sair, recolher menu) e não quer ver um botão de alternar tema ali, já que esse controle completo já existe na página de Aparência.

**Why this priority**: Depende da US2 (Aparência virando bloco fixo acessível) — só faz sentido remover a duplicata depois que o caminho alternativo está visível e a um clique de distância.

**Independent Test**: Abrir o rodapé do menu e confirmar que só restam usuário/Sair e recolher menu — sem botão de tema — e que a alternância de tema continua funcionando normalmente a partir de Aparência.

**Acceptance Scenarios**:

1. **Given** o rodapé do menu lateral, **When** o usuário o observa, **Then** não há nenhum controle de alternância de tema ali.
2. **Given** a página Aparência, **When** o usuário alterna entre tema claro e escuro por lá, **Then** a mudança é aplicada e persistida normalmente, como já acontecia antes.

---

### User Story 4 - Rótulos de menu que nunca quebram linha (Priority: P1)

Um usuário vê o item "Manuais & Comandos" quebrando em duas linhas dentro do menu, o que desalinha a altura desse item em relação aos vizinhos.

**Why this priority**: É um defeito visual concreto, já reproduzido, com risco de se repetir em qualquer rótulo futuro — correção simples e de alto impacto imediato.

**Independent Test**: Olhar o item de menu de manuais/comandos em qualquer combinação de tema/layout e confirmar que o rótulo cabe numa linha só; testar também com um rótulo propositalmente longo pra confirmar que o comportamento de fallback (reticências) funciona.

**Acceptance Scenarios**:

1. **Given** qualquer tema e accent ativo, **When** o item de manuais/comandos é exibido no menu lateral, **Then** seu rótulo ocupa uma única linha.
2. **Given** um rótulo de item de menu mais longo que o espaço disponível, **When** ele é exibido, **Then** o texto é cortado com reticências em vez de quebrar para uma segunda linha.

---

### User Story 5 - Ver de relance onde há pendência (Priority: P2)

Um usuário olha o menu lateral e quer saber, sem entrar em cada view, se há revogações ou tarefas do Kanban aguardando ação.

**Why this priority**: Melhora eficiência de triagem diária, mas o usuário ainda consegue descobrir pendências entrando em cada view — não é bloqueante.

**Independent Test**: Ter pelo menos 1 demanda de revogação em aberto e 1 tarefa fora da coluna "Concluído", e verificar que os itens "Revogação" e "Kanban" no menu mostram um contador numérico. Resolver/concluir essas pendências e verificar que o contador some.

**Acceptance Scenarios**:

1. **Given** N demandas de revogação em aberto (N > 0), **When** o usuário olha o item "Revogação" no menu, **Then** vê um indicador numérico com o valor N.
2. **Given** zero pendências num item com suporte a contador, **When** o usuário olha esse item, **Then** nenhum indicador numérico aparece (menu não fica poluído com zeros).
3. **Given** um contador visível, **When** a pendência correspondente é resolvida (ex.: tarefa movida pra "Concluído"), **Then** o contador é atualizado para refletir o novo total, sem exigir recarregar a página inteira.

---

### User Story 6 - Saber o que o botão de recolher faz antes de clicar (Priority: P3)

Um usuário passa o mouse sobre o ícone de recolher/expandir o menu e quer confirmar o que ele faz antes de clicar, já que o ícone sozinho («) não é autoexplicativo.

**Why this priority**: Comportamento básico já existente no sistema — esta história documenta e confirma formalmente o requisito, com risco baixo de regressão.

**Independent Test**: Passar o mouse sobre o botão de recolher/expandir em ambos os estados (menu expandido e recolhido) e confirmar que aparece um texto explicativo apropriado a cada estado.

**Acceptance Scenarios**:

1. **Given** o menu lateral expandido, **When** o usuário passa o mouse sobre o botão de recolher, **Then** um texto indica que a ação vai recolher o menu.
2. **Given** o menu lateral recolhido (modo compacto), **When** o usuário passa o mouse sobre o mesmo botão, **Then** o texto indica que a ação vai expandir o menu.

---

### User Story 7 - Ler ícones e rótulos inativos do menu institucional sem esforço (Priority: P1)

Um usuário com o modo de marca institucional (CAIXA) ativo olha os itens não-selecionados do menu sobre o fundo azul sólido e precisa conseguir ler o rótulo/ícone sem forçar a vista.

**Why this priority**: Questão de acessibilidade (contraste) mensurável e já abaixo do mínimo recomendado — mesma prioridade de outros itens de contraste do levantamento geral.

**Independent Test**: Ativar o modo CAIXA e medir o contraste entre a cor do texto/ícone inativo do menu e o fundo azul sólido da barra lateral.

**Acceptance Scenarios**:

1. **Given** o modo de marca institucional ativo, **When** um item de menu está no estado inativo (não hover, não ativo), **Then** o contraste entre seu texto e o fundo da barra lateral atinge no mínimo 4.5:1 (WCAG AA).

### Edge Cases

- O que acontece com o agrupamento (US1) se um item pertencer conceitualmente a mais de uma categoria? Cada item tem exatamente uma categoria — a definição de pertencimento é fixa, não reavaliada por contexto de uso.
- Como o layout compacto (só ícones) exibe os cabeçalhos de grupo (US1)? Como o espaço é mínimo nesse modo, os cabeçalhos de grupo podem ficar ocultos, mantendo só um espaçamento maior entre grupos como indicação visual.
- Como o bloco fixo de Aparência/Configurações (US2) se comporta no layout horizontal (menu no topo)? Continua visível e clicável, adaptado à orientação horizontal, sem se misturar com a lista de itens frequentes.
- O que acontece com o contador de pendências (US5) se a chamada de contagem falhar (ex. API indisponível)? O item de menu não mostra contador (falha silenciosa), sem quebrar a navegação.
- Como o corte de rótulo com reticências (US4) interage com o layout compacto (só ícones)? Nesse modo o rótulo já fica oculto por completo — a regra de reticências só é relevante nos layouts lateral e horizontal.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O menu lateral DEVE agrupar os itens de navegação de uso frequente em categorias funcionais rotuladas (Certificados, Ciclo de vida, Segurança, Sistema).
- **FR-002**: O item Dashboard DEVE permanecer fora de qualquer categoria, no topo da navegação.
- **FR-003**: Aparência e Configurações NÃO DEVEM aparecer na lista rolável principal de navegação.
- **FR-004**: Aparência e Configurações DEVEM ficar acessíveis num bloco fixo, sempre visível, separado da lista principal e do rodapé de usuário/sair/recolher.
- **FR-005**: O bloco fixo de Aparência/Configurações DEVE aplicar o mesmo destaque visual de item ativo usado na lista principal.
- **FR-006**: O rodapé do menu lateral NÃO DEVE conter nenhum controle de alternância de tema.
- **FR-007**: A alternância de tema DEVE continuar funcional e persistente a partir da página Aparência.
- **FR-008**: Todo rótulo de item de menu DEVE permanecer numa única linha em qualquer combinação de tema/accent/layout suportado.
- **FR-009**: Um rótulo de menu mais longo que o espaço disponível DEVE ser cortado com reticências, nunca quebrado em múltiplas linhas.
- **FR-010**: Os itens "Revogação" e "Kanban" DEVEM exibir um indicador numérico de pendências acionáveis quando esse número for maior que zero.
- **FR-011**: Um item com indicador de pendências DEVE ocultar o indicador quando o número de pendências for zero.
- **FR-012**: O indicador de pendências DEVE se atualizar depois que uma ação relevante muda a contagem (ex. mover tarefa do Kanban, concluir uma revogação), sem exigir recarregar a página inteira.
- **FR-013**: O botão de recolher/expandir o menu DEVE expor, via tooltip, uma descrição textual da ação, diferente conforme o estado atual (recolher vs. expandir).
- **FR-014**: No modo de marca institucional (CAIXA), o contraste entre o texto/ícone de um item de menu inativo e o fundo da barra lateral DEVE atingir no mínimo 4.5:1 (WCAG AA).

### Key Entities

- **Item de menu**: rótulo, ícone, destino de navegação, categoria funcional (ou nenhuma, se for Dashboard), estado (ativo/inativo/hover), indicador de pendência opcional.
- **Categoria funcional**: rótulo do grupo (Certificados, Ciclo de vida, Segurança, Sistema), lista ordenada de itens de menu pertencentes a ela.
- **Indicador de pendência**: contagem numérica associada a um item de menu, calculada a partir de dados do sistema (demandas de revogação em aberto, tarefas de Kanban não concluídas).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos 16 itens de uso frequente aparecem dentro de uma das 4 categorias funcionais definidas; nenhum item fica órfão ou duplicado entre categorias.
- **SC-002**: Aparência e Configurações ficam acessíveis em no máximo 1 clique a partir de qualquer view, sem exigir rolagem da lista principal de navegação.
- **SC-003**: 0% dos rótulos de itens de menu quebram em múltiplas linhas em qualquer combinação suportada de tema × accent × layout.
- **SC-004**: 100% dos pares de cor texto/fundo de itens de menu inativos no modo institucional atingem contraste mínimo 4.5:1.
- **SC-005**: O indicador de pendências reflete a contagem real do sistema em até 1 ação do usuário (a próxima navegação ou atualização relevante) após a mudança de estado.

## Assumptions

- Breadcrumb no topo do conteúdo principal foi avaliado e descartado nesta rodada — o título de cada view somado ao menu agrupado (US1) já fornece contexto de localização suficiente; pode ser reconsiderado no futuro se usuários relatarem confusão mesmo com o agrupamento em produção.
- O tooltip nativo do navegador (atributo de título) é suficiente para atender FR-013 — não é necessário um componente de tooltip customizado.
- As categorias funcionais e o mapeamento de cada um dos 16 itens já foram definidos no planejamento prévio desta feature e não são reabertos como decisão de design nesta especificação.
- O cálculo de pendências (Revogação, Kanban) reaproveita os mesmos critérios de status/coluna já usados nas respectivas views — não introduz uma nova definição de "pendente".
- A atualização do indicador de pendências (FR-012) não precisa ser em tempo real entre usuários simultâneos — reflete o estado no momento da navegação/ação do próprio usuário.
