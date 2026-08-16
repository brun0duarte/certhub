"""Revogação via Serpro (ICP-Brasil) — specs/004-revogacao-certificados."""
from .base import RevocationProvider


class SerproRevocationProvider(RevocationProvider):
    name = "serpro"
    label = "Serpro"

    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        if not cn.strip():
            return {"ok": False, "code": "INVALID_INPUT", "output": "Informe o CN do certificado."}
        return self._not_connected()
