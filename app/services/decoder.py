"""Detecção automática de tipo e decodificação: certificado, CSR, chave privada ou PFX."""
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import dsa, ec, rsa
from cryptography.hazmat.primitives.serialization import (
    Encoding, load_der_private_key, load_pem_private_key, pkcs12,
)
from cryptography.x509.oid import ExtensionOID, NameOID

from . import certparse


def load_csr(data: bytes) -> x509.CertificateSigningRequest | None:
    try:
        return x509.load_pem_x509_csr(data)
    except Exception:
        pass
    try:
        return x509.load_der_x509_csr(data)
    except Exception:
        return None


def _key_type_label(pub) -> str:
    if isinstance(pub, rsa.RSAPublicKey):
        return f"RSA {pub.key_size}"
    if isinstance(pub, ec.EllipticCurvePublicKey):
        return f"EC {pub.curve.name}"
    if isinstance(pub, dsa.DSAPublicKey):
        return f"DSA {pub.key_size}"
    return type(pub).__name__


def decode_csr_fields(csr: x509.CertificateSigningRequest) -> dict:
    cn_attrs = csr.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
    sans = []
    try:
        ext = csr.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = ext.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        pass
    return {
        "cn": cn_attrs[0].value if cn_attrs else csr.subject.rfc4514_string(),
        "subject": csr.subject.rfc4514_string(),
        "sans": ", ".join(sans),
        "key_type": _key_type_label(csr.public_key()),
        "sig_algo": csr.signature_hash_algorithm.name if csr.signature_hash_algorithm else "—",
        "signature_valid": csr.is_signature_valid,
        "pem": csr.public_bytes(Encoding.PEM).decode(),
    }


def decode_key_fields(key, encrypted: bool) -> dict:
    return {"key_type": _key_type_label(key.public_key()), "encrypted": encrypted}


def _try_private_key(data: bytes, pwd: bytes | None):
    """Retorna (key|None, needs_password: bool)."""
    for loader in (load_pem_private_key, load_der_private_key):
        try:
            return loader(data, password=pwd), False
        except TypeError:
            return None, True
        except Exception:
            continue
    return None, False


def detect_and_decode(data: bytes, password: str | None = None, filename: str = "") -> dict:
    """Auto-detecta o tipo do conteúdo colado/enviado e devolve os campos decodificados.
    Nunca devolve material de chave privada, só metadados."""
    pwd = password.encode() if password else None

    try:
        cert = certparse._load_x509(data)
        return {"type": "cert", **certparse._extract(cert)}
    except ValueError:
        pass

    csr = load_csr(data)
    if csr is not None:
        return {"type": "csr", **decode_csr_fields(csr)}

    looks_pem = data.lstrip().startswith(b"-----BEGIN")
    looks_pfx = filename.lower().endswith((".pfx", ".p12"))
    if not looks_pem or looks_pfx:
        try:
            key, pfx_cert, extra = pkcs12.load_key_and_certificates(data, pwd)
            return {
                "type": "pfx",
                "has_key": key is not None,
                "cert": certparse._extract(pfx_cert) if pfx_cert is not None else None,
                "extra_certs": len(extra or []),
            }
        except Exception:
            if pwd is None and (not looks_pem or looks_pfx):
                return {"type": "needs_password", "hint": "pfx"}

    key, needs_pwd = _try_private_key(data, pwd)
    if needs_pwd:
        return {"type": "needs_password", "hint": "key"}
    if key is not None:
        return {"type": "key", **decode_key_fields(key, encrypted=bool(pwd))}

    raise ValueError("Conteúdo não reconhecido — cole um certificado, CSR, chave privada ou envie um PFX.")
