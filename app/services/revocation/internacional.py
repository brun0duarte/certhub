"""Revogação via CA internacional (ex.: Sectigo) — specs/004-revogacao-certificados."""
from .base import RevocationProvider


class InternacionalRevocationProvider(RevocationProvider):
    name = "internacional"
    label = "CA Internacional"

    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        if not cn.strip():
            return {"ok": False, "code": "INVALID_INPUT", "output": "Informe o CN do certificado."}
        return self._not_connected()
