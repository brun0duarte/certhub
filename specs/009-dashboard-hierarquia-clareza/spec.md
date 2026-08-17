# Feature Specification: Hierarquia e Clareza do Dashboard

**Feature Branch**: `009-dashboard-hierarquia-clareza`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Revisão de UX do Dashboard (8 pontos): hierarquia de cor dos cards de KPI com rótulo de cumulativo, agrupamento da tabela 'Próximos vencimentos' por data, legenda dos badges de ambiente (HMP/TQS/PRD/DES), compressão e agrupamento da 'Atividade Recente', contraste WCAG AA dos badges de status e renomeação de 'Excluir', linha de média/destaque do mês atual no gráfico de demandas por mês, correção do grid com espaço vazio na 3ª linha de painéis, e ação rápida de renovação por linha na tabela de vencimentos."

## Clarifications

### Session 2026-08-17

- Q: Quando o Dashboard tiver mais de 2 janelas de alerta configuradas, a cor de severidade de cada card deve vir de faixas fixas em dias ou ser relativa às janelas configuradas? → A: Faixas fixas em dias (ex. ≤30 vermelho, ≤60 âmbar, >60 verde), independente de quantas/quais janelas o admin configurou.
- Q: A partir de quantos certificados com a mesma data de vencimento a linha vira um grupo-resumo recolhido? → A: A partir de 3 certificados na mesma data (2 continuam soltos, lado a lado).
- Q: No feed "Atividade Recente", a partir de quantos eventos idênticos seguidos eles viram uma entrada agrupada com contador "×N"? → A: A partir de 3 eventos idênticos consecutivos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconhecer severidade dos KPIs sem calcular (Priority: P1)

Um usuário abre o Dashboard e precisa saber, num relance, quais números exigem ação imediata (certificados já vencidos) versus quais são só informativos (total de certificados, REQs em aberto), e se os totais de "vencem em ≤30/60/90 dias" se somam ou se sobrepõem.

**Why this priority**: É a primeira coisa que qualquer usuário vê ao entrar no sistema — se a hierarquia de cor não bate com a severidade real, decisões erradas de priorização acontecem antes de qualquer outra interação.

**Independent Test**: Abrir o Dashboard com um conjunto de dados que tenha mais de 3 janelas de alerta configuradas (ex.: 15/30/60/90 dias) e confirmar visualmente que a cor de cada card corresponde à urgência do valor do threshold (não à posição na lista), e que os cards cujo valor é cumulativo mostram um aviso textual disso.

**Acceptance Scenarios**:

1. **Given** o Dashboard com "Vencidos" > 0, **When** a página carrega, **Then** o card "Vencidos" usa a cor de maior severidade e se distingue visualmente dos cards "vencem em ≤N dias".
2. **Given** mais de 3 janelas de alerta configuradas em Configurações, **When** o Dashboard renderiza os cards de alerta, **Then** a cor de cada card é determinada pelo valor do threshold (não pela posição no array), e nenhuma janela extra herda incorretamente a cor "ok".
3. **Given** um card de threshold maior que o primeiro (ex. "≤60 dias"), **When** o usuário o lê, **Then** um texto auxiliar indica que o número inclui os certificados já contados nos thresholds menores.

---

### User Story 2 - Ler badges de status com contraste adequado e sem confundir com ação (Priority: P1)

Um usuário no tema claro olha o widget "Certificados por Lifecycle" e o card de status de qualquer certificado, e precisa distinguir as cores dos badges e entender que "Excluir" é um status do certificado (baixado do inventário), não um botão de exclusão clicável.

**Why this priority**: Badge ilegível ou rótulo ambíguo gera erro de leitura ou clique acidental — risco de correção maior do que qualquer melhoria cosmética.

**Independent Test**: Alternar pro tema claro, abrir o Dashboard e a tela de detalhe de um certificado com status "reservado"/"instalado"/"em_inventario", e verificar que o texto de cada badge é legível sobre o fundo, e que nenhum rótulo de status usa um verbo de ação isolado.

**Acceptance Scenarios**:

1. **Given** o tema claro ativo, **When** o widget "Certificados por Lifecycle" renderiza qualquer um dos 6 status, **Then** o contraste entre texto e fundo do badge atende WCAG AA (4.5:1).
2. **Given** um certificado com `lifecycle_status = "excluir"`, **When** seu badge é exibido em qualquer tela, **Then** o rótulo mostrado não é mais o verbo isolado "Excluir".

