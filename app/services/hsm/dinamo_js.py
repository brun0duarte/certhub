"""Provider Dinamo Networks via SDK JavaScript oficial (v2 — ainda não implementado).

Plano: um helper Node.js (`hsm-helper.js`) usando o SDK JS da Dinamo
(https://docs.dinamonetworks.io/hsm/api/), chamado pelo backend:
    node hsm-helper.js gen-csr --label X --cn Y --sans a,b
"""
from .base import KeyProvider

_MSG = ("Integração com o SDK JavaScript da Dinamo ainda não implementada. "
        "Use o provider 'hsmutil' (Configurações > HSM) por enquanto.")


class DinamoJsProvider(KeyProvider):
    name = "dinamo_js"

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        return {"ok": False, "output": _MSG}

    def gen_csr(self, label, cn, sans=None, key_type="rsa2048", **kwargs):
        return {"ok": False, "output": _MSG}

    def export_key(self, label, out_path, **kwargs):
        return {"ok": False, "output": _MSG}
