# Quickstart: Demandas de Revogação de Certificados

Guia de validação manual das 3 user stories. Assume app rodando localmente com usuário autenticado e ao menos um certificado já cadastrado no inventário (Certificados).

## US1 — Abrir demanda de revogação a partir do inventário

1. Acesse **Certificados**, abra o detalhe de um certificado qualquer.
2. Acione **"🚫 Revogar"**.
3. **Esperado**: abre o formulário de nova demanda com tipo "Revogação" travado, CN/serial/thumbprint/emissor já preenchidos a partir do certificado.
4. Escolha um destino (ex.: "Serpro") e confirme.
5. **Esperado**: demanda criada, aparece na aba **Revogação** (US2) com o destino escolhido visível.
6. Repita o passo 2-4 pro mesmo certificado, sem concluir a primeira demanda.
7. **Esperado**: aviso de que já existe uma demanda de revogação em aberto pra esse certificado, com opção de confirmar mesmo assim (`contracts/reqs-revoke-api.md`, duplicidade não bloqueante).

## US2 — Acompanhar na aba Revogação

1. Acesse a nova aba **Revogação**.
2. **Esperado**: só demandas `demand_type='revogacao'` aparecem, com busca, filtro (ambiente/status/destino) e ordenação funcionando — mesmo padrão de Geração/Instalação.
3. Acione **"+ Nova demanda"** na própria aba.
4. **Esperado**: consegue abrir uma demanda de revogação preenchendo CN manualmente, sem vir de um certificado do inventário (`revoke_cert_id` fica nulo).
5. Abra o detalhe de uma demanda de revogação e avance o status até "Concluída".
6. **Esperado**: se a demanda tinha um certificado vinculado (veio do inventário), o `lifecycle_status` desse certificado passa a "Revogado" — confira em Certificados.

## US3 — Destino/canal e provider (sem conexão real)

1. Numa demanda de revogação em aberto, acione a ação de solicitar a revogação (botão que chama `POST /reqs/{id}/revoke`).
2. **Esperado**: resposta clara indicando que a revogação automática pra aquele destino ainda não está conectada, pedindo confirmação manual — nunca um "sucesso" fingido (`contracts/revocation-provider.md`).
3. Repita com os 5 destinos diferentes (Internacional, Serpro, AC Interna NPRD, AC Interna PRD, Outros).
4. **Esperado**: cada um responde com a mesma estrutura, mencionando o nome do próprio destino na mensagem — confirma que os 5 providers estão de fato implementados e sendo chamados (não é um único stub genérico disfarçado).
5. Escolha destino "Outros" ao criar uma demanda sem descrever o destino no campo de texto livre.
6. **Esperado**: erro `400` pedindo a descrição (`contracts/reqs-revoke-api.md`).

## Testes automatizados de referência

- Novo `tests/test_revocation_providers.py`: um teste por provider confirmando `ok: False`, `code: "NOT_CONNECTED"`, e que nenhuma chamada de rede/subprocess é feita (sem necessidade de mock, já que não há I/O externo real).
- Extensão de `tests/test_reqs_lifecycle.py`: validação de `revoke_destination` obrigatório, `revoke_destination_other` obrigatório quando `outros`, aviso não-bloqueante de duplicidade, e atualização de `certificates.lifecycle_status` para `revogado` ao concluir uma demanda com `revoke_cert_id`.