---

### User Story 3 - Ver os 3 gráficos de análise sem espaço vazio (Priority: P1)

Um usuário com dados suficientes pra popular os 3 painéis de análise (demandas por mês, tipos de chave, saúde dos certificados) vê os 3 lado a lado, sem um buraco vazio no lugar de um 4º painel inexistente.

**Why this priority**: É um defeito visual concreto e de baixo esforço de correção — deixa o dashboard com aparência quebrada/incompleta.

**Independent Test**: Popular o banco com dados que gerem os 3 conjuntos (`reqs_by_month`, `key_types`, `cert_health`) e conferir que os 3 painéis ocupam uma grade de 3 colunas sem coluna vazia.

**Acceptance Scenarios**:

1. **Given** os 3 conjuntos de dados de análise disponíveis, **When** o Dashboard renderiza a linha de painéis de análise, **Then** os 3 painéis se distribuem numa grade de 3 colunas sem espaço vazio à direita do último.
2. **Given** apenas 1 ou 2 dos 3 conjuntos disponíveis, **When** o Dashboard renderiza essa linha, **Then** os painéis presentes ocupam o espaço de forma equilibrada (sem quebra de layout).

---

### User Story 4 - Entender os códigos de ambiente sem perguntar (Priority: P2)

Um usuário novo vê badges "PRD", "TQS", "HMP", "DES" espalhados pelo sistema e não sabe o que cada sigla significa nem por que têm cores diferentes.

**Why this priority**: Afeta compreensão, mas o usuário consegue inferir pelo contexto/nome do ambiente com mais esforço — não bloqueia o uso.

**Independent Test**: Passar o mouse sobre um badge de ambiente e ver a expansão da sigla; abrir o Dashboard e localizar a legenda fixa com as 4 siglas e suas cores.

**Acceptance Scenarios**:

1. **Given** qualquer badge de ambiente na interface, **When** o usuário passa o mouse sobre ele, **Then** um tooltip mostra o nome completo do ambiente (Produção/Homologação/Teste de Qualidade/Desenvolvimento).
2. **Given** o Dashboard, **When** o usuário olha o bloco "Demandas por ambiente e status", **Then** uma legenda visível explica as 4 siglas e indica que a cor reflete a criticidade do ambiente.

---

### User Story 5 - Escanear vencimentos agrupados por data (Priority: P2)

Um usuário com muitos certificados vencendo na mesma data vê uma lista repetitiva linha-a-linha em vez de um resumo por data.

**Why this priority**: Melhora escaneabilidade em bases grandes, mas a tabela atual continua funcional (só verbosa) enquanto não corrigida.

**Independent Test**: Ter 5+ certificados com a mesma data de vencimento no conjunto `next_expiring` e verificar que a tabela mostra uma linha-resumo com contagem, expansível pra ver os certificados individuais.

**Acceptance Scenarios**:

1. **Given** múltiplos certificados vencendo na mesma data, **When** a tabela "Próximos vencimentos" renderiza, **Then** essas linhas aparecem agrupadas numa única linha-resumo com contador.
2. **Given** uma linha-resumo agrupada, **When** o usuário clica nela, **Then** as linhas individuais daquela data ficam visíveis.

---

### User Story 6 - Iniciar renovação direto da tabela do Dashboard (Priority: P2)

Um usuário vendo um certificado prestes a vencer no Dashboard quer iniciar a renovação sem navegar até o Monitor de Vencimentos.

**Why this priority**: Atalho de produtividade — o caminho alternativo (via Monitor) já existe e funciona, então isso é conveniência, não bloqueio.

**Independent Test**: No Dashboard, clicar no ícone de ação de um certificado sem demanda ativa e confirmar que o formulário de nova demanda de renovação abre pré-preenchido.

**Acceptance Scenarios**:

1. **Given** um certificado na tabela "Próximos vencimentos" sem demanda ativa, **When** o usuário clica no ícone de ação da linha, **Then** o formulário de nova demanda de renovação abre pré-preenchido com os dados do certificado.
2. **Given** um certificado que já tem demanda ativa, **When** o usuário olha a linha correspondente, **Then** nenhuma ação de renovação é oferecida (evita duplicar demanda).

---

