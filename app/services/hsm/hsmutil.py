"""Provider via utilitário CLI do HSM (ex.: hsmutil da Dinamo).

Os comandos são templates configurados na aba Configurações, com placeholders:
{label} {cn} {sans} {keysize} {key_type} {out}
Nunca executa string livre vinda da UI — apenas os templates salvos.
"""
import shlex
import subprocess

from .base import KeyProvider

KEY_SIZES = {"rsa2048": "2048", "rsa4096": "4096", "ecp256": "256"}


class HsmUtilProvider(KeyProvider):
    name = "hsmutil"

    def __init__(self, templates: dict):
        self.templates = templates or {}

    def _run(self, template_name: str, **params) -> dict:
        template = (self.templates.get(template_name) or "").strip()
        if not template:
            return {"ok": False, "output":
                    f"Template '{template_name}' não configurado. "
                    "Defina o comando na aba Configurações > HSM."}
        try:
            cmd = template.format(**params)
        except KeyError as e:
            return {"ok": False, "output": f"Placeholder desconhecido no template: {e}"}
        try:
            proc = subprocess.run(shlex.split(cmd), capture_output=True,
                                  text=True, timeout=120)
        except FileNotFoundError:
            return {"ok": False, "output": f"Executável não encontrado: {cmd.split()[0]}"}
        except subprocess.TimeoutExpired:
            return {"ok": False, "output": "Comando excedeu o tempo limite (120s)."}
        output = (proc.stdout + "\n" + proc.stderr).strip()
        return {"ok": proc.returncode == 0, "output": output, "command": cmd}

    def _params(self, label, cn="", sans=None, key_type="rsa2048", out=""):
        return {
            "label": label, "cn": cn or label,
            "sans": ",".join(sans or []),
            "key_type": key_type,
            "keysize": KEY_SIZES.get(key_type, "2048"),
            "out": out,
        }

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        return self._run("gen_key", **self._params(label, key_type=key_type, out=kwargs.get("out", "")))

    def gen_csr(self, label, cn, sans=None, key_type="rsa2048", **kwargs):
        result = self._run("gen_csr", **self._params(label, cn, sans, key_type, kwargs.get("out", "")))
        if result.get("ok") and "BEGIN CERTIFICATE REQUEST" in result.get("output", ""):
            result["csr_pem"] = result["output"]
        return result

    def export_key(self, label, out_path, **kwargs):
        return self._run("export_key", **self._params(label, out=out_path))
