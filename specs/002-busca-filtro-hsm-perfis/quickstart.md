# Quickstart: Busca de Demandas, Filtros/Ordenação e Perfis de HSM

Guia de validação manual/end-to-end das 4 user stories. Assume app rodando localmente (`uvicorn app.main:app --reload`) com usuário autenticado.

## Pré-requisitos

- Base com volume razoável de demandas para testar US1/US2 de forma representativa (ex.: usar `demo_data.py` / gerador de dados aleatórios já existente no projeto para popular dezenas/centenas de REQs).
- Uma configuração de HSM (mesmo que fake/mock) já salva em `hsm_dinamo_config` de uma instalação anterior, para validar a migração automática de US4.

## US1 — Buscar demanda ao vincular uma CSR

1. Acesse **Gerar CSR**.
2. No campo "Demanda vinculada", digite parte do número de uma REQ existente (ex.: `00123`).
3. **Esperado**: a lista de sugestões mostra apenas REQs cujo número contém o texto digitado (contrato: `contracts/req-picker-component.md`).
4. Repita digitando parte de um CN em vez do número da REQ — sugestões devem filtrar por CN também.
5. Selecione uma sugestão, gere a CSR, e confirme (via Histórico/Auditoria) que ficou vinculada à REQ correta.
6. Repita o mesmo teste nas telas: Decoder, HSM → Gerar CSR, referência de credencial de um local de instalação, e no fluxo de avançar demanda para Instalação — comportamento deve ser idêntico nas 5 telas.

## US2 — Filtrar e ordenar em Monitor, Geração e Instalação

1. Acesse **Demandas de Geração**.
2. Aplique um filtro (ex.: ambiente = PRD) e escolha ordenar por "Ambiente" ou "REQ".
3. **Esperado**: lista mostra só itens do ambiente filtrado, na ordem escolhida (contrato: `contracts/reqs-sort.md`, `GET /reqs?env=PRD&sort=env&dir=asc`).
4. Repita em **Demandas de Instalação** — mesmas opções de ordenação devem estar disponíveis.
5. Confirme em **Monitor de Vencimentos** que filtro + busca + ordenação continuam combináveis como hoje (sem regressão).
6. Limpe os filtros — lista volta ao total, ordenação padrão.

## US3 — Layout da aba HSM

1. Acesse a aba **HSM (Dinamo)** em uma janela de largura de desktop padrão (ex.: 1440px).
2. **Esperado**: o painel "🔎 Buscar no HSM" tem o mesmo espaçamento entre label/campo/botão que os demais painéis da mesma aba (Criar chave, Importar certificado, Gerar CSR, Exportar).
3. Redimensione a janela para larguras menores (ex.: 1024px, 768px) e confirme que nada se sobrepõe.

## US4 — Perfis de HSM (PRD/NPRD)

1. **Migração**: com uma instalação que já tinha `hsm_dinamo_config` preenchido, acesse a aba HSM pela primeira vez após o deploy. **Esperado**: operação funciona normalmente sem pedir novo cadastro (perfil "Padrão" criado automaticamente e ativo).
2. Vá em **Configurações** → seção HSM (Dinamo) e cadastre um segundo perfil nomeado "NPRD" com host/porta/usuário/senha diferentes do perfil existente (renomeado ou mantido como "PRD").
3. Na aba **HSM**, use o seletor de perfil ativo para trocar entre "PRD" e "NPRD" (`PUT /hsm/active-profile`, contrato em `contracts/hsm-profiles-api.md`).
4. **Esperado**: a troca é instantânea (sem recarregar credenciais manualmente) e uma operação de busca no HSM (🔎 Buscar no HSM) passa a consultar o HSM do perfil selecionado.
5. Tente cadastrar um segundo perfil com o mesmo nome de um já existente — **esperado**: erro claro, cadastro rejeitado (FR-011).
6. Tente excluir o único perfil restante (ou o perfil atualmente ativo sem trocar antes) — **esperado**: exclusão bloqueada (FR-012).

## Testes automatizados de referência

- `tests/test_hsm_routes.py` — estender para cobrir `GET /hsm/profiles`, `PUT /hsm/active-profile`, e a migração automática de `hsm_dinamo_config` → `hsm_dinamo_profiles`.
- Novo teste para `GET /reqs?sort=...&dir=...` (parâmetros novos, valores inválidos caindo no default).
