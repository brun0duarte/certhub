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


def generate_key(key_type: str = "rsa2048"):
    """Gera uma chave privada (objeto cryptography, não PEM) do tipo pedido."""
    algo, size = KEY_TYPES.get(key_type, KEY_TYPES["rsa2048"])
    if algo == "EC":
        return ec.generate_private_key(ec.SECP256R1())
    return rsa.generate_private_key(public_exponent=65537, key_size=size)


def build_csr(key, cn: str, sans: list[str] | None = None,
              org: str = "", country: str = "",
              state: str = "", locality: str = "",
              ou: str = "", email: str = "") -> str:
    """Monta e assina uma CSR pra uma chave já existente. Retorna csr_pem."""
    name_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, cn)]
    if org:
        name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATION_NAME, org))
    if ou:
        name_attrs.append(x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, ou))
    if country:
        name_attrs.append(x509.NameAttribute(NameOID.COUNTRY_NAME, country[:2].upper()))
    if state:
        name_attrs.append(x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, state))
    if locality:
        name_attrs.append(x509.NameAttribute(NameOID.LOCALITY_NAME, locality))
    if email:
        name_attrs.append(x509.NameAttribute(NameOID.EMAIL_ADDRESS, email))

    builder = x509.CertificateSigningRequestBuilder().subject_name(x509.Name(name_attrs))

    san_list = [s.strip() for s in (sans or []) if s.strip()]
    if cn not in san_list:
        san_list.insert(0, cn)
    builder = builder.add_extension(
        x509.SubjectAlternativeName([x509.DNSName(s) for s in san_list]),
        critical=False,
    )

    csr = builder.sign(key, hashes.SHA256())
    return csr.public_bytes(serialization.Encoding.PEM).decode()


def key_to_pem(key) -> str:
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def generate_key_and_csr(cn: str, sans: list[str] | None = None, key_type: str = "rsa2048",
                         org: str = "", country: str = "",
                         state: str = "", locality: str = "",
                         ou: str = "", email: str = "") -> tuple[str, str]:
    """Retorna (key_pem, csr_pem)."""
    key = generate_key(key_type)
    csr_pem = build_csr(key, cn, sans, org=org, country=country,
                         state=state, locality=locality, ou=ou, email=email)
    return key_to_pem(key), csr_pem


def build_certreq_inf(cn: str, sans: list[str] | None = None, key_type: str = "rsa2048",
                      org: str = "", country: str = "", exportable: bool = True,
                      state: str = "", locality: str = "",
                      ou: str = "", email: str = "") -> str:
    """Monta o conteúdo do .inf usado por `certreq -new`."""
    _, size = KEY_TYPES.get(key_type, KEY_TYPES["rsa2048"])
    subject_parts = [f"CN={cn}"]
    if ou:
        subject_parts.append(f"OU={ou}")
    if org:
        subject_parts.append(f"O={org}")
    if locality:
        subject_parts.append(f"L={locality}")
    if state:
        subject_parts.append(f"S={state}")
    if country:
        subject_parts.append(f"C={country[:2].upper()}")
    if email:
        subject_parts.append(f"E={email}")

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
