# Research: Demandas de Revogação de Certificados

## 1. Tipo de demanda "revogação" já parcialmente reconhecido, mas sem fluxo próprio

**Decision**: Reaproveitar o `demand_type='revogacao'` já existente (já presente em `DEMAND_TYPES`/`STATUS_LABEL`/`REQ_STATUSES` no frontend, já aceito por `newDemandModal` como opção de tipo, já contemplado no filtro "Todos" de Geração e no seletor de tipo do Histórico) — hoje sem nenhuma tela dedicada, nenhum campo específico de destino, e sem entrada a partir do inventário. Ou seja, a modelagem de dados de demanda (`reqs`) e o roteamento genérico já suportam esse tipo; falta a aba própria, os campos de destino/canal e a ação "Revogar" a partir de um certificado.

**Rationale**: Reaproveitar o tipo já reconhecido evita qualquer migração de dados de demandas existentes e mantém consistência com o resto do sistema (badges, filtros, templates de resposta já reconhecem `revogacao`).

**Alternatives considered**: Criar um novo tipo de entidade separado de `reqs` só para revogação — rejeitado; toda a infraestrutura de demanda (status, atividade, histórico, templates de resposta) já existe e se aplica igualmente bem a revogação, só falta os campos específicos.

## 2. Já existe um roteiro de revogação documentado — vira a base do fluxo formal

**Decision**: O roteiro já documentado em `app/routers/reqs.py` (`FLOWS["revogacao"]`, exibido como fluxograma de referência) — identificar motivo → localizar serial/thumbprint no inventário → solicitar revogação no destino certo → confirmar CRL/OCSP → remover dos sistemas → documentar — é a base direta do fluxo de demanda modelado aqui. A demanda formaliza esse processo, sem inventar um novo.

**Rationale**: Já é o processo mental que o usuário segue hoje manualmente; a feature só dá rastreamento a ele, mantendo a mesma linguagem/etapas já documentadas no próprio sistema.

## 3. Como modelar os 5 destinos de revogação — colunas dedicadas em `reqs`, não uma tabela nova

**Decision**: Duas colunas novas em `reqs`: `revoke_destination` (um de `internacional`, `serpro`, `ac_interna_nprd`, `ac_interna_prd`, `outros`) e `revoke_destination_other` (texto livre, só usado quando `revoke_destination='outros'`). Motivo/observações reaproveitam a coluna `notes` já existente em `reqs` — sem coluna nova para isso.

**Rationale**: Só existem 5 valores fixos, conhecidos e estáveis — uma tabela de "destinos" separada (com FK) adicionaria complexidade sem benefício real (não há atributos por destino além do nome e, por baixo, qual provider tratar). Consistente com o padrão já usado no projeto para conjuntos fixos pequenos (`ENVS`, `CERT_TYPES`, `INSTALL_LOCATIONS` — todos são listas Python/JS fixas, não tabelas).

**Alternatives considered**: Nova tabela `revocation_destinations` — rejeitada por excesso de estrutura pra 5 valores fixos sem atributos próprios. Reaproveitar `cert_category` (já existente em `certificates`) como destino de revogação — rejeitado; são conceitos diferentes (categoria de emissão do certificado vs. canal de revogação), com valores parcialmente sobrepostos mas não idênticos (`cert_category` não distingue AC Interna PRD de NPRD, por exemplo).

## 4. Vínculo entre a demanda de revogação e o certificado alvo

**Decision**: Nova coluna `reqs.revoke_cert_id INTEGER REFERENCES certificates(id) ON DELETE SET NULL`, preenchida quando a demanda é aberta a partir do inventário (US1). Quando aberta "do zero" pela aba de Revogação (US2/AC3), fica `NULL` — os dados do certificado (CN, serial, thumbprint, emissor) são só texto digitado, sem vínculo formal a uma linha de `certificates`.

**Rationale**: Mesma convenção já usada em `install_locations.cert_id` (referência nullable a um certificado específico). `certificates.req_id` já existe mas tem semântica diferente (aponta pra demanda que *gerou* o certificado) — reaproveitar geraria conflito/sobrescrita quando o mesmo certificado passa por geração e depois por revogação. Um campo próprio evita essa colisão.

## 5. Status da demanda de revogação — reaproveitar `REQ_STATUSES`, sem estados novos

**Decision**: Demandas de revogação usam os mesmos `REQ_STATUSES` já existentes (`aberta`, `concluida`, `cancelada`) — sem os estados intermediários específicos de geração (`csr_gerada`, `cert_emitido`, `instalado`, que não fazem sentido pra revogação). A confirmação de que a revogação foi efetivada (CRL/OCSP) é registrada como uma ação que marca a demanda como `concluida` (mesma mecânica de `PUT /reqs/{id}` já usada por todo tipo de demanda), sem exigir uma máquina de estados nova.

