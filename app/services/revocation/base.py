"""Interface comum dos providers de revogação (um por destino/canal).

Mesmo espírito de app/services/hsm/base.py::KeyProvider — nesta fase nenhuma
implementação faz conexão de rede real (specs/004-revogacao-certificados,
FR-008); cada revoke() é uma função de verdade, só o passo de conexão externa
é que ainda não existe.
"""
from abc import ABC, abstractmethod

NOT_CONNECTED_MESSAGE = (
    "Revogação automática via {label} ainda não está conectada — "
    "confirme manualmente após revogar por fora do sistema."
)


class RevocationProvider(ABC):
    name: str = "base"
    label: str = "destino desconhecido"

    @abstractmethod
    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        """Solicita a revogação. Retorna {'ok': bool, 'code': str, 'output': str}."""

    def _not_connected(self) -> dict:
        return {"ok": False, "code": "NOT_CONNECTED", "output": NOT_CONNECTED_MESSAGE.format(label=self.label)}
