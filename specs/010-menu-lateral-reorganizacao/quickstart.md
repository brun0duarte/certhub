# Quickstart: validar a reorganização do menu lateral

## Pré-requisitos

- Branch `010-menu-lateral-reorganizacao` (ou a branch de implementação que aplica as mudanças descritas em `plan.md`/`tasks.md`) com as mudanças aplicadas.
- Banco local com pelo menos 1 demanda `demand_type='revogacao'` em status aberto e 1 tarefa fora da coluna "Concluído", pra exercitar os badges de contagem (US5).

## Subir o app

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8477
# ou: python run.py
```

## Validar o backend (endpoint novo)

```bash
curl -s http://127.0.0.1:8477/nav-counts | python3 -m json.tool
```
Esperado: JSON com `revogacao_pendente` e `kanban_pendente`, ambos inteiros ≥ 0, batendo com a contagem manual (`SELECT COUNT(*) FROM reqs WHERE demand_type='revogacao' AND status NOT IN ('concluida','cancelada')` etc. via `sqlite3`).

## Validar o frontend (navegador)

1. Abrir `http://127.0.0.1:8477`, logar.
2. **Agrupamento (US1)**: menu lateral mostra 4 cabeçalhos de grupo (Certificados, Ciclo de vida, Segurança, Sistema) acima dos itens correspondentes; Dashboard aparece isolado no topo, sem cabeçalho.
3. **Bloco fixo (US2)**: rolar a lista principal do menu (se necessário) — Aparência e Configurações NÃO estão nela; aparecem sempre visíveis logo acima do rodapé de usuário/sair/recolher, mesmo com o menu principal rolado.
4. **Rodapé sem botão de tema (US3)**: rodapé mostra só usuário, Sair e recolher — sem ícone de sol/lua. Ir em Aparência → card "Tema" → alternar Claro/Escuro → confirma que ainda funciona e persiste (recarregar a página, tema mantido).
5. **Rótulo sem quebra (US4)**: item de Manuais mostra "Manuais" numa linha só, mesma altura dos vizinhos, nos temas claro/escuro × accents padrão e "caixa".
6. **Badges de contagem (US5)**: com a demanda de revogação e a tarefa Kanban pendentes do pré-requisito, o item "Revogação" e o item "Kanban" mostram um número. Concluir a tarefa Kanban (mover pra "Concluído") e voltar ao menu (qualquer navegação) — o contador do Kanban deve cair ou sumir.
7. **Tooltip de recolher (US6)**: passar o mouse sobre o botão de recolher com o menu expandido → tooltip "Recolher menu"; clicar, passar o mouse de novo → tooltip "Expandir menu".
8. **Contraste CAIXA (US7)**: em Aparência, ativar accent "caixa". Olhar um item de menu inativo (não hover, não ativo) — texto/ícone devem estar claramente legíveis sobre o azul institucional sólido, nos dois temas (claro/escuro).

## Validar as 3 combinações de layout

Repetir os passos 2–4 acima nos 3 modos de "Posição do menu" (Lateral, Compacto, Horizontal) em Aparência — conferir que o bloco fixo (US2) e os cabeçalhos de grupo (ocultos no modo compacto, ver contrato `sidebar-dom-structure.md`) se comportam corretamente em cada um.

## Regressão rápida

- `node --check app/static/app.js` e `python3 -m py_compile app/routers/dashboard.py` sem erro.
- `pytest -q` (ciente de 2 falhas de ambiente pré-existentes nesta máquina, não relacionadas a esta feature: `python-multipart` e módulo `akamai` ausentes).
- Trocar de accent "caixa" pra "blue" (padrão) e voltar — ícones do `#nav` e de `.sidebar-secondary` devem reverter/trocar corretamente nos dois sentidos (contrato `sidebar-dom-structure.md`, invariante 2).
