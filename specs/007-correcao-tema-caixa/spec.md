# Feature Specification: Correção de Cores e Layout no Modo CAIXA

**Feature Branch**: `007-correcao-tema-caixa`

**Created**: 2026-08-16

**Status**: Draft

**Input**: User description: "Eu ainda acho que a interface está com as cores destonantes, outra coisa, a aba decodificar pem está com o layout quebrado, vamos garantir que as cores no tema da caixa, tanto no modo claro como escuro sigam o padrão de cores"

## Nota de escopo

Esta spec é um refinamento sobre `006-tema-marca-caixa` (Modo CAIXA institucional,
já implementado). Não reabre nem duplica as User Stories 1-7 daquela spec —
assume que o Modo CAIXA já existe, ativa a paleta azul/laranja institucional e
os ícones de marca, e foca no que ficou faltando depois de uso real: pontos da
interface onde a cor ainda destoa da identidade institucional, e um bug de
layout na aba Decoder.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cor institucional coerente em todo elemento de destaque (Priority: P1)

Um usuário com o Modo CAIXA ativo navega pela interface, em tema claro e em
tema escuro, e espera que **todo** elemento visual de destaque (não só sidebar,
cabeçalho e botão primário) use consistentemente a paleta azul/laranja
institucional — sem caixas de cor genéricas que pareçam soltas ou fora do
padrão de marca.

**Why this priority**: É a crítica direta e repetida do usuário sobre o Modo
CAIXA ("ainda acho que a interface está com as cores destonantes") — sem
resolver isso, o modo institucional continua parecendo malfeito mesmo depois
da primeira leva de implementação (spec 006).

**Independent Test**: Com o Modo CAIXA ativo, navegar pelo menu lateral e
observar o item ativo/hover — a cor de destaque usada deve visivelmente
pertencer à mesma família de azul institucional da sidebar (não uma caixa
escura ou pastel genérica que contrasta mal com o azul sólido ao redor).
Repetir em tema claro e escuro.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo em tema claro, **When** o usuário abre
   qualquer item do menu lateral, **Then** o destaque do item ativo usa uma
   variante da paleta institucional (não a cor de destaque genérica usada
   pelas outras 5 opções de cor), mantendo contraste legível sobre o azul da
   sidebar.
2. **Given** o Modo CAIXA está ativo em tema escuro, **When** o usuário abre
   qualquer item do menu lateral, **Then** o mesmo se aplica — o destaque do
   item ativo não pode aparecer como uma caixa escura/pastel destoante sobre
   o azul institucional.
3. **Given** o Modo CAIXA está ativo, **When** o usuário revisa qualquer
   elemento de UI que hoje herda cor de destaque genérica (`--accent`,
   `--accent-soft`, `--accent-text`) fora da sidebar/cabeçalho/botão primário
   já cobertos pela spec 006, **Then** esse elemento também reflete a paleta
   institucional de forma coerente com o restante da tela.

---

### User Story 2 - Tipografia de marca não depende de rede externa (Priority: P2)

Um usuário com o Modo CAIXA ativo vê o nome do produto e os títulos de página
na tipografia geométrica de marca (Poppins) de forma consistente, mesmo que a
rede não tenha acesso a serviços externos (ambiente interno, offline, CSP
restritivo) — sem cair silenciosamente para uma fonte diferente que quebra a
identidade visual pretendida.

**Why this priority**: Hoje a fonte é carregada via `@import` de um CDN
externo (Google Fonts); se esse recurso falhar, a tipografia de marca não
aparece e ninguém percebe o motivo — isso é uma causa direta e concreta de
"cores/identidade destonante" percebida pelo usuário, e contraria o princípio
já adotado para os ícones de marca (FR-013 da spec 006: nenhuma dependência
externa em tempo de execução).

**Independent Test**: Com o Modo CAIXA ativo, bloquear o acesso ao domínio do
CDN de fontes (ex.: via ferramenta de desenvolvedor do navegador) e recarregar
a página — o nome do produto e os títulos de página devem continuar usando
uma tipografia com o mesmo espírito geométrico, sem regressão visível.

**Acceptance Scenarios**:

