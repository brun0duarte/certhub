# Contract: Componente de seleção de demanda com busca (US1)

Contrato interno de UI — não é uma API de rede, mas define a interface reutilizada nos 5 pontos onde hoje existe um `<select>` de REQs (geração de CSR, decoder, CSR via HSM, referência de credencial de instalação, avanço para instalação), para garantir comportamento idêntico nos 5 lugares (FR-003).

## Interface

```
reqPicker(container: HTMLElement, reqs: Array<{id, req_number, cn, env}>, options?: {
  placeholder?: string,   // default: "Buscar REQ ou CN…"
  selectedId?: number,    // pré-seleciona uma demanda existente
  allowEmpty?: boolean,   // default: true — permite "— nenhuma —"
}) -> { getValue(): number | null }
```

## Comportamento

- Renderiza um `input.input` de texto + lista de sugestões (`req_number · cn (env)`) filtrada por substring (case-insensitive) em `req_number` OU `cn`, atualizada a cada tecla (FR-002).
- Lista de sugestões vazia após filtrar → exibe "Nenhuma demanda encontrada" na lista (não esconde o campo, não parece erro) — cobre o edge case de US1.
- Selecionar um item da lista preenche o texto exibido e fixa `getValue()` para aquele `id`; texto exibido sem correspondência exata a uma sugestão selecionada → `getValue()` retorna `null` (equivalente a "nenhuma selecionada" no `<select>` atual), evitando salvar um `req_id` que não corresponde ao texto visível.
- `options.allowEmpty` mantém o comportamento de "— nenhuma —" já presente nas telas onde a vinculação é opcional.
- Sem `reqs` correspondendo a nada digitado com o campo vazio (foco inicial) → lista mostra todas as `reqs` recebidas, replicando o `<select>` atual (edge case "campo vazio" do FR-002/Acceptance Scenario 4 de US1).

## Pontos de substituição (mesmo dado de entrada em todos, `GET /reqs` já carregado na tela)

| Tela | Uso atual (linha aproximada em `app.js`) |
|---|---|
| Gerar CSR | `#c-req` (L.1854-1855) |
| Decoder | `#dc-req` (L.2089) |
| CSR via HSM | `#h-csr-req` (L.2523) |
| Referência de credencial (local de instalação) | `data-loc-credref` (L.1276) |
| Avançar para instalação | seletor de REQ no modal (L.2396) |
