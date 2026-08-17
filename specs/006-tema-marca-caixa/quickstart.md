# Quickstart: Validar o Modo CAIXA (escopo completo — cor, ícone, fonte, login)

Guia de validação manual — não há suíte automatizada de frontend no projeto. Backend não é alterado; nenhum comando de migração/seed é necessário além do setup normal do projeto.

## Pré-requisitos

- Implementação concluída conforme `contracts/caixa-accent-tokens.md`, `contracts/caixa-brand-icon.md`, `contracts/caixa-icon-skin.md` e `contracts/caixa-typography-login.md`.
- App rodando localmente e acessível no navegador, logado com um usuário qualquer.

## Parte 1 — Cor e persistência (já validado em T001-T013, reconferir sem regressão)

1. **Ativar o Modo CAIXA**: Aparência → clicar swatch "caixa". Sidebar fica azul `#0066B3`, `.brand-icon` vira o X, itens de nav legíveis em branco.
2. **Persistência**: recarregar (F5) — Modo CAIXA continua ativo.
3. **Claro/escuro**: alternar tema com Modo CAIXA ativo — sidebar permanece azul institucional nos dois; botão primário usa `#0066B3` no claro e `#0097D7` no escuro.
4. **Reversão**: selecionar outra cor de destaque — sidebar e ícone voltam ao padrão.
5. **Laranja pontual**: um badge `.k-cat` fica laranja; badges de status semântico (sucesso/erro/aviso) continuam com as cores de sempre.

## Parte 2 — Ícones de linha (US4, novo)

6. **Nav lateral**: com Modo CAIXA ativo, verificar que os 18 itens do menu lateral mostram ícone de linha, não emoji.
7. **Navegação entre views**: abrir pelo menos 3 seções diferentes (ex. Dashboard, Geração, Instalação) — título de cada página e ícones de botões/badges aparecem como ícone de linha.
8. **Modal**: abrir qualquer modal do sistema (ex. detalhe de um certificado) — ícones dentro do modal também aparecem como ícone de linha.
9. **Sub-render sem navegação nova**: interagir com um filtro/busca que atualiza uma lista sem trocar de view (ex. busca de perfil HSM, se aplicável) — ícones do resultado atualizado também usam ícone de linha.
10. **Toast intacto**: disparar uma ação que gera notificação temporária (toast) — o toast continua mostrando emoji (se tinha), sem troca — valida FR-012/SC-007.
11. **Dado de usuário intacto**: verificar o nome de usuário exibido no rodapé da sidebar — não é afetado mesmo que contenha caractere igual a um emoji mapeado.
12. **Reversão total**: desativar o Modo CAIXA — navegar pelas mesmas 3 views do passo 7 e confirmar que os emojis originais voltaram em 100% dos pontos — valida SC-008.

## Parte 3 — Tipografia (US5, novo)

13. Com Modo CAIXA ativo, comparar visualmente o nome "CertHub" na sidebar e o título de uma página contra um parágrafo/tabela normal — os primeiros devem estar em Poppins (mais geométrica/arredondada), o corpo continua na fonte de sistema de sempre.

## Parte 4 — Cor completa (US6, novo)

14. Com Modo CAIXA ativo, verificar que o título de qualquer página (`.view-title`) está na cor institucional (azul), não neutro.
15. Em tema escuro com Modo CAIXA ativo, clicar um botão de ação primária (ex. "Nova solicitação") e usar as ferramentas de acessibilidade do navegador (DevTools → Accessibility, ou extensão de contraste) para confirmar razão ≥ 4.5:1 entre o texto do botão e o fundo `#0097D7`.

## Parte 5 — Login e favicon (US7, novo)

16. Com Modo CAIXA ativo, fazer logout — a tela de login deve mostrar a cor institucional e o ícone X no lugar do emoji, mesmo sem estar autenticado.
17. Verificar a aba do navegador — o favicon deve ser o X institucional (index.html e login.html).
18. Limpar `localStorage` (ou usar uma aba anônima nunca usada) e abrir a tela de login — deve aparecer exatamente como antes desta feature (sem cor/ícone institucional), confirmando o default seguro.

## Critério de aceite do quickstart

Todos os 18 passos produzem o resultado esperado, sem regressão nas 5 opções de destaque existentes, no comportamento de tema claro/escuro fora do Modo CAIXA, nem em toasts/dados de usuário/badges de status de domínio (`.badge-lc-*`) em nenhuma circunstância.
