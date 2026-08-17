# Quickstart: Ajustes de Layout do HSM e Preservação de Estado entre Abas

Guia de validação manual das 3 user stories. Assume app rodando localmente (`uvicorn app.main:app --reload`) com usuário autenticado e ao menos 2 perfis de HSM cadastrados (ver `specs/002-busca-filtro-hsm-perfis/quickstart.md` pra cadastrar).

## US1 — Sem sobreposição do painel "Criar chave"

1. Acesse a aba **HSM (Dinamo)** em largura de desktop (1440px).
2. **Esperado**: os painéis "🔑 Criar chave" e "📥 Importar certificado emitido" (lado a lado) têm espaçamento claro em relação ao painel seguinte ("📝 Gerar CSR a partir de uma chave do HSM") — nenhum elemento encostado ou sobreposto (contrato: fix de CSS em `research.md` #1).
3. Repita em 1024px e 768px — sem sobreposição em nenhuma largura.
4. Repita em **Decoder**, **Certificados** e **Validar cadeia** (mesmas classes `.grid.grid-2`) — confirmar que o mesmo espaçamento passa a valer ali (efeito colateral desejado do fix).

## US2 — Perfil de HSM ativo visível no topo

1. Com ao menos 2 perfis cadastrados (ex.: PRD, NPRD), acesse a aba **HSM**.
2. **Esperado**: no topo da aba aparece o nome, host e usuário do perfil ativo (ex.: "PRD · 10.0.0.1 · master") — sem a senha em nenhum lugar da tela.
3. Troque o perfil ativo pelo seletor já existente.
4. **Esperado**: a informação exibida atualiza imediatamente pro novo perfil, sem precisar recarregar a página.
5. Remova todos os perfis (ou teste numa instalação sem nenhum cadastrado) — **esperado**: continua aparecendo o aviso "nenhum perfil configurado" no lugar da informação de perfil (sem quebrar o layout).

## US3 — Preservar dados ao trocar de aba

1. Acesse **Demandas de Geração**, aplique um filtro (ex.: ambiente = PRD), uma busca por texto, e navegue pra página 2 (se houver dados suficientes).
2. Troque pra outra aba (ex.: Dashboard) e volte pra **Geração**.
3. **Esperado**: filtro, busca e página 2 continuam aplicados exatamente como estavam, com os dados buscados de novo do servidor (não uma lista congelada).
4. Acesse **Gerar CSR**, preencha CN e alguns SANs sem clicar em "Gerar CSR".
5. Troque de aba e volte.
6. **Esperado**: CN e SANs digitados continuam no formulário.
7. Repita o teste na aba **HSM** (preencher rótulo em "Criar chave" sem enviar, trocar de aba, voltar) — campo continua preenchido.
8. Recarregue a página inteira (F5) em qualquer momento com campos preenchidos.
9. **Esperado**: tudo reseta — esse cenário está fora do escopo (FR-007), não é regressão.
10. Com uma lista filtrada preservada, altere os dados no servidor por outro meio (ex.: outra aba do navegador conclui uma demanda) de forma que o total de páginas diminua abaixo da página preservada.
11. **Esperado**: ao voltar pra aba com aquele filtro, a lista ajusta automaticamente pra última página válida em vez de aparecer vazia (FR-009).

## Testes automatizados de referência

- Extensão de `tests/test_hsm_routes.py`: `GET /hsm/profiles` passa a retornar `host`/`username` por perfil, nunca `password`.
- US1 e US3 são mudanças de frontend (CSS e JS puro, sem framework de teste no projeto) — validação é manual/visual conforme os passos acima; sem cobertura pytest aplicável.
