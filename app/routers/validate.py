"""Validação de cadeia: análise elo a elo de certificados enviados ou de um servidor remoto."""
import socket
import ssl
import urllib.request
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import AuthorityInformationAccessOID, NameOID
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

router = APIRouter(tags=["validate"])

MAX_AIA_HOPS = 4


def _load_certs(data: bytes, filename: str) -> list[x509.Certificate]:
    if b"-----BEGIN CERTIFICATE-----" in data:
        return x509.load_pem_x509_certificates(data)
    for loader in (lambda d: [x509.load_der_x509_certificate(d)],
                   pkcs7.load_der_pkcs7_certificates,
                   pkcs7.load_pem_pkcs7_certificates):
        try:
            return loader(data)
        except Exception:
            continue
    raise HTTPException(400, f"Não consegui ler certificados de '{filename}' "
                             "(formatos aceitos: PEM, DER, P7B)")


def _is_ca(cert: x509.Certificate) -> bool:
    try:
        return cert.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    except x509.ExtensionNotFound:
        return False


def _aia_ca_issuers_url(cert: x509.Certificate) -> str | None:
    try:
        aia = cert.extensions.get_extension_for_class(x509.AuthorityInformationAccess).value
    except x509.ExtensionNotFound:
        return None
    for desc in aia:
        if desc.access_method == AuthorityInformationAccessOID.CA_ISSUERS:
            url = desc.access_location.value
            if url.startswith("http"):
                return url
    return None


def _dns_names(cert: x509.Certificate) -> list[str]:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        return san.get_values_for_type(x509.DNSName)
    except x509.ExtensionNotFound:
        cn = cert.subject.get_attributes_for_oid(NameOID.COMMON_NAME)
        return [cn[0].value] if cn else []


