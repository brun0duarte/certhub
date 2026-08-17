# Quickstart: validar a hierarquia e clareza do Dashboard

## Pré-requisitos

- Branch com as mudanças de `plan.md`/`tasks.md` aplicadas.
- Banco local com: mais de 3 janelas de alerta configuradas em Configurações (ex. 15/30/60/90 dias) pra exercitar US1; vários certificados vencendo na mesma data pra US5; um certificado sem demanda ativa pra US6; certificados com pelo menos 3 status de lifecycle diferentes (incl. `reservado`, que tem o pior contraste hoje) pra US2; 3+ eventos consecutivos idênticos em `activity_log` (mesma ação, mesma REQ) pra US7; dados em `reqs_by_month`, `key_types` e `cert_health` simultaneamente pra US3; histórico de 3+ meses em `reqs_by_month` incluindo o mês corrente pra US8.

## Subir o app

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8477
# ou: python run.py
```

## Validar o backend (extensão de /dashboard)

```bash
curl -s http://127.0.0.1:8477/dashboard | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['next_expiring'][0].keys())"
```
Esperado: chaves incluindo `ownership`, `external_partner`, `partner_email`, `has_active_demand` além das já existentes.

## Validar o frontend (navegador)

1. Abrir `http://127.0.0.1:8477`, logar, ir pro Dashboard.
2. **US1 — severidade dos KPIs**: com 4 janelas de alerta configuradas, confirmar que a cor de cada card de "vencem em ≤N dias" corresponde à urgência (não à posição); "Vencidos" visualmente mais forte que os demais; cards de threshold >1º mostram o aviso de "cumulativo".
3. **US2 — contraste de badges**: no tema claro, abrir um certificado com status `reservado`/`instalado`/`em_inventario` — badge legível; confirmar que o rótulo "Excluir" não existe mais (virou "Baixado do inventário").
4. **US3 — grid sem buraco**: com os 3 conjuntos de análise disponíveis, confirmar que os 3 painéis ficam lado a lado numa grade de 3 colunas, sem espaço vazio.
5. **US4 — legenda de ambiente**: passar o mouse num badge de ambiente → tooltip com o nome completo; ver a legenda fixa abaixo do bloco "Demandas por ambiente e status".
6. **US5 — agrupamento por data**: confirmar que certificados vencendo na mesma data aparecem como 1 linha-resumo com contador, expansível ao clicar.
7. **US6 — ação rápida de renovação**: numa linha sem demanda ativa, clicar no ícone de renovação → `newDemandModal` abre pré-preenchido; confirmar que linhas com demanda ativa não mostram a ação.
8. **US7 — atividade recente compacta**: cada evento ocupa no máximo 2 linhas; eventos consecutivos idênticos aparecem agrupados com indicador "×N".
9. **US8 — média e mês atual no gráfico**: no gráfico "Demandas criadas por mês", confirmar a linha de referência de média e o destaque visual na barra do mês corrente.

## Regressão rápida

- `python3 -m py_compile app/routers/dashboard.py` e `node --check app/static/app.js` sem erro.
- `pytest -q` (ciente de 2 falhas de ambiente pré-existentes nesta máquina, não relacionadas: `python-multipart` e módulo `akamai` ausentes).
- Repetir os passos 2–9 no tema escuro além do claro.
