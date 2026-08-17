# Data Model: Ajustes de Layout do HSM e Preservação de Estado entre Abas

Nenhuma tabela SQL nova ou alterada. Duas estruturas de dados envolvidas: uma extensão pequena da resposta de um endpoint já existente (US2), e uma estrutura nova que vive só no frontend, em memória (US3).

## Perfil de HSM — resposta de `GET /hsm/profiles` (US2)

Já existe como setting `hsm_dinamo_profiles` (specs/002). Sem mudança de armazenamento — só a resposta do endpoint `GET /hsm/profiles` ganha 2 campos por item da lista:

| Campo | Tipo | Mudança | Notas |
|---|---|---|---|
| `name` | string | já existente | identificador do perfil |
| `host` | string | **novo** | não é segredo — ok expor no frontend |
| `username` | string | **novo** | não é segredo — ok expor no frontend |
| `password` | — | continua **nunca** exposto | omitido por padrão, sem mudança |

## Estado de view (US3) — só em memória do frontend, não persistido

Objeto `viewState` no escopo do módulo `app.js` (nunca serializado, nunca enviado ao backend, nunca gravado em `localStorage`/`sessionStorage`). Chave = nome da view (mesmo valor usado em `location.hash`, ex. `"geracao"`, `"hsm"`); valor = objeto livre com os campos relevantes daquela view.

**Views com filtro/busca/paginação preservados** (leem/gravam `page`, `search`, e os filtros próprios da tela):

| View | Campos preservados |
|---|---|
| `geracao` | `search`, `env`, `status`, `type` (demand_type), `sortKey`, `sortDir`, `page` |
| `instalacao` | `search`, `env`, `status`, `sortKey`, `sortDir`, `page` |
| `historico` | `search`, `env`, `status`, `type`, `page` |
| `monitor` | `search`, `days`, `ownership`, `pendingOnly`, `sortKey`, `sortDir`, `page` |
| `auditoria` | filtros já existentes da tela (usuário/ação/busca) + `page`, conforme campos atuais de `views.auditoria` |
| `certs` | filtro/busca já existente da tela + `page`, conforme campos atuais de `views.certs` |

**Views com formulário de múltiplos campos preservado** (campos de entrada ainda não enviados — resultado da última ação, se houver, NÃO é preservado, conforme FR-011):

| View | Campos preservados |
|---|---|
| `csr` | engine, demanda vinculada, CN, SANs, campos do Subject DN (O/OU/C/ST/L/E), tipo de chave, label HSM |
| `hsm` | campos dos 4 formulários da aba (criar chave, importar certificado, gerar CSR, exportar) — rótulo, tipo, CN, SANs, subject DN, formato |
| `decoder` | conteúdo colado/arquivo selecionado ainda não decodificado (campo de texto PEM; arquivo em si não é restaurável via JS por limitação do navegador — ver Edge Cases) |
| `settings` | todos os campos do formulário (pastas, alertas, política de senha, templates, perfis de HSM em edição) — inclui campos de senha, mantidos só em memória (FR-007) |

**Regras de validação**:
- Ao montar uma view, se existir estado salvo para aquele nome, os campos de formulário/filtro MUST ser inicializados com os valores salvos (em vez do valor vazio/padrão).
- Toda mudança de valor num campo coberto (input/select/textarea) MUST atualizar o objeto de estado daquela view imediatamente (mesmo evento que já dispara busca/filtragem, sem debounce adicional além do que já existe pra busca por texto).
- Campos de arquivo (`<input type="file">`) MUST NOT ter o arquivo em si preservado — não é possível reatribuir um `FileList` via JavaScript por restrição de segurança do navegador; apenas os demais campos do mesmo formulário são preservados (edge case documentado no spec).
- Resultado de uma ação já concluída (ex.: `#h-csr-result`, `#dc-result`, `#c-result`) MUST NOT ser restaurado — só os campos de entrada do formulário.
- Ao restaurar `page` de uma lista, a busca ao servidor MUST ocorrer normalmente (dados sempre atuais); se `page` salvo exceder o novo total de páginas, MUST cair pra última página válida (FR-009).
