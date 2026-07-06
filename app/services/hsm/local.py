"""Provider local: chaves em software via biblioteca `cryptography`."""
from .. import crypto
from .base import KeyProvider


class LocalProvider(KeyProvider):
    name = "local"

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        key_pem, _ = crypto.generate_key_and_csr(label, [], key_type)
        return {"ok": True, "key_pem": key_pem, "output": f"Chave {key_type} gerada em software."}

    def gen_csr(self, label, cn, sans=None, key_type="rsa2048", **kwargs):
        key_pem, csr_pem = crypto.generate_key_and_csr(
            cn, sans or [], key_type,
            org=kwargs.get("org", ""), country=kwargs.get("country", ""),
        )
        return {"ok": True, "key_pem": key_pem, "csr_pem": csr_pem,
                "output": "Chave e CSR geradas em software."}

    def export_key(self, label, out_path, **kwargs):
        return {"ok": False, "output": "Provider local não mantém chaves; use o arquivo .key salvo na pasta da REQ."}