### User Story 7 - Ler a Atividade Recente sem ruído repetido (Priority: P2)

Um usuário olha o feed de atividade recente e, quando várias ações idênticas seguidas acontecem (ex. 5 status alterados em sequência na mesma REQ), quer ver isso condensado, não 5 linhas iguais.

**Why this priority**: Reduz ruído visual, mas a informação completa continua acessível mesmo sem essa melhoria.

**Independent Test**: Gerar 3+ eventos consecutivos idênticos (mesma ação, mesma REQ) e verificar que o feed os mostra como uma entrada agrupada com contador.

**Acceptance Scenarios**:

1. **Given** um evento de atividade, **When** exibido no feed, **Then** ocupa no máximo 2 linhas (era 3).
2. **Given** 3 ou mais eventos consecutivos com mesma ação e mesma REQ, **When** o feed renderiza, **Then** aparecem como uma única entrada com indicador de repetição (ex. "×3").

---

### User Story 8 - Ver tendência e o mês atual no gráfico de demandas (Priority: P3)

Um usuário olhando "Demandas criadas por mês" quer saber se o mês atual está acima ou abaixo da média histórica, sem contar manualmente.

**Why this priority**: Melhoria analítica incremental — o gráfico já comunica o volume por mês sem isso, essa é uma camada extra de contexto.

**Independent Test**: Abrir o Dashboard com histórico de pelo menos 3 meses e conferir que o gráfico mostra uma linha de referência de média e destaca visualmente a barra do mês corrente.

**Acceptance Scenarios**:

1. **Given** dados de "demandas criadas por mês" dos últimos 12 meses, **When** o gráfico renderiza, **Then** uma linha de referência indica a média do período.
2. **Given** o mês corrente presente nos dados, **When** o gráfico renderiza, **Then** a barra correspondente ao mês atual tem destaque visual distinto das demais.

### Edge Cases

- O que acontece quando não há nenhum certificado vencendo (`next_expiring` vazio)? A tabela deve continuar mostrando o estado vazio atual, sem tentar agrupar/paginar nada.
- Como o sistema trata um card de KPI cujo valor é zero? Deve manter a cor "ok"/neutra, não a cor de severidade do threshold.
- O que acontece se todos os 3 conjuntos de análise (`reqs_by_month`, `key_types`, `cert_health`) estiverem vazios? A linha de painéis inteira não deve renderizar (comportamento atual já cobre isso).
- Como o agrupamento por data (US5) se comporta com 1 ou 2 certificados na mesma data? Deve renderizar como linha(s) simples soltas — o agrupamento só entra em vigor a partir de 3 certificados na mesma data.
- Como a ação de renovação rápida (US6) se comporta se o certificado for de ownership externo sem e-mail de parceiro cadastrado? O formulário pré-preenchido deve abrir mesmo assim, com o campo de e-mail em branco pro usuário completar.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE colorir cada card de KPI de vencimento conforme faixas fixas de dias — até 30 dias: severidade crítica; até 60 dias: severidade de atenção; acima de 60 dias: severidade ok — calculadas a partir do valor do threshold em si (não da posição no array de configuração), suportando qualquer quantidade de janelas de alerta configuradas.
- **FR-002**: O sistema DEVE exibir um indicador textual nos cards de KPI cujo valor é cumulativo, informando que o número inclui os certificados já contados em thresholds menores.
- **FR-003**: O card "Vencidos" DEVE ser visualmente distinguível dos cards de "vencem em ≤N dias", refletindo maior severidade (é passado, não previsão).
- **FR-004**: O sistema DEVE garantir contraste mínimo de 4.5:1 (WCAG AA) entre texto e fundo em todos os badges de status de lifecycle de certificado, nos temas claro e escuro.
- **FR-005**: O rótulo do status de lifecycle atualmente "Excluir" DEVE ser renomeado para um texto que não seja interpretável como botão de ação.
- **FR-006**: A linha de painéis de análise (demandas por mês / tipos de chave / saúde dos certificados) DEVE distribuir os painéis presentes numa grade sem deixar espaço vazio quando os 3 estiverem disponíveis.
- **FR-007**: Cada badge de ambiente (PRD/TQS/HMP/DES) DEVE expor, via tooltip, o nome completo do ambiente que representa.
- **FR-008**: O Dashboard DEVE exibir uma legenda visível explicando as 4 siglas de ambiente e a lógica de cor associada.
- **FR-009**: A tabela "Próximos vencimentos" DEVE agrupar, numa linha-resumo com contagem expansível, os certificados que vencem na mesma data sempre que houver 3 ou mais nessa data; com 1 ou 2 certificados na mesma data, eles continuam exibidos como linhas soltas normais.
- **FR-010**: Cada linha da tabela "Próximos vencimentos" referente a um certificado sem demanda ativa DEVE oferecer uma ação de início rápido de renovação, que abre o formulário de nova demanda pré-preenchido.
- **FR-011**: Certificados com demanda ativa NÃO DEVEM oferecer a ação de renovação rápida (evita duplicidade).
- **FR-012**: Cada entrada do feed "Atividade Recente" DEVE ocupar no máximo 2 linhas de texto.
- **FR-013**: Sequências de 3 ou mais eventos consecutivos no feed de atividade com a mesma ação e a mesma REQ DEVEM ser agrupadas numa única entrada com contador de repetições; sequências de 1 ou 2 eventos idênticos permanecem exibidas normalmente, sem agrupar.
- **FR-014**: O gráfico "Demandas criadas por mês" DEVE exibir uma linha de referência com a média do período exibido.
- **FR-015**: O gráfico "Demandas criadas por mês" DEVE destacar visualmente a barra correspondente ao mês corrente, quando presente nos dados.