def _hostname_match(cert: x509.Certificate, hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    for name in _dns_names(cert):
        name = name.lower()
        if name == host:
            return True
        if name.startswith("*.") and "." in host and host.split(".", 1)[1] == name[2:]:
            return True
    return False


def _key_info(cert: x509.Certificate) -> str:
    key = cert.public_key()
    name = type(key).__name__.replace("_", "").replace("PublicKey", "")
    size = getattr(key, "key_size", None)
    if size:
        return f"{name} {size}"
    curve = getattr(key, "curve", None)
    return f"{name} {curve.name}" if curve else name


def _cn_of(name: x509.Name) -> str:
    attrs = name.get_attributes_for_oid(NameOID.COMMON_NAME)
    return attrs[0].value if attrs else name.rfc4514_string()


def _order_chain(certs: list[x509.Certificate]) -> list[x509.Certificate]:
    by_subject = {c.subject.rfc4514_string(): c for c in certs}
    issuers = {c.issuer.rfc4514_string() for c in certs
               if c.issuer.rfc4514_string() != c.subject.rfc4514_string()}
    candidates = [c for c in certs if c.subject.rfc4514_string() not in issuers]
    non_ca = [c for c in candidates if not _is_ca(c)]
    leaf = (non_ca or candidates or certs)[0]
    chain, cur = [leaf], leaf
    while cur.subject != cur.issuer:
        nxt = by_subject.get(cur.issuer.rfc4514_string())
        if not nxt or nxt in chain:
            break
        chain.append(nxt)
        cur = nxt
    return chain


def _analyze(certs: list[x509.Certificate], hostname: str = "",
             fetch_aia: bool = False) -> dict:
    warnings = []
    if fetch_aia:
        for _ in range(MAX_AIA_HOPS):
            chain = _order_chain(certs)
            last = chain[-1]
            if last.subject == last.issuer:
                break
            url = _aia_ca_issuers_url(last)
            if not url:
                break
            try:
                with urllib.request.urlopen(url, timeout=6) as resp:
                    fetched = _load_certs(resp.read(), url)
                certs = certs + [c for c in fetched if c not in certs]
                warnings.append(f"Intermediária baixada via AIA: {url}")
            except HTTPException:
                warnings.append(f"AIA retornou conteúdo ilegível: {url}")
                break
            except Exception as e:
                warnings.append(f"Falha ao baixar via AIA ({url}): {e}")
                break

    chain = _order_chain(certs)
    now = datetime.now(timezone.utc)
    links, all_sig_ok, any_expired = [], True, False

    for i, cert in enumerate(chain):
        issuer_cert = chain[i + 1] if i + 1 < len(chain) else None
        self_signed = cert.subject == cert.issuer
        sig_ok, sig_error = None, ""
        verifier = issuer_cert or (cert if self_signed else None)
        if verifier is not None:
            try:
                cert.verify_directly_issued_by(verifier)
                sig_ok = True
            except Exception as e:
                sig_ok, sig_error = False, str(e)
                all_sig_ok = False
        expired = now > cert.not_valid_after_utc
        not_yet = now < cert.not_valid_before_utc
        if expired or not_yet:
            any_expired = True
        days_left = (cert.not_valid_after_utc - now).days
        is_ca = _is_ca(cert)
        if i > 0 and not is_ca:
            warnings.append(f"'{_cn_of(cert.subject)}' assina outros certificados "
                            "mas não tem basicConstraints CA=true.")
        links.append({
            "cn": _cn_of(cert.subject),
            "subject": cert.subject.rfc4514_string(),
            "issuer": cert.issuer.rfc4514_string(),
            "issuer_cn": _cn_of(cert.issuer),
            "serial": format(cert.serial_number, "x"),
            "not_before": cert.not_valid_before_utc.strftime("%Y-%m-%d %H:%M"),
            "not_after": cert.not_valid_after_utc.strftime("%Y-%m-%d %H:%M"),
            "days_left": days_left,
            "expired": expired,
            "not_yet_valid": not_yet,
            "is_ca": is_ca,
            "self_signed": self_signed,
            "sig_ok": sig_ok,
            "sig_error": sig_error,
            "sig_algo": cert.signature_hash_algorithm.name if cert.signature_hash_algorithm else "—",
            "key": _key_info(cert),
            "sans": _dns_names(cert) if i == 0 else [],
        })

    root = chain[-1]
    complete = root.subject == root.issuer
    missing = None
    if not complete:
        missing = {"issuer": _cn_of(root.issuer), "aia_url": _aia_ca_issuers_url(root)}

    unused = len(certs) - len(chain)
    if unused > 0:
        warnings.append(f"{unused} certificado(s) enviado(s) não pertence(m) à cadeia.")

    if not all_sig_ok or any_expired:
        verdict = "invalida"
    elif complete:
        verdict = "valida"
    else:
        verdict = "incompleta"

    hostname_ok = _hostname_match(chain[0], hostname) if hostname.strip() else None
    return {"verdict": verdict, "complete": complete, "missing": missing,
            "hostname": hostname.strip() or None, "hostname_ok": hostname_ok,
            "chain": links, "warnings": warnings}


@router.post("/validate/chain")
async def validate_chain(files: list[UploadFile] = File(...),
                         hostname: str = Form(""),
                         fetch_aia: bool = Form(False)):
    certs = []
    for f in files:
        data = await f.read()
        for cert in _load_certs(data, f.filename or "arquivo"):
            if cert not in certs:
                certs.append(cert)
    if not certs:
        raise HTTPException(400, "Nenhum certificado encontrado nos arquivos.")
    return _analyze(certs, hostname=hostname, fetch_aia=fetch_aia)


class RemoteIn(BaseModel):
    host: str
    port: int = 443
    fetch_aia: bool = False


@router.post("/validate/remote")
def validate_remote(body: RemoteIn):
    host = body.host.strip().replace("https://", "").split("/")[0]
    if ":" in host:
        host, _, p = host.partition(":")
        body.port = int(p)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with socket.create_connection((host, body.port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                raw_chain = (ssock.get_unverified_chain()
                             if hasattr(ssock, "get_unverified_chain")
                             else [ssock.getpeercert(binary_form=True)])
                tls = {"version": ssock.version(), "cipher": (ssock.cipher() or ["—"])[0]}
    except OSError as e:
        raise HTTPException(502, f"Não consegui conectar em {host}:{body.port} — {e}")
    certs = []
    for item in raw_chain or []:
        der = item if isinstance(item, bytes) else item.public_bytes(ssl.ENCODING_DER)
        cert = x509.load_der_x509_certificate(der)
        if cert not in certs:
            certs.append(cert)
    if not certs:
        raise HTTPException(502, f"O servidor {host}:{body.port} não apresentou certificados.")
    result = _analyze(certs, hostname=host, fetch_aia=body.fetch_aia)
    result["tls"] = tls
    result["server"] = f"{host}:{body.port}"
    return result
