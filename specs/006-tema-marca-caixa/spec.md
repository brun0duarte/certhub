# Feature Specification: Tema Institucional CAIXA

**Feature Branch**: `006-tema-marca-caixa`

**Created**: 2026-08-16

**Last Amended**: 2026-08-16 (escopo expandido: cor+fonte+logo+ícones em toda a interface, não só cor de destaque)

**Status**: Draft

**Input**: User description: "Vamos criar um novo tema com base no manual de marca da caixa economica federal. file:///home/bruno/Downloads/manual-de-identidade-visual-caixa.pdf" — refinado posteriormente: "quando eu disse que queria um novo tema, era para mudar toda a interface, não apenas a cor de destaque [...] cores, fontes e logo, vamos substituir esses emoji"

## Nota de escopo

A primeira versão desta spec tratou o Modo CAIXA como "mais uma cor de destaque" (User Stories 1-3 abaixo) — isso já foi implementado e continua válido como base. O usuário deixou claro depois que isso é insuficiente: o Modo CAIXA precisa mudar cor, tipografia, logo **e os ícones de interface** (hoje emojis) de forma abrangente, não só a cor de destaque. As User Stories 4-7 abaixo cobrem essa expansão.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ativar o modo visual CAIXA (Priority: P1)

Um usuário do CertHub abre a aba Aparência e escolhe o modo institucional CAIXA, fazendo com que a barra lateral, o cabeçalho e os elementos de destaque da aplicação passem a refletir a identidade visual oficial da CAIXA (azul e laranja institucionais, elemento-síntese "X" como marca d'água/ícone), em vez do visual neutro padrão do CertHub.

**Why this priority**: É o núcleo da funcionalidade — sem a opção de ativação e a reskin visual básica, não existe "tema CAIXA".

**Independent Test**: Pode ser testado isoladamente abrindo a aba Aparência, selecionando "Modo CAIXA" e verificando visualmente que sidebar, cabeçalho e botões primários mudam para as cores institucionais (azul #0066B3), sem precisar de nenhuma outra funcionalidade do sistema.

**Acceptance Scenarios**:

1. **Given** o usuário está na aba Aparência com o tema padrão ativo, **When** ele seleciona "Modo CAIXA", **Then** a barra lateral, o cabeçalho e os botões primários passam a usar o azul institucional CAIXA (#0066B3) e o elemento-síntese "X" aparece como ícone/marca no lugar do ícone genérico atual.
2. **Given** o Modo CAIXA está ativo, **When** o usuário recarrega a página ou reabre o app em outra sessão no mesmo navegador, **Then** o Modo CAIXA continua ativo (preferência persistida).
3. **Given** o Modo CAIXA está ativo, **When** o usuário seleciona novamente uma das 5 cores de destaque padrão (verde, roxo, teal, âmbar, vermelho) ou volta ao "padrão CertHub", **Then** o visual institucional é desfeito e a aparência retorna ao comportamento atual do sistema.

**Status**: ✅ Implementado (T001-T009).

---

### User Story 2 - Alternar entre claro e escuro no Modo CAIXA (Priority: P2)

Um usuário com o Modo CAIXA ativo alterna entre tema claro e escuro (como já faz hoje), e espera que a paleta institucional se adapte mantendo legibilidade e contraste adequados em ambos os modos.

**Why this priority**: O app já oferece claro/escuro como funcionalidade consolidada; o Modo CAIXA precisa respeitar essa escolha para não regredir uma funcionalidade existente, mas isso é secundário à existência do modo em si (P1).

**Independent Test**: Com o Modo CAIXA ativo, alternar claro/escuro pelo botão existente e verificar que o azul e o laranja institucionais permanecem legíveis e com contraste adequado em ambos os fundos.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo em tema claro, **When** o usuário alterna para o tema escuro, **Then** a interface usa uma variante escura da paleta CAIXA (fundo escuro, azul/laranja ajustados para contraste), sem quebrar a identidade institucional.
2. **Given** o Modo CAIXA está ativo em tema escuro, **When** o usuário alterna para o tema claro, **Then** a interface volta à variante clara da paleta CAIXA (fundo claro, azul institucional cheio como nas versões "chapada positiva"/"volume positiva" do manual).

**Status**: ✅ Implementado (T010).

---

### User Story 3 - Uso pontual da cor secundária (laranja) em alertas/destaques (Priority: P3)

Elementos que hoje usam cores semânticas de destaque pontual (ex.: badges, chips, indicadores de atenção que não sejam erro/sucesso/aviso já mapeados) podem usar o laranja institucional CAIXA quando o Modo CAIXA está ativo, reforçando a identidade sem virar a cor dominante da interface.

**Why this priority**: É um refinamento visual que reforça a fidelidade ao manual de marca, mas a interface já é funcional e reconhecível como "CAIXA" apenas com o azul (P1) e os dois modos claro/escuro (P2).

**Independent Test**: Com o Modo CAIXA ativo, localizar um elemento de destaque pontual mapeado (ex.: um badge de "novo" ou indicador de destaque neutro) e confirmar que usa o laranja institucional (#F7941E) em vez de uma cor genérica, sem substituir as cores semânticas já existentes de sucesso (verde), erro (vermelho) e aviso (âmbar).

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo, **When** o usuário visualiza um elemento de destaque pontual não-semântico (badge/chip neutro), **Then** esse elemento usa o laranja institucional CAIXA.
2. **Given** o Modo CAIXA está ativo, **When** o usuário visualiza um indicador de status já semântico (sucesso, erro, aviso), **Then** essas cores permanecem inalteradas (verde/vermelho/âmbar), pois o laranja institucional não substitui semântica de status.

**Status**: ✅ Implementado (T011-T012).

---

### User Story 4 - Ícones de marca substituem os emojis da interface (Priority: P1)

Um usuário com o Modo CAIXA ativo navega pelo app e vê ícones de linha consistentes (não emojis) na navegação lateral, nos títulos de página, nos botões e nos badges — reforçando a sensação de um produto com identidade visual própria em vez de uma interface genérica com emojis do sistema operacional.

**Why this priority**: É a mudança mais visível e mais pedida explicitamente pelo usuário ("vamos substituir esses emoji"); sem isso, o Modo CAIXA continua parecendo "cor de destaque com nome bonito", que foi exatamente a crítica recebida.

**Independent Test**: Com o Modo CAIXA ativo, navegar por pelo menos 3 seções diferentes do menu lateral e abrir 1 modal, verificando que os ícones de nav, os títulos de página e os botões/badges mostram ícones de linha (não emojis); desativar o Modo CAIXA e confirmar que os emojis originais voltam em todos os mesmos pontos.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo, **When** o usuário abre qualquer item do menu lateral, **Then** o ícone daquele item aparece como ícone de linha (não emoji).
2. **Given** o Modo CAIXA está ativo, **When** o usuário abre uma página ou um modal que tem botões/badges com ícone, **Then** esses ícones aparecem como ícones de linha.
3. **Given** o Modo CAIXA está ativo, **When** o usuário vê uma notificação temporária (toast) ou um nome de usuário/valor de dado exibido em tela, **Then** esse conteúdo permanece exatamente como hoje (emoji, se houver, não é trocado) — a troca de ícone não se aplica a mensagens temporárias nem a dados/texto livre.
4. **Given** o Modo CAIXA está desativado (qualquer outra cor de destaque ou padrão), **When** o usuário navega pelo app, **Then** todos os emojis aparecem exatamente como hoje, sem nenhuma mudança.

---

### User Story 5 - Tipografia de marca em títulos (Priority: P2)

Um usuário com o Modo CAIXA ativo vê o nome do produto na barra lateral e os títulos de cada página em uma tipografia com o mesmo espírito geométrico do logotipo CAIXA, reforçando a identidade visual sem comprometer a leitura do restante do conteúdo.

**Why this priority**: Reforça a identidade de marca de forma perceptível, mas o produto já é utilizável e reconhecível como "CAIXA" com cor+ícone (P1) mesmo sem essa mudança tipográfica.

**Independent Test**: Com o Modo CAIXA ativo, verificar visualmente que o nome "CertHub" na sidebar e o título de qualquer página usam uma tipografia diferente (mais geométrica/arredondada) do texto normal do corpo, e que o corpo de texto (parágrafos, tabelas, formulários) continua na fonte padrão de sempre.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo, **When** o usuário olha o nome do produto na sidebar ou o título de qualquer página, **Then** esse texto usa a tipografia de marca (geométrica), visivelmente diferente da fonte do corpo.
2. **Given** o Modo CAIXA está ativo, **When** o usuário lê o conteúdo normal de uma página (tabelas, formulários, parágrafos), **Then** esse conteúdo continua na fonte padrão do sistema, sem mudança.

---

### User Story 6 - Cor institucional alcança títulos e botões de ação (Priority: P2)

Um usuário com o Modo CAIXA ativo percebe a cor institucional não só na sidebar, mas também nos títulos de cada página e garante que o texto dos botões de ação primária continua legível em ambos os temas (claro/escuro).

**Why this priority**: Fecha lacunas de cor que o levantamento técnico identificou (título de página sem cor, botão primário nunca testado no azul escuro) — sem isso, partes da interface ficam "esquecidas" e quebram a consistência visual que o P1 (US1) começou.

**Independent Test**: Com o Modo CAIXA ativo, abrir qualquer página e verificar que o título usa o azul institucional, e clicar em um botão de ação primária (ex. "Nova solicitação") em tema claro e escuro, confirmando que o texto permanece legível nos dois casos.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo, **When** o usuário abre qualquer página, **Then** o título da página usa a cor institucional (variante clara ou escura conforme o tema ativo).
2. **Given** o Modo CAIXA está ativo em tema escuro, **When** o usuário vê um botão de ação primária, **Then** o texto do botão atende ao contraste mínimo legível (WCAG AA) sobre o azul institucional escuro.

---

### User Story 7 - Tela de login reflete o Modo CAIXA (Priority: P3)

Um usuário que já ativou o Modo CAIXA neste navegador vê a identidade institucional já na tela de login (antes mesmo de entrar no sistema), em vez de uma tela de login neutra seguida por um app institucional.

**Why this priority**: É consistência de borda a borda, mas o valor central do Modo CAIXA (P1-P4 acima) já é entregue inteiramente dentro do app, depois do login.

**Independent Test**: Com o Modo CAIXA já ativado em uma sessão anterior neste navegador, fazer logout e verificar que a tela de login mostra a cor institucional e o ícone de marca em vez do emoji genérico.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA foi ativado em uma sessão anterior neste navegador, **When** o usuário vê a tela de login (deslogado), **Then** a cor institucional e o ícone de marca (elemento-síntese "X") aparecem no lugar do emoji genérico, sem precisar estar autenticado.
2. **Given** o Modo CAIXA nunca foi ativado neste navegador, **When** o usuário vê a tela de login, **Then** ela aparece exatamente como hoje (sem mudança).

---

### Edge Cases

- O que acontece se o usuário tinha uma das 5 cores de destaque (`data-accent`) selecionada antes de ativar o Modo CAIXA? A seleção anterior de destaque é preservada em memória (não apagada), mas fica inativa enquanto o Modo CAIXA estiver ligado — ao desativar o Modo CAIXA, a cor de destaque anterior volta a valer.
- Como o sistema garante contraste de texto/ícones sobre o azul institucional em botões e sidebar, já que o manual não define uma paleta completa de UI (só a marca gráfica)? Cores de superfície, texto e estados (hover/disabled) que o manual não cobre devem ser derivadas seguindo o padrão de contraste já usado pelas paletas de destaque existentes (AA mínimo para texto sobre fundo colorido).
- O elemento-síntese "X" não pode ser distorcido, rotacionado, ter cores alteradas nem ser usado como marca d'água decorativa sobre imagens complexas (regras explícitas do manual, seção 1.2.4) — a aplicação como ícone de sidebar/marca/favicon deve respeitar essas restrições (proporção, cores oficiais, fundo sólido).
- O que acontece em relatórios/exportações (ex.: PDF de certificado, chain PEM) hoje neutros — eles também herdam o Modo CAIXA? Fora de escopo desta feature; o Modo CAIXA se aplica apenas à interface web do CertHub, não a documentos exportados.
- O que acontece com emojis que aparecem em notificações temporárias (toasts) que misturam texto fixo com dado dinâmico (ex. nome de um certificado)? Ficam fora da troca de ícone em qualquer tema — o risco de trocar um emoji no meio de texto que muda a cada notificação é maior que o ganho visual, então toasts continuam com emoji sempre, mesmo sob Modo CAIXA.
- O que acontece com emoji dentro de dado do usuário (ex. nome de exibição) ou de valores de domínio exibidos em tabela? Nunca são trocados — a troca de ícone é restrita a elementos de interface fixos (nav, títulos, botões, badges de status conhecidos), nunca a conteúdo dinâmico/texto livre.
- O que acontece com badges de status de "local de instalação" (ex. pedido/instalado/em inventário/reservado/fim de vida)? Ficam fora de escopo do Modo CAIXA — são cores semânticas de domínio (mesma lógica já aplicada a sucesso/erro/aviso na US3), não elementos de marca.
- A tela de login usa um tema escuro fixo hoje, independente da preferência de tema claro/escuro do usuário — esse comportamento pré-existente não muda nesta feature; só a cor institucional (accent) e o ícone de marca passam a refletir a escolha salva.

## Requirements *(mandatory)*

### Functional Requirements

**Já implementados (US1-3):**

- **FR-001**: O sistema DEVE oferecer, na aba Aparência, uma opção "Modo CAIXA" que ativa uma reskin institucional completa da interface (sidebar, cabeçalho, botões primários, links e elementos de destaque), lado a lado com as 5 cores de destaque já existentes (verde, roxo, teal, âmbar, vermelho) e o modo padrão do CertHub.
- **FR-002**: Quando o Modo CAIXA estiver ativo, o azul institucional CAIXA (Pantone 287C / #0066B3, com a variante de gradiente "volume" onde aplicável) DEVE ser a cor dominante de destaque (accent) em toda a interface.
- **FR-003**: O sistema DEVE usar o elemento-síntese "X" da CAIXA (extraído da versão chapada do manual) como ícone de marca da sidebar/cabeçalho quando o Modo CAIXA estiver ativo, respeitando as regras do manual: sem distorção, sem rotação, sem alteração de cores, com a área de proteção mínima especificada (1X ao redor do elemento) e tamanho não inferior à redução mínima definida para meio on-line (50px de largura).
- **FR-004**: O laranja institucional CAIXA (Pantone 151C / #F7941E) DEVE ser reservado para destaques pontuais não-semânticos (badges/chips neutros) e NÃO DEVE substituir as cores semânticas já existentes de sucesso, erro e aviso.
- **FR-005**: O Modo CAIXA DEVE funcionar corretamente tanto no tema claro quanto no tema escuro já existentes, com uma variante de paleta institucional definida para cada um, mantendo contraste de texto legível (mínimo AA) sobre fundos azuis/coloridos.
- **FR-006**: A escolha do Modo CAIXA DEVE ser persistida por usuário/navegador da mesma forma que a preferência de tema claro/escuro e de cor de destaque já são hoje (mesmo mecanismo de persistência local existente).
- **FR-007**: Ativar o Modo CAIXA DEVE desativar visualmente qualquer uma das 5 cores de destaque selecionadas anteriormente sem apagar essa seleção; desativar o Modo CAIXA (voltando ao padrão CertHub ou escolhendo outra cor de destaque) DEVE restaurar o comportamento visual atual do sistema.
- **FR-008**: O sistema NÃO DEVE reproduzir o logotipo completo "CAIXA" (wordmark) em nenhuma tela — apenas o elemento-síntese "X" pode ser usado como ícone, conforme decisão de escopo desta feature.
- **FR-009**: O sistema NÃO DEVE aplicar o azul/laranja institucional a documentos ou exportações gerados pelo CertHub (ex.: PDFs de certificado, cadeias PEM) — o Modo CAIXA é restrito à interface web.

**Novos (US4-7):**

- **FR-010**: Quando o Modo CAIXA estiver ativo, o sistema DEVE substituir os emojis usados como ícone de interface (navegação lateral, títulos de página, botões de ação, badges de status, opções da aba Aparência, ícone de marca) por um conjunto de ícones de linha consistente.
- **FR-011**: A substituição de emoji por ícone DEVE ocorrer apenas quando o Modo CAIXA estiver ativo; em qualquer outra opção de aparência (padrão ou as 5 cores de destaque), os emojis DEVEM permanecer exatamente como são hoje, sem nenhuma mudança.
- **FR-012**: A substituição de ícone NÃO DEVE afetar notificações temporárias (toasts), nomes/valores de dados do usuário ou qualquer outro texto livre/dinâmico — apenas elementos de interface fixos (nav, títulos, botões, badges de status conhecidos).
- **FR-013**: Os ícones usados na substituição DEVEM vir de um conjunto de ícones de linha de licença aberta (não desenhados exclusivamente para a marca CAIXA), hospedado como parte do próprio sistema (sem depender de serviço externo em tempo de execução para carregá-los).
- **FR-014**: Quando o Modo CAIXA estiver ativo, o nome do produto na barra lateral e os títulos de página DEVEM usar uma tipografia geométrica diferente da fonte padrão do corpo de texto; o corpo de texto (tabelas, formulários, parágrafos) NÃO DEVE mudar de fonte em nenhum tema.
- **FR-015**: Quando o Modo CAIXA estiver ativo, o título de cada página DEVE usar a cor institucional (variante clara ou escura conforme o tema ativo).
- **FR-016**: Quando o Modo CAIXA estiver ativo, o texto de botões de ação primária DEVE permanecer legível (contraste mínimo AA) sobre o azul institucional, tanto na variante clara quanto na escura.
- **FR-017**: Se o Modo CAIXA já foi ativado neste navegador, a tela de login DEVE refletir a cor institucional e o ícone de marca (elemento-síntese "X"), sem exigir que o usuário esteja autenticado para isso.
- **FR-018**: Badges de status de "local de instalação" (ciclo de vida: pedido, instalado, em inventário, reservado, excluir, fim de vida) NÃO DEVEM ser afetados pelo Modo CAIXA — permanecem com as cores semânticas atuais em qualquer tema.

### Key Entities

- **Preferência de Aparência do Usuário**: representa a escolha visual do usuário (tema claro/escuro, cor de destaque OU Modo CAIXA ativo), armazenada localmente por navegador, já existente hoje e estendida para incluir o novo modo institucional. É a mesma preferência lida pela tela de login (US7), sem exigir autenticação.
- **Paleta CAIXA**: conjunto de cores institucionais derivadas do manual de marca (azul #0066B3, laranja #F7941E, variantes claras/escuras e de gradiente) usado para preencher os tokens visuais (fundo, destaque, texto, bordas, título de página) quando o Modo CAIXA está ativo.
- **Conjunto de Ícones de Marca**: mapeamento entre os emojis usados hoje como ícone de interface e seus equivalentes em ícone de linha, usado apenas quando o Modo CAIXA está ativo; não inclui toasts, dados de usuário ou badges de status de domínio (ciclo de vida de local).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário consegue ativar o Modo CAIXA a partir da aba Aparência em no máximo 2 cliques.
- **SC-002**: Com o Modo CAIXA ativo, 100% dos elementos de destaque primário da interface (sidebar, cabeçalho, botões de ação primária) usam o azul institucional CAIXA, verificável visualmente sem inspecionar código.
- **SC-003**: A preferência pelo Modo CAIXA permanece ativa em 100% das vezes que o usuário recarrega a página ou reabre o app na mesma sessão de navegador.
- **SC-004**: Em qualquer combinação de Modo CAIXA + tema claro/escuro, o contraste de texto sobre fundos coloridos (sidebar, botão primário, título de página) atende ao critério WCAG AA (razão mínima 4.5:1 para texto normal).
- **SC-005**: Nenhuma tela do sistema, com o Modo CAIXA ativo, exibe o elemento-síntese "X" distorcido, rotacionado, com cor alterada ou em tamanho abaixo de 50px de largura, verificável por inspeção visual das telas principais (sidebar, cabeçalho, aba Aparência, favicon, login).
- **SC-006**: Com o Modo CAIXA ativo, 100% dos 18 itens do menu de navegação lateral mostram ícone de linha em vez de emoji.
- **SC-007**: Com o Modo CAIXA ativo, uma notificação temporária (toast) e um nome de usuário exibido em tela continuam mostrando o emoji original (se houver) sem nenhuma troca — validado navegando por pelo menos 3 fluxos que disparam toast.
- **SC-008**: Desativar o Modo CAIXA restaura 100% dos emojis originais em todos os pontos testados em SC-006/SC-007, sem nenhum resíduo visual do modo anterior.

## Assumptions

- O Modo CAIXA é uma opção de personalização visual opcional, não o tema padrão do CertHub para novas instalações — usuários continuam vendo o visual neutro atual até escolherem ativá-lo (decisão de escopo: "lado a lado").
- Não há necessidade de suporte a múltiplas variações do azul/laranja institucional (ex.: gradientes "volume" completos) fora dos elementos onde o manual os recomenda (marca gráfica); superfícies de UI (fundos de painel, bordas, texto) usam tons sólidos derivados da paleta oficial, já que o manual não define uma paleta de interface completa.
- O elemento-síntese "X" foi extraído/recriado a partir da versão chapada (positiva/negativa) publicada no manual (`manual-de-identidade-visual-caixa.pdf`, seção 1.2.1) como asset vetorial versionado no projeto — não há dependência de arquivo de logo original fornecido separadamente pela CAIXA.
- Esta feature não altera nomes, textos ou terminologia do CertHub para parecer um produto oficial da CAIXA — trata-se de uma opção de skin visual para uso interno, não de rebranding institucional formal.
- Documentos e exportações gerados pelo sistema (certificados, PDFs, cadeias PEM) permanecem fora do escopo do Modo CAIXA.
- O manual de marca da CAIXA fornecido cobre apenas o capítulo de marca gráfica (logotipo e elemento-síntese) — não define paleta de UI, tipografia de interface nem sistema de ícones. Tipografia (US5) e conjunto de ícones (US4) são decisões de design deste projeto, inspiradas no espírito geométrico da marca, não extraídas literalmente do manual.
- A tela de login mantém seu tema claro/escuro fixo atual (comportamento pré-existente, não relacionado a esta feature) — só a cor institucional e o ícone de marca passam a refletir a preferência salva.
- Badges de status de ciclo de vida de "local de instalação" e notificações temporárias (toasts) ficam permanentemente fora do escopo de troca visual do Modo CAIXA, por serem, respectivamente, semântica de domínio e conteúdo dinâmico — essa exclusão é definitiva, não uma lacuna a ser fechada depois.
