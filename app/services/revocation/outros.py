"""Revogação via destino não catalogado (descrito em texto livre pelo usuário
na demanda). specs/004-revogacao-certificados."""
from .base import RevocationProvider


class OutrosRevocationProvider(RevocationProvider):
    name = "outros"
    label = "destino informado"

    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        if not cn.strip():
            return {"ok": False, "code": "INVALID_INPUT", "output": "Informe o CN do certificado."}
        return self._not_connected()
