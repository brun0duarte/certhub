# Research: Integração com HSM via API (Dinamo Networks)

## 1. Como integrar com o HSM Dinamo a partir do backend Python

**Decision**: usar o SDK oficial JavaScript da Dinamo (`@dinamonetworks/hsm-dinamo`) por trás de um script Node.js dedicado (`app/services/hsm/node/hsm-helper.js`), invocado pelo backend Python via subprocess com protocolo JSON em stdin/stdout (uma chamada de processo por operação). O provider `DinamoJsProvider` (`app/services/hsm/dinamo_js.py`) implementa a interface `KeyProvider` já existente e traduz para/desse protocolo.

**Rationale**:
- A documentação da Dinamo (https://docs.dinamonetworks.io/hsm/api/) não expõe uma API REST/HTTP pública — os "clientes" oficiais são bibliotecas nativas: C/C++, Java, .NET e JavaScript.
- O projeto já havia planejado exatamente essa abordagem: o stub existente em `app/services/hsm/dinamo_js.py` já documenta "um helper Node.js (`hsm-helper.js`) usando o SDK JS da Dinamo, chamado pelo backend".
- O ambiente já possui Node.js disponível (`node v25.8.1` no ambiente de desenvolvimento), então o custo de introduzir esse bridge é baixo.
- Manter o contrato `KeyProvider` (`gen_key`, `gen_csr`, `export_key`, mais os métodos novos desta feature) preserva a troca de engine já existente na tela de Configurações (local / hsmutil / dinamo_js) sem mudar o restante do sistema.

**Alternatives considered**:
- *Reimplementar em Python puro o protocolo binário do HSM*: rejeitado — não é um protocolo documentado publicamente, alto risco e esforço fora de escopo.
- *Expor um microserviço Node HTTP separado*: rejeitado por adicionar mais um processo de longa duração para operar/monitorar, quando um subprocess por chamada (curta duração, poucas operações administrativas) é suficiente para o volume de uso (SC-001..SC-005 falam de segundos, não de alta frequência).
- *CLI `hsmutil` (já existente como provider)*: continua disponível como alternativa mais simples, mas não cobre nativamente importação de certificado, exportação PFX/P12 nem busca — manteria templates de shell arbitrários e mais dificuldade de tratar dados binários (PFX) e senhas com segurança.

## 2. Autenticação e escopo (resolvido na especificação)

**Decision**: autenticação via host + usuário/senha de partição (`authUsernamePassword`), como confirmado nos exemplos oficiais (`Exemplos.Conectando-se_ao_HSM`). A conexão já é escopada pela partição do usuário autenticado — a listagem de objetos (`conn.management.listObjs()`, conforme `Exemplos.Listando_objetos_em_uma_partição_do_HSM`) naturalmente retorna apenas os objetos dessa partição, sem necessidade de filtro adicional de escopo no código da aplicação.

**Rationale**: elimina a necessidade de mTLS ou de um modelo de token de API não documentado publicamente; reaproveita o mesmo padrão de credenciais (host/usuário/senha) já usado em outras integrações do sistema (ex.: templates do provider `hsmutil`).

**Alternatives considered**: mTLS e token de API foram considerados na fase de especificação (`spec.md`, FR-013) e descartados por não haver evidência de suporte na documentação oficial consultada.

## 3. Onde guardar as credenciais/configuração de conexão

**Decision**: nova entrada em `DEFAULT_SETTINGS` (`app/db.py`), seguindo o padrão já usado por `hsmutil_templates` — um valor JSON `hsm_dinamo_config` com `{host, port, username, password}`, editável na aba Configurações já existente. A senha de conexão é armazenada como as demais credenciais sensíveis do sistema (mesmo tratamento hoje dado a `password` em `reqs` e a senhas geradas pelo módulo de senhas).

**Rationale**: consistente com o mecanismo de configuração já usado por `hsmutil_templates`; evita introduzir um novo sistema de configuração paralelo.

**Alternatives considered**: variáveis de ambiente (`HSM_HOST`, `HSM_USERNAME`, `HSM_PASSWORD`, suportadas nativamente pelo SDK) — mantidas como *fallback* documentado para ambientes que preferem não guardar credencial no banco, mas não como mecanismo primário, para não fugir do padrão de configuração via UI já estabelecido no projeto.

## 4. Exportação PFX/P12 e política de senha (resolvido na especificação)

**Decision**: a senha do arquivo PFX/P12 exportado é gerada/gerenciada pelo módulo de senhas já existente (`app/services/passwordgen.py` + `password_policy` em `settings`), não digitada manualmente pelo usuário nem exibida uma única vez de forma ad-hoc.

**Rationale**: reaproveita política e força de senha já auditada no projeto; evita duplicar lógica de geração de senha.

## 5. Persistência local de certificados importados/exportados

**Decision**: reaproveitar a tabela `certificates` já existente (`app/db.py`), adicionando uma coluna `hsm_label` (nullable) para vincular um registro de certificado ao rótulo da chave no HSM, e usando `source='hsm'` para diferenciar de certificados apenas importados por upload manual. Não é criada uma tabela nova de "chaves HSM" — o HSM permanece a fonte da verdade para chaves e associação chave↔certificado; a busca (`/hsm/search`) consulta o HSM ao vivo via `listObjs()`, não uma cópia local.

**Rationale**: minimiza duplicação de estado entre o HSM e o banco local (risco de dessincronização); segue o padrão já usado pelo repositório de CSRs (`csrs`), que guarda o resultado mas não é fonte da verdade de nada externo.

**Alternatives considered**: tabela dedicada `hsm_keys` espelhando todo o inventário do HSM — rejeitada nesta fase por criar um segundo lugar de verdade a manter sincronizado, sem necessidade demonstrada pelos requisitos (FR-009 pede busca funcional, não um cache local).

## 6. Testes sem depender de HSM real

**Decision**: os testes do `DinamoJsProvider` usam um *fake* do bridge Node (função injetável que substitui a chamada de subprocess, retornando payloads JSON de exemplo), seguindo o mesmo espírito dos testes já existentes em `tests/test_reqs_lifecycle.py` (que testam via `TestClient` do FastAPI sem infraestrutura externa real).

**Rationale**: viabiliza CI sem exigir acesso a um HSM Dinamo real; a interface `KeyProvider` já foi desenhada para ser substituível (prova disso é o próprio `LocalProvider`).

## 7. API real do SDK (confirmado após `npm install`, lendo `node_modules/@dinamonetworks/hsm-dinamo/dist/**/*.d.ts` — v4.27.0)

Os nomes de método usados nas seções anteriores eram provisórios até a instalação do pacote real. Depois de instalado, os `.d.ts` do pacote (com JSDoc completo) confirmaram a API efetiva, bem diferente do que um nome "óbvio" sugeriria:

- **Criar chave**: `conn.key.create(name, algorithm, exportable, temporary, blockchain): Promise<boolean>`, com `algorithm` vindo de `hsm.enums.RSA_ASYMMETRIC_KEYS.ALG_RSA_2048/ALG_RSA_4096`. Chaves são criadas sempre com `exportable=true` pelo `dinamo_js` (é a própria aplicação quem cria a chave, então a exportação via PFX precisa estar disponível; `NOT_EXPORTABLE` só se aplica a chaves pré-existentes no HSM criadas fora da aplicação).
- **Gerar CSR**: `conn.key.generatePKCS10(keyName, dn, hashAlgorithm?): Promise<Buffer>` (CSR em **DER**, convertido pra PEM no bridge). `dn` é um objeto `{CN, O, OU: string[], L, ST, C, E}` — **não existe parâmetro de SAN** nessa API; `generatePKCS10` só assina o Distinguished Name. SANs enviados pela aplicação são aceitos na entrada (compatibilidade com o contrato) mas **não chegam a entrar na CSR** — limitação do SDK, não do bridge. Documentado no topo de `hsm-helper.js`.
- **Importar certificado**: `conn.key.importCertificate(name, certData: Buffer): Promise<boolean>`. **Descoberta importante**: essa chamada não valida em nenhum momento que o certificado corresponde à chave `name` — é só um upload de blob. A validação de FR-006 (chave pública do certificado = chave pública da entrada no HSM) não é feita pelo HSM nessa API; por isso o bridge faz essa checagem ele mesmo (`conn.key.exportAsymmetricPub(label, true)` comparado byte a byte com a SPKI extraída do certificado via `node-forge`) antes de chamar `importCertificate`.
- **Exportar PFX/P12**: **não existe** `exportPFX`/`exportPKCS12` nessa versão do SDK (só existe `importPKCS12`, para o sentido contrário). O bridge monta o PKCS#12 no lado Node, combinando `conn.key.exportPKCS8(label, password)` (chave privada, já protegida pela senha) + `conn.key.exportCertClearText(certName)` (certificado em claro), decodificando com `node-forge` (`forge.pki.decryptPrivateKeyInfo` + `forge.pkcs12.toPkcs12Asn1`) e devolvendo o PKCS#12 resultante. `node-forge` foi adicionado como dependência do bridge (`package.json`).
- **Nome do certificado**: o SDK trata chave e certificado como objetos independentes, cada um com seu próprio nome — não existe "associar certificado a uma chave" como conceito nativo. O bridge usa a convenção `${label}.cert` para o nome do certificado, e considera "chave com certificado associado" quando esse nome também existe no HSM (usado tanto em `import-cert` quanto em `search`).
- **Buscar/listar**: `conn.management.listObjs(): Promise<string[]>` retorna só os **nomes** dos objetos (não objetos ricos com metadados). Para montar o resultado de busca, o bridge chama `conn.management.getObjectInfo(name)` (retorna `{type, version, attributes}`, sem CN/validade) e, quando existe `${name}.cert`, exporta e faz parse do certificado (`node-forge`) pra extrair `cn`/`not_after`. Isso é uma chamada adicional por objeto correspondente à busca — aceitável para o volume esperado (SC-005: até 10 mil objetos, mas o filtro por `query` é aplicado antes de buscar detalhes, então só objetos que já batem com o termo buscado pagam esse custo extra).
- **Erros**: `HsmError` (lançado pelo SDK) expõe `.errorCode` numérico do firmware. Mapeados no bridge: `5022 ERR_OBJ_ALREADY_EXISTS`→`ALREADY_EXISTS`, `5004 ERR_CANNOT_OPEN_OBJ`/`5023 ERR_INVALID_OBJ_NAME`→`NOT_FOUND`, `5002 ERR_ACCESS_DENIED`→`NOT_EXPORTABLE` (só na exportação) ou erro genérico, `5001 ERR_NET_FAIL`→`CONN_FAILED`. Não existe um código de firmware específico para "chave pública não confere" — esse caso é sempre gerado pelo próprio bridge (ver importação de certificado acima), nunca pelo HSM.
- **Módulo ESM**: o pacote é `"type": "module"` (só ESM, sem CJS). O `hsm-helper.js` e seu `package.json` foram ajustados para `"type": "module"` também, evitando qualquer interop CJS/ESM.

Validado localmente: `node hsm-helper.js gen-key` com HSM inexistente retorna `{"ok": false, "code": "CONN_FAILED", ...}` corretamente (round-trip completo do protocolo, só faltando um HSM real pra validar as operações de fato — ver `quickstart.md`).

## Itens que ainda dependem de um HSM real para validação final

- Formato exato de retorno de `exportPKCS8`/`exportCertClearText` (assumido DER a partir da leitura do código-fonte do SDK, mas nunca observado contra hardware real).
- Se o firmware realmente não valida correspondência chave↔certificado em `importCertificate` como o código-fonte sugere (a checagem do bridge cobre esse caso de qualquer forma, então uma validação nativa adicional do HSM seria redundante, não um problema).
- Nomes de campo retornados por `getObjectInfo` para tipos de chave fora de RSA (ex.: EC), caso a aplicação passe a suportar mais tipos de chave no futuro (fora do escopo desta feature — ver `Assumptions` em `spec.md`).
