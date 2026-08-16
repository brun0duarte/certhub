"""Revogação via AC Interna — duas instâncias (produção e não produção), hoje
operadas manualmente via acesso remoto + execução de script. specs/004-revogacao-certificados."""
from .base import RevocationProvider

_AMBIENTE_LABEL = {"nprd": "AC Interna NPRD", "prd": "AC Interna PRD"}


class AcInternaRevocationProvider(RevocationProvider):
    name = "ac_interna"

    def __init__(self, ambiente: str = "nprd"):
        self.ambiente = ambiente if ambiente in _AMBIENTE_LABEL else "nprd"
        self.label = _AMBIENTE_LABEL[self.ambiente]

    def revoke(self, cn: str, serial: str = "", thumbprint: str = "", reason: str = "") -> dict:
        if not cn.strip():
            return {"ok": False, "code": "INVALID_INPUT", "output": "Informe o CN do certificado."}
        return self._not_connected()
