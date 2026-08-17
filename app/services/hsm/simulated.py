"""Provider de HSM simulado — mesmo contrato do DinamoJsProvider (gen_key,
gen_csr, export_key, import_cert, export_pfx, search_objects), mas
implementado em software com um keystore persistido em SQLite
(tabela hsm_sim_keys), sem exigir hardware Dinamo real.

Existe pra viabilizar desenvolvimento/demo do fluxo "criar chave → gerar CSR
→ importar certificado" integrado ao HSM sem depender de um HSM físico —
selecionável por perfil (`hsm_dinamo_profiles[].engine == "simulated"`),
ver app/routers/hsm.py::_provider().
"""
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from ..crypto import build_csr, generate_key, key_to_pem
from .base import ERROR_MESSAGES, ERROR_STATUS, KeyProvider


class SimulatedHsmProvider(KeyProvider):
    name = "simulated"

    def __init__(self, conn):
        self.conn = conn

    def _error(self, code: str, message: str | None = None) -> dict:
        code = code if code in ERROR_STATUS else "CONN_FAILED"
        return {"ok": False, "code": code, "http_status": ERROR_STATUS[code],
                "output": message or ERROR_MESSAGES[code]}

    def _row(self, label: str):
        return self.conn.execute(
            "SELECT label, key_type, key_pem, cert_pem FROM hsm_sim_keys WHERE label=?",
            (label,)).fetchone()

    # ---- contrato KeyProvider ----

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        if self._row(label):
            return self._error("ALREADY_EXISTS")
        key = generate_key(key_type)
        self.conn.execute(
            "INSERT INTO hsm_sim_keys (label, key_type, key_pem) VALUES (?,?,?)",
            (label, key_type, key_to_pem(key)))
        self.conn.commit()
        return {"ok": True, "output": f"Chave {key_type} criada (simulado).",
                "label": label, "key_type": key_type}

    def gen_csr(self, label, cn, sans=None, key_type="rsa2048", **kwargs):
        row = self._row(label)
        if not row:
            return self._error("NOT_FOUND")
        key = serialization.load_pem_private_key(row["key_pem"].encode(), password=None)
        csr_pem = build_csr(
            key, cn, sans or [], org=kwargs.get("org", ""), ou=kwargs.get("ou", ""),
            country=kwargs.get("country", ""), state=kwargs.get("state", ""),
            locality=kwargs.get("locality", ""), email=kwargs.get("email", ""))
        return {"ok": True, "output": "CSR gerada (simulado).", "csr_pem": csr_pem}

    def export_key(self, label, out_path, **kwargs):
        return {"ok": False, "output": "Chaves do HSM simulado só são exportáveis via PFX/P12 "
                                        "(use a exportação em /hsm/keys/{label}/export)."}

    # ---- operações específicas de HSM (fora do contrato KeyProvider genérico) ----

    def import_cert(self, label: str, cert_pem: str) -> dict:
        row = self._row(label)
        if not row:
            return self._error("NOT_FOUND")
        key = serialization.load_pem_private_key(row["key_pem"].encode(), password=None)
        cert = x509.load_pem_x509_certificate(cert_pem.encode())
        key_pub = key.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        cert_pub = cert.public_key().public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        if key_pub != cert_pub:
            return self._error("KEY_MISMATCH")
        self.conn.execute(
            "UPDATE hsm_sim_keys SET cert_pem=?, updated_at=datetime('now','localtime') WHERE label=?",
            (cert_pem, label))
        self.conn.commit()
        return {"ok": True, "output": "Certificado importado e associado à chave (simulado)."}

    def export_pfx(self, label: str, password: str) -> dict:
        row = self._row(label)
        if not row or not row["cert_pem"]:
            return self._error("NOT_FOUND")
        key = serialization.load_pem_private_key(row["key_pem"].encode(), password=None)
        cert = x509.load_pem_x509_certificate(row["cert_pem"].encode())
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=label.encode(), key=key, cert=cert, cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(password.encode()))
        return {"ok": True, "output": "PFX/P12 exportado (simulado).", "pfx_bytes": pfx_bytes}

    def search_objects(self, query: str = "") -> dict:
        rows = self.conn.execute(
            "SELECT label, key_type, cert_pem FROM hsm_sim_keys WHERE label LIKE ? ORDER BY label",
            (f"%{query}%",)).fetchall()
        results = []
        for r in rows:
            cn, not_after = None, None
            if r["cert_pem"]:
                cert = x509.load_pem_x509_certificate(r["cert_pem"].encode())
                cn_attrs = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
                cn = cn_attrs[0].value if cn_attrs else None
                not_after = cert.not_valid_after_utc.isoformat()
            results.append({"label": r["label"], "key_type": r["key_type"],
                             "has_certificate": bool(r["cert_pem"]), "cn": cn, "not_after": not_after})
        return {"ok": True, "output": "Busca concluída.", "results": results}
