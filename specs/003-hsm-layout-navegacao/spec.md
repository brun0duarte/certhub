# Feature Specification: Ajustes de Layout do HSM e Preservação de Estado entre Abas

**Feature Branch**: `003-hsm-layout-navegacao`

**Created**: 2026-08-15

**Status**: Draft

**Input**: User description: "Corrigir 3 problemas na aba HSM e navegação do CertHub:
1) O painel \"Criar chave\" na aba HSM está maior que o painel vizinho \"Importar certificado emitido\" (lado a lado em grid 2 colunas), causando sobreposição visual — corrigir pra ficarem consistentes.
2) No topo da aba HSM, exibir de forma visível qual perfil de HSM está em uso no momento — nome do perfil, host e usuário (ex: \"PRD · 10.0.0.1 · master\") — sem exibir a senha.
3) Ao trocar de aba dentro do sistema (navegação SPA, sem recarregar a página) e depois voltar a uma aba visitada anteriormente, preservar o que o usuário tinha preenchido/aplicado nela: campos de formulário ainda não salvos, filtros/busca aplicados, e a página atual de paginação. Isso vale só dentro da mesma sessão (não precisa sobreviver a F5/reload da página). Não é necessário adicionar nenhum botão de \"voltar\" — fora de escopo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Corrigir sobreposição do painel "Criar chave" no HSM (Priority: P1)

Na aba HSM, os painéis "Criar chave" e "Importar certificado emitido" ficam lado a lado (duas colunas). O painel "Criar chave" está mais alto que o vizinho, fazendo com que ele se sobreponha a elementos abaixo, atrapalhando a leitura e o clique nos controles seguintes.

**Why this priority**: É um defeito visual ativo que pode impedir o uso correto de controles da aba HSM agora — maior urgência que os itens informativos/de conveniência.

**Independent Test**: Abrir a aba HSM em uma largura de desktop padrão e verificar que o painel "Criar chave" não se sobrepõe a nenhum outro elemento da tela, com altura consistente em relação ao painel vizinho.

**Acceptance Scenarios**:

1. **Given** o usuário abre a aba HSM, **When** observa os painéis "Criar chave" e "Importar certificado emitido" lado a lado, **Then** nenhum dos dois se sobrepõe a outro elemento da página, independente de qual tenha mais conteúdo.
2. **Given** o usuário redimensiona a janela para larguras comuns de desktop, **When** observa a aba HSM, **Then** o alinhamento entre os dois painéis permanece consistente, sem sobreposição.

---

### User Story 2 - Exibir o perfil de HSM em uso no topo da aba (Priority: P2)

Hoje, ao entrar na aba HSM, não fica visível qual HSM (perfil, host, usuário) está sendo usado nas operações daquela aba — é preciso ir em Configurações pra conferir. Isso é arriscado quando existem múltiplos perfis (ex.: PRD e NPRD): o usuário pode operar no ambiente errado sem perceber.

**Why this priority**: Reduz risco de operação no ambiente HSM errado, mas não bloqueia o uso — o perfil ativo já pode ser conferido em Configurações hoje.

**Independent Test**: Com dois ou mais perfis de HSM cadastrados, abrir a aba HSM e confirmar visualmente, sem sair da aba, qual perfil está ativo (nome, host e usuário); trocar o perfil ativo e confirmar que a informação exibida atualiza imediatamente.

**Acceptance Scenarios**:

1. **Given** existe um perfil de HSM ativo, **When** o usuário abre a aba HSM, **Then** o nome do perfil, o host e o usuário de conexão aparecem visíveis no topo da aba, sem precisar de nenhuma ação adicional.
2. **Given** a informação do perfil ativo está visível, **When** o usuário observa essa informação, **Then** a senha do perfil não é exibida em nenhum momento.
3. **Given** o usuário troca o perfil ativo (seletor de troca rápida já existente na aba HSM), **When** a troca é concluída, **Then** a informação exibida no topo (nome, host, usuário) atualiza para refletir o novo perfil ativo.
4. **Given** nenhum perfil de HSM está configurado, **When** o usuário abre a aba HSM, **Then** o aviso já existente de "nenhum perfil configurado" continua sendo exibido no lugar da informação de perfil.

---

### User Story 3 - Preservar dados ao trocar de aba (Priority: P3)

O usuário pode estar preenchendo um formulário (ex.: campos da aba HSM, Gerar CSR) ou com filtros/busca/página aplicados numa lista (ex.: Geração, Instalação, Monitor) e precisar consultar outra aba do sistema rapidamente. Hoje, ao voltar pra aba anterior, tudo que não foi salvo se perde e a tela volta ao estado inicial.

**Why this priority**: Melhora a experiência e evita retrabalho, mas não impede a operação — o usuário só precisa preencher de novo. Menor urgência que os itens que envolvem defeito visual ativo ou risco de erro operacional.

**Independent Test**: Preencher parcialmente um formulário (ou aplicar um filtro/busca/página) em uma aba, navegar para outra aba do sistema sem salvar, voltar à aba original e confirmar que os valores preenchidos, filtros aplicados e página atual continuam exatamente como estavam.

**Acceptance Scenarios**:

1. **Given** o usuário preencheu parcialmente um formulário em uma aba (sem salvar/enviar), **When** navega para outra aba e depois volta pra aba original, **Then** os valores preenchidos nos campos continuam lá.
2. **Given** o usuário aplicou um filtro, uma busca por texto e/ou navegou pra uma página específica de uma lista paginada, **When** troca de aba e volta, **Then** o filtro, a busca e a página atual continuam aplicados exatamente como estavam.
3. **Given** o usuário recarrega a página inteira do navegador (F5) a qualquer momento, **When** a página recarrega, **Then** o estado preenchido/aplicado NÃO precisa ser restaurado — esse cenário está fora do escopo desta funcionalidade.
4. **Given** os dados de uma lista mudaram no servidor enquanto o usuário estava em outra aba (ex.: uma demanda foi concluída por outra pessoa), **When** o usuário volta pra aba com filtro/página preservados, **Then** a lista é buscada novamente do servidor com o filtro/página preservados aplicados sobre os dados atuais — não exibe dados desatualizados.

