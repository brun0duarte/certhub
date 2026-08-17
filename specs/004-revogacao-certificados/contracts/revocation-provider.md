# Contract: `RevocationProvider` (app/services/revocation/)

Interface interna, mesmo espírito de `app/services/hsm/base.py::KeyProvider` — não é uma API de rede, é o contrato que toda implementação de destino de revogação segue, garantindo que `POST /reqs/{id}/revoke` (`contracts/reqs-revoke-api.md`) não precise saber qual destino está por trás.

## Interface

```python
class RevocationProvider(ABC):
    name: str = "base"

    @abstractmethod
    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        """Solicita a revogação. Retorna {'ok': bool, 'code': str, 'output': str}."""
```

## Implementações (uma por destino, `app/services/revocation/`)

| Arquivo | Classe | `revoke_destination` correspondente |
|---|---|---|
| `internacional.py` | `InternacionalRevocationProvider` | `internacional` |
| `serpro.py` | `SerproRevocationProvider` | `serpro` |
| `ac_interna.py` | `AcInternaRevocationProvider(ambiente="nprd")` | `ac_interna_nprd` |
| `ac_interna.py` | `AcInternaRevocationProvider(ambiente="prd")` | `ac_interna_prd` |
| `outros.py` | `OutrosRevocationProvider` | `outros` |

**Resolução do provider** (`app/routers/reqs.py`, usado por `POST /reqs/{id}/revoke`):

```python
_PROVIDERS = {
    "internacional": lambda: InternacionalRevocationProvider(),
    "serpro": lambda: SerproRevocationProvider(),
    "ac_interna_nprd": lambda: AcInternaRevocationProvider(ambiente="nprd"),
    "ac_interna_prd": lambda: AcInternaRevocationProvider(ambiente="prd"),
    "outros": lambda: OutrosRevocationProvider(),
}
```

## Comportamento nesta fase (FR-008)

Toda implementação MUST:
- Não abrir nenhuma conexão de rede, subprocess, ou qualquer I/O externo.
- Retornar sempre `{"ok": False, "code": "NOT_CONNECTED", "output": "Revogação automática via {label do destino} ainda não está conectada — confirme manualmente após revogar por fora do sistema."}`.
- Ainda assim executar sua lógica própria de validação de entrada (ex.: `serial`/`thumbprint` vazios) e logging — a função é real e testável, só o passo de conexão externa é que não existe ainda (research.md #6).

## Extensão futura (FR-009)

Quando um destino ganhar execução automatizada real, só a implementação daquele destino muda (o `revoke()` passa a tentar a conexão real e retornar `ok: true`/`false` conforme o resultado real) — a interface, a resolução por `revoke_destination`, o endpoint `POST /reqs/{id}/revoke` e a UI que o consome permanecem os mesmos.