**Rationale**: `update_req` já aplica guardas de transição *condicionais ao `demand_type`* (ex.: `status='concluida'` exige certificado vinculado só pra `geracao`/`recebimento`/`renovacao` — `app/routers/reqs.py` linha ~317). Revogação simplesmente não entra nessa guarda condicional — pode ir de `aberta` direto pra `concluida` sem exigir certificado vinculado (já que muitas vezes é aberta a partir de um certificado que já existe, mas nem sempre — US2/AC3 permite abertura manual). Evita inflar `REQ_STATUSES` com valores que só uma minoria dos tipos de demanda usaria.

**Alternatives considered**: Estados dedicados (`solicitada`, `confirmada`, `concluida`) — rejeitado por ora; a spec pede rastreamento e confirmação manual, não uma esteira de aprovação formal. Se o processo real exigir mais granularidade depois, dá pra adicionar sem quebrar o que for construído agora (mesma lógica condicional por `demand_type` já em uso).

## 6. "Providers" de revogação — mesma arquitetura já usada pros providers de HSM, mas sem simulação real

**Decision**: Novo pacote `app/services/revocation/` com `base.py` (`RevocationProvider`, ABC com um único método `revoke(cn, serial, thumbprint, reason="") -> dict`, retorno no mesmo formato `{"ok": bool, "output": str, "code": str}` já usado pelos providers de HSM) e 5 implementações concretas — uma por destino (`internacional.py`, `serpro.py`, `ac_interna.py` com duas classes parametrizadas por ambiente NPRD/PRD, `outros.py`). Cada uma é uma implementação real e completa da interface (função existe, é chamada, tem lógica de log/auditoria), mas **sempre** retorna `{"ok": False, "code": "NOT_CONNECTED", "output": "Revogação automática via <destino> ainda não está conectada — confirme manualmente após revogar por fora do sistema."}` — nenhuma chamada de rede é feita.

**Rationale**: Atende literalmente ao pedido — "as funções devem ser implementadas" (a interface e as 5 classes existem, são chamadas de verdade a partir de uma ação real na demanda) e "não vamos conectar de fato" (o corpo de cada função é honesto sobre não ter conexão real, em vez de fingir sucesso). Diferente dos providers de HSM (onde dava pra simular criptografia de verdade com uma biblioteca local), aqui não existe uma "revogação simulada" que faça sentido — simular sucesso enganaria o usuário sobre o estado real de um certificado que continua válido. Por isso a estrutura fica pronta (endpoint, botão, provider por destino) mas o resultado é sempre "não conectado, confirme manualmente" — condizente com FR-008.

**Alternatives considered**: Não criar provider nenhum, só um campo de destino sem nenhuma "ação" associada — rejeitado; não atende ao pedido explícito de "implementar os providers" nem prepara a extensão futura (FR-009) tão claramente quanto ter a interface já presente e testável.

## 7. Onde a ação "Revogar" aparece a partir do inventário

**Decision**: Botão "🚫 Revogar" na barra de ações do modal `certDetail()` (`app/static/app.js`), ao lado de "📜 Histórico" — abre `newDemandModal('revogacao', {...dados do certificado}, onDone)`.

**Rationale**: `certDetail()` já é o ponto central de ações sobre um certificado do inventário (mudar lifecycle, mudar tipo, copiar PEM/thumbprint, ver histórico) — adicionar mais uma ação ali é consistente com o padrão existente, sem criar um novo ponto de entrada paralelo.

## 8. Lifecycle do certificado após revogação confirmada

**Decision**: Novo valor `revogado` em `LIFECYCLE_STATUSES` (`app/db.py`) e no mapa `LIFECYCLE_STATUS` (`app/static/app.js`). Ao marcar a demanda de revogação como `concluida` (com `revoke_cert_id` preenchido), `certificates.lifecycle_status` do certificado alvo é atualizado automaticamente pra `revogado`.

**Rationale**: `lifecycle_status` já é o campo que reflete "estado real" do certificado no inventário (`instalado`, `em_inventario`, `fim_de_vida`, etc.) — sem um valor de "revogado" explícito, um certificado revogado ficaria indistinguível de um certificado normal em qualquer listagem/filtro do inventário, o que contraria o objetivo da feature (SC-003).

## Resumo (Technical Context)

- Sem novas dependências — reaproveita FastAPI/pydantic (backend) e o JS vanilla já usado em `app.js` (frontend), consistente com specs/001-003.
- Migração de schema pequena e aditiva: 3 colunas novas em `reqs` (`revoke_destination`, `revoke_destination_other`, `revoke_cert_id`), 1 novo valor de enum em `LIFECYCLE_STATUSES`/`LIFECYCLE_STATUS` — sem tabela nova.
- Novo pacote de serviço `app/services/revocation/` (providers), mesmo padrão arquitetural de `app/services/hsm/`.
- Sem chamada de rede real em nenhum provider nesta fase (FR-008) — resultado sempre "não conectado", nunca um sucesso fingido.