### Edge Cases

- Se a página preservada não existir mais após os dados mudarem (ex.: usuário estava na página 5, mas agora só há 2 páginas de resultado), o sistema deve ajustar para a última página válida em vez de mostrar uma lista vazia.
- Campos sensíveis (ex.: senha de perfil de HSM em Configurações) preenchidos e não salvos: o valor preservado ao trocar de aba não pode ser gravado em nenhum armazenamento persistente do navegador — só mantido em memória da sessão ativa da página.
- Modais (ex.: detalhe de uma demanda) não são consideradas "abas" para efeito de preservação — fechar um modal e reabri-lo não precisa restaurar o que estava preenchido nele.
- Resultados de ações já concluídas (ex.: CSR gerada exibida como resultado, resultado de uma busca no HSM) não precisam ser preservados ao trocar de aba — só os campos de entrada ainda não enviados, filtros, busca e paginação.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Na aba HSM, o painel "Criar chave" MUST ter altura e alinhamento consistentes com o painel vizinho "Importar certificado emitido", sem sobrepor nenhum elemento da tela, em larguras de desktop padrão.
- **FR-002**: A aba HSM MUST exibir, de forma visível no topo (sem exigir nenhuma ação do usuário), o nome, o host e o usuário do perfil de HSM atualmente ativo.
- **FR-003**: A informação do perfil ativo exibida no topo da aba HSM MUST NUNCA incluir a senha do perfil.
- **FR-004**: Quando o usuário trocar o perfil de HSM ativo pelo seletor já existente na aba, a informação exibida no topo MUST atualizar imediatamente para refletir o novo perfil ativo.
- **FR-005**: Quando nenhum perfil de HSM estiver configurado, a aba HSM MUST continuar exibindo o aviso já existente de ausência de perfil, no lugar da informação de perfil ativo.
- **FR-006**: O sistema MUST preservar, ao trocar de aba via navegação interna (sem recarregar a página) e retornar a uma aba visitada anteriormente na mesma sessão: valores de campos de formulário ainda não salvos, filtros e busca por texto aplicados, e a página atual de listas paginadas.
- **FR-007**: A preservação de estado descrita em FR-006 MUST ser mantida apenas em memória, durante a sessão ativa da página no navegador — MUST NOT ser gravada em armazenamento persistente do navegador (ex.: localStorage, sessionStorage, cookies) nem sobreviver a um recarregamento completo da página (F5).
- **FR-008**: Ao restaurar uma lista com filtro/busca/página preservados, o sistema MUST buscar os dados atualizados do servidor e aplicar o filtro/busca/página preservados sobre esses dados atuais, nunca exibir dados desatualizados em cache.
- **FR-009**: Se a página preservada não existir mais no conjunto de dados atualizado (ex.: total de páginas diminuiu), o sistema MUST ajustar automaticamente para a última página válida em vez de exibir uma lista vazia.
- **FR-010**: Modais (ex.: detalhe de demanda) MUST NOT ter seu conteúdo preservado por esta funcionalidade — fechar e reabrir um modal reinicia seu estado normalmente.
- **FR-011**: Resultados de ações já concluídas exibidos em tela (ex.: CSR gerada, resultado de busca no HSM) MUST NOT precisar ser preservados ao trocar de aba — o escopo é limitado a entradas ainda não enviadas (campos de formulário, filtros, busca, paginação).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O painel "Criar chave" da aba HSM não apresenta sobreposição visual com nenhum outro elemento em nenhuma largura de desktop padrão testada.
- **SC-002**: Usuários identificam qual HSM (perfil, host, usuário) está em uso em até 2 segundos ao abrir a aba HSM, sem precisar sair dela.
- **SC-003**: 100% dos campos de formulário não salvos, filtros/busca aplicados e página de paginação são restaurados exatamente como estavam ao voltar pra uma aba visitada antes, dentro da mesma sessão.
- **SC-004**: Nenhum dado de formulário preenchido (incluindo senhas) fica persistido em armazenamento do navegador como parte dessa funcionalidade — confirmável inspecionando o que é salvo no navegador após o uso normal do sistema.

## Assumptions

- "Aba" corresponde às seções de navegação principais do sistema (ex.: Dashboard, Kanban, Monitor, Geração, Instalação, Histórico, Auditoria, Gerar CSR, Decoder, Certificados, HSM, Senhas, Docs, Configurações, Validar cadeia, Usuários, Aparência) — não inclui modais abertos dentro de uma aba.
- A preservação de estado (US3) se aplica de forma geral a qualquer aba com campos de formulário, filtro, busca ou paginação — não só às abas citadas como exemplo pelo usuário — já que a mesma expectativa de "não perder o que eu digitei ao trocar de aba" se aplica ao sistema como um todo.
- "Perfil de HSM ativo" e o seletor de troca rápida já existem na aba HSM (funcionalidade anterior) — esta funcionalidade só adiciona a exibição do nome/host/usuário no topo, reaproveitando o perfil já resolvido pelo backend.
- Não há necessidade de suportar múltiplas abas do navegador abertas simultaneamente compartilhando o mesmo estado preservado — cada aba do navegador (cada carregamento de página) tem seu próprio estado independente.
