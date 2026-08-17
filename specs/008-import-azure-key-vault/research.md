# Research: Importação Completa pro Azure Key Vault

Sem `[NEEDS CLARIFICATION]` no Technical Context — Technical Context inteiro resolvido direto (mesma stack e mesmo padrão já usados por `AzureKeyVaultProvider`/`AzionProvider` em specs/005). Pesquisa registrada abaixo é sobre decisões concretas de formato de requisição/resposta, validadas contra uma chamada real feita manualmente à API do Key Vault (`vpn.bancofic.com.br`, `kv-certhub`).

## 1. Bloco `policy` na requisição de importação

**Decision**: Adicionar ao corpo da requisição:
```json
"policy": {
  "key_props": {"exportable": true, "kty": "RSA", "key_size": 2048, "reuse_key": false},
  "secret_props": {"contentType": "application/x-pkcs12"}
}
```
como um dicionário fixo no código (não vindo de `config` nem de setting).

**Rationale**: É exatamente o bloco usado na chamada manual que teve sucesso confirmado contra `kv-certhub.vault.azure.net` (resposta 200 com `policy.key_props`/`secret_props` ecoados de volta). `key_size: 2048` bate com toda chave hoje gerada pelo fluxo HSM da REQ (`_resolve_key_material`, providers.py:85) — não há caminho no sistema hoje que gere chave de tamanho diferente pra esse provider. `reuse_key: false` é o padrão correto porque cada importação desta feature monta um PFX novo (`pkcs12.serialize_key_and_certificates`, providers.py:176) a partir da chave já resolvida — não há reaproveitamento de chave já existente no vault a preservar.

**Alternatives considered**:
- *Deixar sem `policy` (comportamento atual)*: Key Vault aplica uma política padrão inferida do PFX — funciona, mas não é o comportamento validado/desejado pelo usuário (risco de o Key Vault não marcar a chave como exportável, por exemplo, o que impediria reexportar o certificado depois). Rejeitado — é exatamente o gap que a User Story 2 pede pra fechar.
- *Tornar `policy` configurável por local (novo campo em `config_fields`)*: mais flexível, mas nenhum outro provider de nuvem (Azion, AWS) expõe política de chave como campo de formulário hoje, e o spec (Assumptions) já fixa isso como não-configurável nesta etapa. Rejeitado por escopo.

## 2. Extrair validade e thumbprint da resposta

**Decision**: Ler direto os campos já prontos da resposta — sem decodificar o certificado (`cer`):
- `attributes.nbf` e `attributes.exp` — inteiros epoch (segundos UTC) → formatar com `datetime.fromtimestamp(..., tz=timezone.utc)`.
- `x5t` — já é o thumbprint (SHA-1, base64url) pronto pra exibir.
- `id` — pegar o último segmento do path (`.rsplit("/", 1)[-1]`) como identificador de versão.

**Rationale**: Todos os 3 campos vêm prontos no JSON de resposta (confirmado na resposta real capturada), sem precisar abrir o `cer` (DER base64) com `cryptography.x509` — menos código, menos ponto de falha no parsing. `AzionProvider.install()` (providers.py:298-308) já estabelece o padrão do projeto: `try/except (ValueError, KeyError)` em volta do parsing, com fallback pra mensagem genérica em caso de formato inesperado (FR-004) — mesmo padrão será reaplicado aqui.

**Alternatives considered**:
- *Decodificar `cer` com `cryptography.x509.load_der_x509_certificate`*: dado redundante (mesma validade já está em `attributes`) e mais código/mais forma de falhar (base64 inválido, DER malformado). Rejeitado — sem ganho sobre usar `attributes`.
- *Chamar de volta o Key Vault (`GET` no `id`) pra confirmar o certificado*: desnecessário, a resposta do próprio `import` já é completa (não é um 202/Accepted assíncrono). Rejeitado.

## 3. Formato da mensagem de sucesso

**Decision**: Uma linha só, mesmo estilo textual do `AzionProvider`:
`"Certificado importado no Key Vault '{vault}' como '{cert_name}' (versão {version}) — válido até {exp} · thumbprint {x5t}."`

**Rationale**: Consistência com o texto já exibido hoje pra Azion (`output` é texto livre em `install_runs.output`, sem schema estruturado pra UI parsear) — reaproveita o mesmo padrão de "uma frase densa com os campos relevantes separados por `·`" já usado em providers.py:303-305.

**Alternatives considered**: JSON estruturado no campo `output` — rejeitado, quebraria o contrato implícito hoje (toda a UI/histórico assume texto livre pra esse campo; mudar o tipo seria uma alteração de escopo maior, fora do pedido desta feature).