### Key Entities

- **Card de KPI (stat-card)**: Um indicador numérico do Dashboard (vencidos, vencem em N dias, REQs abertas, certificados totais); tem um valor, um rótulo, uma cor de severidade e, opcionalmente, um indicador de "cumulativo".
- **Certificado (linha de vencimento)**: CN, ambiente, data de vencimento, dias restantes, status de lifecycle, ownership, se tem demanda ativa — usado tanto na tabela de vencimentos quanto na ação de renovação rápida.
- **Evento de atividade**: ação realizada, REQ relacionada, detalhe textual, usuário, timestamp — pode ser agrupado com eventos idênticos consecutivos.
- **Badge de ambiente**: sigla (PRD/TQS/HMP/DES), nome completo, cor de severidade associada.
- **Badge de status de lifecycle**: status do certificado no inventário, rótulo legível, par de cor de fundo/texto com contraste garantido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos pares de cor/fundo dos badges de status de lifecycle atingem contraste mínimo 4.5:1 nos temas claro e escuro.
- **SC-002**: A cor de severidade de cada card de KPI corresponde corretamente ao valor do threshold em cenários com 1 a 6 janelas de alerta configuradas, sem exceção.
- **SC-003**: Com os 3 conjuntos de dados de análise disponíveis, 0% de área vazia sobra na linha de painéis (os 3 preenchem as 3 colunas).
- **SC-004**: Usuários identificam corretamente o significado de uma sigla de ambiente sem precisar perguntar a um colega ou consultar documentação externa — verificável pela presença do tooltip/legenda em 100% dos badges de ambiente exibidos.
- **SC-005**: Uma renovação pode ser iniciada a partir do Dashboard em no máximo 2 cliques (ícone de ação → formulário pré-preenchido), sem navegar pra outra view.
- **SC-006**: Em bases com certificados vencendo na mesma data, o número de linhas visíveis por padrão na tabela "Próximos vencimentos" cai em pelo menos 50% comparado à listagem 1:1 atual.

## Assumptions

- O endpoint `GET /dashboard` pode ser estendido com novos campos (ownership, parceiro externo, e-mail, flag de demanda ativa) na lista `next_expiring` sem quebrar consumidores existentes, já que é consumido só pela view do Dashboard.
- A paleta de cores por severidade (vermelho/âmbar/verde ou equivalente) já usada no restante do sistema é reaproveitada — não é criada uma paleta nova.
- A definição de "cumulativo" nos cards de threshold é a already-existente no backend (`dias_restantes <= N`), não uma mudança na lógica de contagem.
- O agrupamento de atividade repetida (US7) considera "consecutivo" apenas dentro da janela de 10 eventos mais recentes já retornada pelo endpoint hoje — não requer buscar mais histórico.
- A ação de renovação rápida (US6) reaproveita o fluxo de criação de demanda de renovação já existente no sistema (usado no Monitor de Vencimentos), sem criar um fluxo paralelo.