1. **Given** o Modo CAIXA está ativo e o dispositivo não tem acesso a serviços
   de fonte externos, **When** o usuário carrega qualquer página do app,
   **Then** a tipografia de marca nos títulos/nome do produto permanece
   consistente com o espírito geométrico da marca, sem depender de uma
   requisição de rede externa em tempo de execução.
2. **Given** o Modo CAIXA está ativo e o dispositivo tem acesso normal à
   internet, **When** o usuário carrega qualquer página, **Then** o
   comportamento visual não piora em relação ao que já existe hoje.

---

### User Story 3 - Aba Decoder sem sobreposição de layout (Priority: P1)

Um usuário abre a aba "Decoder" (decodificar PEM/CSR/certificado/chave/PFX)
para colar ou enviar um arquivo e ver o resultado decodificado, e espera que
os dois painéis da tela (formulário de entrada e repositório de CSRs) e a
tabela de resultado decodificado permaneçam legíveis e dentro de seus
respectivos cartões — sem colunas se sobrepondo ou conteúdo vazando para fora
da área esperada.

**Why this priority**: Reportado pelo usuário como layout quebrado ("colunas
sobrepõem/vazam") — impede o uso confiável de uma funcionalidade central do
app (decodificação de certificados/CSRs), independente do tema de cor ativo.

**Independent Test**: Abrir a aba Decoder, colar/enviar um certificado, CSR,
chave privada ou PFX real (incluindo um com valores longos, como múltiplos
SANs ou hash de thumbprint) e confirmar visualmente que o painel de resultado,
o formulário e o repositório de CSRs continuam cada um dentro do seu próprio
cartão, sem sobreposição, em tema claro e escuro e nas larguras de tela já
suportadas pelo restante do app (breakpoint responsivo em 980px).

**Acceptance Scenarios**:

1. **Given** o usuário está na aba Decoder em uma largura de tela ≥ 980px,
   **When** a página termina de carregar, **Then** o painel de formulário e o
   painel "Repositório de CSRs" aparecem lado a lado, cada um contido dentro
   do seu próprio cartão, sem sobreposição.
2. **Given** o usuário está na aba Decoder em uma largura de tela < 980px,
   **When** a página termina de carregar, **Then** os painéis empilham
   verticalmente sem cortar ou sobrepor conteúdo.
3. **Given** o usuário decodifica um certificado com valores longos (ex.:
   lista de SANs com múltiplos domínios, thumbprint, subject extenso),
   **When** o resultado é exibido, **Then** o conteúdo quebra linha ou rola
   dentro do próprio cartão, sem forçar o painel a vazar sobre o painel
   vizinho nem causar rolagem horizontal da página inteira.
4. **Given** o Modo CAIXA está ativo ou não, **When** o usuário usa a aba
   Decoder, **Then** o comportamento de layout descrito acima é o mesmo — o
   bug de layout não é específico de nenhum tema de cor.

---

### Edge Cases

- O que acontece se a fonte de marca (Poppins) falhar ao carregar hoje? Cai
  silenciosamente para a fonte padrão do sistema, sem aviso — é justamente a
  causa que a User Story 2 corrige.
- O que acontece com um valor decodificado extremamente longo e sem espaços
  (ex.: uma lista de SANs concatenada sem separador visual, ou um subject DN
  muito extenso)? Deve quebrar linha ou rolar dentro do próprio cartão, nunca
  empurrar o layout dos painéis vizinhos.
- O que acontece com elementos de UI que já usam cores semânticas de domínio
  (sucesso/erro/aviso, badges de ciclo de vida de local de instalação)? Ficam
  fora do escopo desta correção — mesma exclusão já definida na spec 006, essas
  cores não são de marca institucional.
- O que acontece nas outras 5 cores de destaque (não-CAIXA) e no tema padrão
  do CertHub? Fora de escopo — esta spec corrige apenas o Modo CAIXA, temas
  claro e escuro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Quando o Modo CAIXA estiver ativo, o destaque do item de
  navegação ativo/hover na barra lateral DEVE usar uma variante da paleta
  institucional CAIXA (não os tokens de cor de destaque genéricos
  compartilhados com as outras 5 opções de cor), mantendo contraste legível
  (mínimo AA) sobre o fundo azul institucional da sidebar, em tema claro e
  escuro.
- **FR-002**: Quando o Modo CAIXA estiver ativo, qualquer outro elemento de
  UI que hoje herda cor de destaque genérica fora do que já foi corrigido pela
  spec 006 (sidebar, cabeçalho, botão primário, título de página) DEVE ser
  revisado e, quando aplicável, migrado para refletir a paleta institucional
  de forma visualmente coerente com os elementos já corrigidos.
- **FR-003**: A tipografia de marca (usada no nome do produto e nos títulos de
  página quando o Modo CAIXA está ativo) NÃO DEVE depender de uma requisição
  de rede a um serviço externo em tempo de execução para se aplicar
  corretamente — deve permanecer visualmente consistente mesmo sem acesso a
  esse serviço.
- **FR-004**: A aba Decoder DEVE renderizar o painel de formulário e o painel
  "Repositório de CSRs" cada um contido dentro do seu próprio cartão, sem
  sobreposição, em qualquer largura de tela já suportada pelo restante do
  app (incluindo abaixo e acima do breakpoint responsivo de 980px).
- **FR-005**: A tabela de resultado decodificado na aba Decoder DEVE exibir
  valores longos (SANs múltiplos, thumbprint, subject extenso) quebrando
  linha ou rolando dentro do próprio cartão, sem forçar sobreposição com o
  painel vizinho nem rolagem horizontal da página inteira.
- **FR-006**: O comportamento de layout da aba Decoder (FR-004, FR-005) DEVE
  ser idêntico independentemente do tema de cor ativo (Modo CAIXA, qualquer
  uma das 5 cores de destaque, ou padrão do CertHub).

### Key Entities

- **Paleta CAIXA** (já definida na spec 006): estendida nesta correção para
  cobrir também os tokens de estado do menu lateral (item ativo/hover) e
  qualquer outro elemento de destaque genérico ainda não migrado.
- **Preferência de Aparência do Usuário** (já existente): não é alterada por
  esta spec, apenas os valores visuais que ela ativa quando o Modo CAIXA está
  selecionado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Com o Modo CAIXA ativo, em tema claro e escuro, 0 elementos de
  destaque visível na interface (incluindo o item ativo do menu lateral) usam
  uma cor fora da paleta institucional CAIXA, verificável por inspeção visual
  das telas principais.
- **SC-002**: A tipografia de marca do Modo CAIXA permanece visualmente
  consistente em 100% dos carregamentos de página, mesmo com acesso a redes
  externas bloqueado.
- **SC-003**: A aba Decoder renderiza sem sobreposição ou vazamento de
  conteúdo entre painéis em 100% das combinações testadas de tema (claro/
  escuro) e largura de tela (≥980px e <980px).
- **SC-004**: Decodificar um certificado com valores longos (SANs múltiplos,
  thumbprint) não produz rolagem horizontal da página nem sobreposição de
  painéis, verificável em pelo menos 2 casos de teste com conteúdo real longo.

## Assumptions

- O item ativo/hover do menu lateral é o exemplo concreto de "cor destonante"
  identificado nesta sessão; a correção de coerência de cor (FR-002) é
  intencionalmente aberta para cobrir outros elementos equivalentes
  encontrados durante a implementação, não uma lista fechada.
- A troca de fonte de marca para uma fonte auto-hospedada (ou fallback de
  sistema com o mesmo espírito geométrico) é uma decisão técnica da fase de
  plano — esta spec só exige que o resultado visual não dependa de rede
  externa, sem prescrever a fonte final.
- O bug de layout da aba Decoder é tratado como defeito geral de CSS/HTML da
  página, não como algo introduzido pelo Modo CAIXA — por isso o FR-006 exige
  que a correção valha para todos os temas, não só o institucional.
- Certificados/CSRs com valores muito longos (múltiplos SANs, thumbprints)
  usados para validar SC-004 podem ser gerados via dados de demonstração
  existentes no projeto (`scripts/demo_data.py`) ou construídos manualmente
  para teste, já que a base atual de dados de demo não continha exemplos com
  múltiplos SANs no momento desta investigação.
