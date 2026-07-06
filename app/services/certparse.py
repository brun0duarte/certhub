"""Leitura automática de certificados (.cer/.crt/.pem/.der/.pfx) -> campos."""
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import ExtensionOID, NameOID


def parse_certificate(data: bytes, filename: str = "", password: str | None = None) -> dict:
    """Extrai os campos de um certificado. Lança ValueError se ilegível."""
    name = filename.lower()
    if name.endswith((".pfx", ".p12")):
        pwd = password.encode() if password else None
        try:
            _key, cert, _extra = pkcs12.load_key_and_certificates(data, pwd)
        except Exception as e:
            raise ValueError(f"Não foi possível abrir o PFX (senha incorreta?): {e}")
        if cert is None:
            raise ValueError("O PFX não contém certificado.")
    else:
        cert = _load_x509(data)
    return _extract(cert)


def _load_x509(data: bytes) -> x509.Certificate:
    try:
        return x509.load_pem_x509_certificate(data)
    except Exception:
        pass
    try:
        return x509.load_der_x509_certificate(data)
    except Exception as e:
        raise ValueError(f"Arquivo não reconhecido como certificado PEM/DER: {e}")


def _extract(cert: x509.Certificate) -> dict:
    def _cn(name: x509.Name) -> str:
        attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
        return attrs[0].value if attrs else name.rfc4514_string()

    sans = []
    try:
        ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        sans = ext.value.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        pass

    pub = cert.public_key()
    if isinstance(pub, rsa.RSAPublicKey):
        key_type = f"RSA {pub.key_size}"
    elif isinstance(pub, ec.EllipticCurvePublicKey):
        key_type = f"EC {pub.curve.name}"
    else:
        key_type = type(pub).__name__

    return {
        "cn": _cn(cert.subject),
        "subject": cert.subject.rfc4514_string(),
        "issuer": cert.issuer.rfc4514_string(),
        "sans": ", ".join(sans),
        "serial": format(cert.serial_number, "x").upper(),
        "thumbprint_sha1": cert.fingerprint(hashes.SHA1()).hex().upper(),
        "not_before": cert.not_valid_before_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "not_after": cert.not_valid_after_utc.strftime("%Y-%m-%d %H:%M:%S"),
        "key_type": key_type,
    }
