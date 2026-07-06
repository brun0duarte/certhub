"""Geração de chave + CSR (wildcard/SAN) e arquivo .inf para certreq."""
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import NameOID

KEY_TYPES = {
    "rsa2048": ("RSA", 2048),
    "rsa4096": ("RSA", 4096),
    "ecp256": ("EC", 256),
}


def generate_key_and_csr(cn: str, sans: list[str] | None = None, key_type: str = "rsa2048",
                         org: str = "", country: str = "") -> tuple[str, str]:
    """Retorna (key_pem, csr_pem)."""
    algo, size = KEY_TYPES.get(key_type, KEY_TYPES["rsa2048"])
    if algo == "EC":
        key = ec.generate_private_key(ec.SECP256R1())
    else:
        key = rsa.generate_private_key(public_exponent=65537, key_size=size)

    name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, cn)]
    if org:
        name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org))
    if country:
        name_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country))

    builder = x509.CertificateSigningRequestBuilder().subject_name(x509.Name(name_attrs))

    san_list = [s.strip() for s in (sans or []) if s.strip()]
    if cn not in san_list:
        san_list.insert(0, cn)
    builder = builder.add_extension(
        x509.SubjectAlternativeName([x509.DNSName(s) for s in san_list]),
        critical=False,
    )

    csr = builder.sign(key, hashes.SHA256())
    key_pem = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    return key_pem, csr_pem


def build_certreq_inf(cn: str, sans: list[str] | None = None, key_type: str = "rsa2048",
                      org: str = "", country: str = "", exportable: bool = True) -> str:
    """Monta o conteúdo do .inf usado por `certreq -new`."""
    _, size = KEY_TYPES.get(key_type, KEY_TYPES["rsa2048"])
    subject_parts = [f"CN={cn}"]
    if org:
        subject_parts.append(f"O={org}")
    if country:
        subject_parts.append(f"C={country}")

    lines = [
        "[NewRequest]",
        f'Subject = "{", ".join(subject_parts)}"',
        f"KeyLength = {size if size >= 1024 else 2048}",
        "KeySpec = 1",
        f"Exportable = {'TRUE' if exportable else 'FALSE'}",
        "MachineKeySet = TRUE",
        'ProviderName = "Microsoft RSA SChannel Cryptographic Provider"',
        "RequestType = PKCS10",
        "HashAlgorithm = sha256",
    ]
    san_list = [s.strip() for s in (sans or []) if s.strip()]
    if cn not in san_list:
        san_list.insert(0, cn)
    if san_list:
        lines += ["", "[Extensions]", '2.5.29.17 = "{text}"']
        for i, san in enumerate(san_list):
            amp = "&" if i < len(san_list) - 1 else ""
            lines.append(f'_continue_ = "dns={san}{amp}"')
    return "\n".join(lines) + "\n"
