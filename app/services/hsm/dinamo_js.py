"""Provider Dinamo Networks via SDK JavaScript oficial.

Não existe API REST pública documentada pela Dinamo — o SDK oficial é nativo
(C/C++, Java, .NET, JavaScript). A integração roda o SDK JS por trás de um
bridge Node.js (`node/hsm-helper.js`), chamado via subprocess, um processo por
operação, protocolo JSON em stdin/stdout — ver
specs/001-integracao-hsm-dinamo/contracts/hsm-node-bridge.md.
"""
import base64
import json
import subprocess
from pathlib import Path

from .base import ERROR_MESSAGES as _ERROR_MESSAGES
from .base import ERROR_STATUS as _ERROR_STATUS
from .base import KeyProvider

_HELPER_SCRIPT = Path(__file__).resolve().parent / "node" / "hsm-helper.js"


class DinamoJsProvider(KeyProvider):
    name = "dinamo_js"

    def __init__(self, connection: dict):
        self.connection = connection or {}

    def _call(self, action: str, params: dict, timeout: int = 30) -> dict:
        request = json.dumps({"connection": self.connection, "params": params})
        try:
            proc = subprocess.run(
                ["node", str(_HELPER_SCRIPT), action],
                input=request, capture_output=True, text=True, timeout=timeout,
            )
        except FileNotFoundError:
            return self._error("CONN_FAILED", "Node.js não encontrado no servidor da aplicação.")
        except subprocess.TimeoutExpired:
            return self._error("TIMEOUT")

        try:
            result = json.loads(proc.stdout)
        except (json.JSONDecodeError, ValueError):
            detail = (proc.stdout + "\n" + proc.stderr).strip()
            return self._error("CONN_FAILED", detail or "Resposta inválida do bridge HSM.")

        if not result.get("ok"):
            return self._error(result.get("code"), result.get("error"))
        return {"ok": True, "data": result.get("data", {})}

    def _error(self, code: str, message: str | None = None) -> dict:
        code = code if code in _ERROR_STATUS else "CONN_FAILED"
        return {"ok": False, "code": code, "http_status": _ERROR_STATUS[code],
                "output": message or _ERROR_MESSAGES[code]}

    # ---- contrato KeyProvider ----

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        result = self._call("gen-key", {"label": label, "key_type": key_type})
        if not result["ok"]:
            return result
        return {"ok": True, "output": f"Chave {key_type} criada no HSM.", **result["data"]}

    def gen_csr(self, label, cn, sans=None, key_type="rsa2048", **kwargs):
        params = {
            "label": label, "cn": cn, "sans": sans or [],
            "org": kwargs.get("org", ""), "ou": kwargs.get("ou", ""),
            "country": kwargs.get("country", ""), "state": kwargs.get("state", ""),
            "locality": kwargs.get("locality", ""), "email": kwargs.get("email", ""),
        }
        result = self._call("gen-csr", params)
        if not result["ok"]:
            return result
        return {"ok": True, "output": "CSR gerada no HSM.", **result["data"]}

    def export_key(self, label, out_path, **kwargs):
        return {"ok": False, "output": "Chaves do HSM só são exportáveis via PFX/P12 "
                                        "(use a exportação em /hsm/keys/{label}/export)."}

    # ---- operações específicas de HSM (fora do contrato KeyProvider genérico) ----

    def import_cert(self, label: str, cert_pem: str) -> dict:
        result = self._call("import-cert", {"label": label, "cert_pem": cert_pem})
        if not result["ok"]:
            return result
        return {"ok": True, "output": "Certificado importado e associado à chave no HSM.", **result["data"]}

    def export_pfx(self, label: str, password: str) -> dict:
        result = self._call("export-pfx", {"label": label, "password": password}, timeout=60)
        if not result["ok"]:
            return result
        pfx_bytes = base64.b64decode(result["data"]["pfx_base64"])
        return {"ok": True, "output": "PFX/P12 exportado do HSM.", "pfx_bytes": pfx_bytes}

    def search_objects(self, query: str = "") -> dict:
        result = self._call("search", {"query": query})
        if not result["ok"]:
            return result
        return {"ok": True, "output": "Busca concluída.", "results": result["data"]["results"]}
