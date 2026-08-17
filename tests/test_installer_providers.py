import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.installers import providers


class _KeepAliveConnection:
    """Sobrevive ao conn.close() do provider pra permitir múltiplas chamadas no teste."""
    def __init__(self, real):
        self._real = real

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._real, name)


def _make_conn(installer_credentials=None, certificates=None):
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    real.execute("CREATE TABLE certificates (id INTEGER PRIMARY KEY, cert_pem TEXT, file_path TEXT)")
    if installer_credentials is not None:
        real.execute("INSERT INTO settings (key, value) VALUES ('installer_credentials', ?)",
                      (json.dumps(installer_credentials),))
    for cert_id, cert_pem, file_path in (certificates or []):
        real.execute("INSERT INTO certificates (id, cert_pem, file_path) VALUES (?,?,?)",
                      (cert_id, cert_pem, file_path))
    real.commit()
    return _KeepAliveConnection(real)


def _patch_conn(monkeypatch, installer_credentials=None, certificates=None):
    conn = _make_conn(installer_credentials, certificates)
    monkeypatch.setattr(providers, "get_db", lambda: conn)
    return conn


class _Resp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self._json = json_data if json_data is not None else {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if not self.ok:
            raise providers.requests.HTTPError(f"HTTP {self.status_code}")


REQ = {"password": "senha123", "hsm_label": ""}


def _rsa_key_and_cert():
    """Par chave+certificado autoassinado real, pros testes que precisam de PEM válido
    de verdade (ex.: AzureKeyVaultProvider reempacota em PFX, não aceita placeholder)."""
    import datetime

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "svc.exemplo.com.br")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    key_pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    return key, cert, key_pem, cert_pem


# ---------------- _resolve_key_material ----------------

class _FakeHsmProvider:
    def __init__(self, key, cert):
        self.key, self.cert = key, cert

    def export_pfx(self, label, password):
        from cryptography.hazmat.primitives import serialization as ser
        from cryptography.hazmat.primitives.serialization import pkcs12
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=label.encode(), key=self.key, cert=self.cert, cas=None,
            encryption_algorithm=ser.BestAvailableEncryption(password.encode()))
        return {"ok": True, "output": "ok", "pfx_bytes": pfx_bytes}


def test_resolve_key_material_uses_hsm_when_label_set(monkeypatch):
    _patch_conn(monkeypatch)
    key, cert, key_pem, cert_pem = _rsa_key_and_cert()
    from app.routers import hsm as hsm_router
    monkeypatch.setattr(hsm_router, "_provider", lambda conn: _FakeHsmProvider(key, cert))

    k, c, chain = providers._resolve_key_material({"uploaded_file_path": ""}, {"hsm_label": "REQ0001"})
    assert "PRIVATE KEY" in k
    assert "CERTIFICATE" in c


def test_resolve_key_material_hsm_export_failure(monkeypatch):
    _patch_conn(monkeypatch)
    from app.routers import hsm as hsm_router

    class _FailingProvider:
        def export_pfx(self, label, password):
            return {"ok": False, "output": "HSM indisponível"}

    monkeypatch.setattr(hsm_router, "_provider", lambda conn: _FailingProvider())
    try:
        providers._resolve_key_material({}, {"hsm_label": "REQ0001"})
        assert False, "deveria levantar ValueError"
    except ValueError as e:
        assert "HSM indisponível" in str(e)


def test_resolve_key_material_falls_back_to_uploaded_file(tmp_path):
    key, cert, key_pem, cert_pem = _rsa_key_and_cert()
    from cryptography.hazmat.primitives import serialization as ser
    from cryptography.hazmat.primitives.serialization import pkcs12
    pfx_bytes = pkcs12.serialize_key_and_certificates(
        name=None, key=key, cert=cert, cas=None,
        encryption_algorithm=ser.BestAvailableEncryption(b"filepass"))
    pfx_path = tmp_path / "manual.pfx"
    pfx_path.write_bytes(pfx_bytes)

    k, c, chain = providers._resolve_key_material(
        {"uploaded_file_path": str(pfx_path)}, {"hsm_label": "", "password": "filepass"})
    assert "PRIVATE KEY" in k


def test_resolve_key_material_no_source_raises():
    try:
        providers._resolve_key_material({"uploaded_file_path": ""}, {"hsm_label": "", "password": ""})
        assert False, "deveria levantar ValueError"
    except ValueError as e:
        assert "HSM" in str(e)


# ---------------- key_source por provider ----------------

def test_key_source_by_provider():
    assert providers.AzureKeyVaultProvider.key_source == "hsm"
    assert providers.AwsAcmProvider.key_source == "hsm"
    assert providers.AwsSecretsManagerProvider.key_source == "hsm"
    assert providers.AzionProvider.key_source == "hsm"
    assert providers.IisWinrmProvider.key_source == "upload"
    for cls in (providers.AkamaiProvider, providers.ApacheSshProvider, providers.NginxSshProvider,
                providers.MainframeRacdcertProvider, providers.BalanceadorProvider):
        assert cls.key_source == "none"


# ---------------- Azure Key Vault ----------------

def test_azure_missing_credentials(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"keyvault_azure": {}})
    result = providers.AzureKeyVaultProvider().install(
        location={}, req=REQ,
        config={"vault_name": "v", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "Azure Key Vault" in result["error"]


def test_azure_missing_key_material(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"}})
    result = providers.AzureKeyVaultProvider().install(
        location={"uploaded_file_path": ""}, req=REQ,
        config={"vault_name": "v", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "HSM" in result["error"]


_KEYVAULT_IMPORT_RESPONSE = {
    "id": "https://vault1.vault.azure.net/certificates/cert1/3691dd9ffcb64387ac6c50a2a24f7265",
    "x5t": "MnDOH_QidmMXGLsqLY1KwDmFtx4",
    "attributes": {"nbf": 1786856515, "exp": 1788043710},
}


def test_azure_success(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"}})
    _key, _cert, key_pem, cert_pem = _rsa_key_and_cert()
    monkeypatch.setattr(providers, "_resolve_key_material", lambda location, req: (key_pem, cert_pem, ""))

    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if "login.microsoftonline.com" in url:
            return _Resp(200, {"access_token": "tok"})
        return _Resp(200, _KEYVAULT_IMPORT_RESPONSE)

    monkeypatch.setattr(providers.requests, "post", fake_post)
    result = providers.AzureKeyVaultProvider().install(
        location={}, req=REQ,
        config={"vault_name": "vault1", "certificate_name": "cert1"}, credential_ref="")
    assert result["ok"] is True
    assert "vault1" in result["output"]
    assert "3691dd9ffcb64387ac6c50a2a24f7265" in result["output"]
    assert "2026-08-29" in result["output"]
    assert "MnDOH_QidmMXGLsqLY1KwDmFtx4" in result["output"]
    assert len(calls) == 2


def test_azure_success_response_missing_fields(monkeypatch):
    """Resposta 200 sem id/x5t/attributes: instalação continua sucesso, cai na mensagem genérica (FR-004)."""
    _patch_conn(monkeypatch, installer_credentials={
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"}})
    _key, _cert, key_pem, cert_pem = _rsa_key_and_cert()
    monkeypatch.setattr(providers, "_resolve_key_material", lambda location, req: (key_pem, cert_pem, ""))

    def fake_post(url, **kwargs):
        if "login.microsoftonline.com" in url:
            return _Resp(200, {"access_token": "tok"})
        return _Resp(200, {})

    monkeypatch.setattr(providers.requests, "post", fake_post)
    result = providers.AzureKeyVaultProvider().install(
        location={}, req=REQ,
        config={"vault_name": "vault1", "certificate_name": "cert1"}, credential_ref="")
    assert result["ok"] is True
    assert result["output"] == "Certificado importado no Key Vault 'vault1' como 'cert1'."


def test_azure_request_includes_policy(monkeypatch):
    """A requisição de importação sempre declara a política do certificado (FR-001)."""
    _patch_conn(monkeypatch, installer_credentials={
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"}})
    _key, _cert, key_pem, cert_pem = _rsa_key_and_cert()
    monkeypatch.setattr(providers, "_resolve_key_material", lambda location, req: (key_pem, cert_pem, ""))

    import_calls = []

    def fake_post(url, **kwargs):
        if "login.microsoftonline.com" in url:
            return _Resp(200, {"access_token": "tok"})
        import_calls.append(kwargs.get("json"))
        return _Resp(200, _KEYVAULT_IMPORT_RESPONSE)

    monkeypatch.setattr(providers.requests, "post", fake_post)
    providers.AzureKeyVaultProvider().install(
        location={}, req=REQ,
        config={"vault_name": "vault1", "certificate_name": "cert1"}, credential_ref="")
    assert len(import_calls) == 1
    policy = import_calls[0]["policy"]
    assert policy["key_props"] == {"exportable": True, "kty": "RSA", "key_size": 2048, "reuse_key": False}
    assert policy["secret_props"] == {"contentType": "application/x-pkcs12"}


def test_azure_api_error_passed_through(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "s"}})
    _key, _cert, key_pem, cert_pem = _rsa_key_and_cert()
    monkeypatch.setattr(providers, "_resolve_key_material", lambda location, req: (key_pem, cert_pem, ""))

    def fake_post(url, **kwargs):
        if "login.microsoftonline.com" in url:
            return _Resp(200, {"access_token": "tok"})
        return _Resp(403, text="Forbidden: vault not found")

    monkeypatch.setattr(providers.requests, "post", fake_post)
    result = providers.AzureKeyVaultProvider().install(
        location={}, req=REQ,
        config={"vault_name": "vault1", "certificate_name": "cert1"}, credential_ref="")
    assert result["ok"] is False
    assert "Forbidden" in result["error"]


# ---------------- AWS Certificate Manager ----------------

def test_aws_acm_missing_credentials(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"aws": {}})
    result = providers.AwsAcmProvider().install(
        location={}, req=REQ,
        config={"region": "sa-east-1", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "AWS" in result["error"]


def test_aws_acm_missing_key_material(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "aws": {"access_key_id": "AK", "secret_access_key": "SK"}})
    result = providers.AwsAcmProvider().install(
        location={"uploaded_file_path": ""}, req=REQ,
        config={"region": "sa-east-1", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "HSM" in result["error"]


def test_aws_acm_success(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "aws": {"access_key_id": "AK", "secret_access_key": "SK", "region": "sa-east-1"}})
    monkeypatch.setattr(providers, "_resolve_key_material",
                         lambda location, req: ("KEYPEM", "CERTPEM", "CHAINPEM"))

    class _FakeAcmClient:
        def import_certificate(self, **kwargs):
            assert kwargs["Certificate"] == b"CERTPEM"
            assert kwargs["PrivateKey"] == b"KEYPEM"
            return {"CertificateArn": "arn:aws:acm:xyz"}

    monkeypatch.setattr(providers.boto3, "client", lambda service, **kw: _FakeAcmClient())
    result = providers.AwsAcmProvider().install(
        location={}, req=REQ,
        config={"region": "sa-east-1", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is True
    assert "arn:aws:acm:xyz" in result["output"]


def test_aws_acm_boto_error_passed_through(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "aws": {"access_key_id": "AK", "secret_access_key": "SK", "region": "sa-east-1"}})
    monkeypatch.setattr(providers, "_resolve_key_material", lambda location, req: ("KEYPEM", "CERTPEM", ""))

    class _FakeAcmClient:
        def import_certificate(self, **kwargs):
            raise providers.ClientError({"Error": {"Code": "ValidationException", "Message": "bad cert"}},
                                          "ImportCertificate")

    monkeypatch.setattr(providers.boto3, "client", lambda service, **kw: _FakeAcmClient())
    result = providers.AwsAcmProvider().install(
        location={}, req=REQ,
        config={"region": "sa-east-1", "certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "bad cert" in result["error"]


# ---------------- AWS Secrets Manager ----------------

def test_aws_secrets_manager_missing_key_material(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "aws": {"access_key_id": "AK", "secret_access_key": "SK"}})
    result = providers.AwsSecretsManagerProvider().install(
        location={"uploaded_file_path": ""}, req=REQ,
        config={"region": "sa-east-1", "secret_name": "s"}, credential_ref="")
    assert result["ok"] is False
    assert "HSM" in result["error"]


def test_aws_secrets_manager_success(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "aws": {"access_key_id": "AK", "secret_access_key": "SK", "region": "sa-east-1"}})
    monkeypatch.setattr(providers, "_resolve_key_material",
                         lambda location, req: ("KEYPEM", "CERTPEM", "CHAINPEM"))

    class _FakeSmClient:
        def put_secret_value(self, **kwargs):
            payload = json.loads(kwargs["SecretString"])
            assert payload == {"tls.crt": "CERTPEM", "tls.key": "KEYPEM", "ca.crt": "CHAINPEM"}

    monkeypatch.setattr(providers.boto3, "client", lambda service, **kw: _FakeSmClient())
    result = providers.AwsSecretsManagerProvider().install(
        location={}, req=REQ,
        config={"region": "sa-east-1", "secret_name": "meu-secret"}, credential_ref="")
    assert result["ok"] is True
    assert "meu-secret" in result["output"]


# ---------------- Azion ----------------

def test_azion_missing_token(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"azion": {}})
    result = providers.AzionProvider().install(
        location={}, req=REQ,
        config={"certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "Azion" in result["error"]


def test_azion_missing_key_material(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"azion": {"api_token": "tok"}})
    result = providers.AzionProvider().install(
        location={"uploaded_file_path": ""}, req=REQ,
        config={"certificate_name": "c"}, credential_ref="")
    assert result["ok"] is False
    assert "HSM" in result["error"]


def test_azion_success(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"azion": {"api_token": "tok"}})
    monkeypatch.setattr(providers, "_resolve_key_material",
                         lambda location, req: ("KEYPEM", "CERTPEM", ""))

    def fake_post(url, **kwargs):
        assert url == "https://api.azion.com/v4/workspace/tls/certificates"
        assert kwargs["json"]["certificate"] == "CERTPEM"
        assert kwargs["json"]["private_key"] == "KEYPEM"
        assert kwargs["json"]["type"] == "edge_certificate"
        assert kwargs["json"]["active"] is True
        assert kwargs["headers"]["Authorization"] == "Bearer tok"
        return _Resp(201, {"data": {
            "id": 154496, "status": "inactive", "status_detail": "",
            "validity": "2026-08-29 20:32:00+00:00", "key_algorithm": "rsa_2048",
        }})

    monkeypatch.setattr(providers.requests, "post", fake_post)
    result = providers.AzionProvider().install(
        location={}, req=REQ,
        config={"certificate_name": "c"}, credential_ref="")
    assert result["ok"] is True
    assert "154496" in result["output"]
    assert "inactive" in result["output"]
    assert "rsa_2048" in result["output"]


# ---------------- Akamai ----------------

def test_akamai_missing_credentials(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={"akamai": {}},
                certificates=[(1, "CERTPEM", None)])
    result = providers.AkamaiProvider().install(
        location={"cert_id": 1}, req=REQ, config={"enrollment_id": "42"}, credential_ref="")
    assert result["ok"] is False
    assert "Akamai" in result["error"]


def test_akamai_missing_cert(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "akamai": {"client_token": "a", "client_secret": "b", "access_token": "c", "host": "host.example.com"}})
    result = providers.AkamaiProvider().install(
        location={"cert_id": None}, req=REQ, config={"enrollment_id": "42"}, credential_ref="")
    assert result["ok"] is False
    assert "certificado" in result["error"]


def test_akamai_no_pending_change(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "akamai": {"client_token": "a", "client_secret": "b", "access_token": "c", "host": "host.example.com"}},
        certificates=[(1, "CERTPEM", None)])
    monkeypatch.setattr(providers.requests, "get", lambda url, **kw: _Resp(200, {"pendingChanges": []}))
    result = providers.AkamaiProvider().install(
        location={"cert_id": 1}, req=REQ, config={"enrollment_id": "42"}, credential_ref="")
    assert result["ok"] is False
    assert "mudança pendente" in result["error"]


def test_akamai_success(monkeypatch):
    _patch_conn(monkeypatch, installer_credentials={
        "akamai": {"client_token": "a", "client_secret": "b", "access_token": "c", "host": "host.example.com"}},
        certificates=[(1, "CERTPEM", None)])
    monkeypatch.setattr(providers.requests, "get",
                         lambda url, **kw: _Resp(200, {"pendingChanges": ["/cps/v2/enrollments/42/changes/9"]}))
    monkeypatch.setattr(providers.requests, "put", lambda url, **kw: _Resp(200, {}))
    result = providers.AkamaiProvider().install(
        location={"cert_id": 1}, req=REQ, config={"enrollment_id": "42"}, credential_ref="")
    assert result["ok"] is True


# ---------------- US2/US3: bloqueio honesto por BeyondTrust / protocolo desconhecido ----------------

def test_apache_missing_fields():
    result = providers.ApacheSshProvider().install(
        location={}, req=REQ, config={}, credential_ref="ref-apache")
    assert result["ok"] is False
    assert "Campos obrigatórios" in result["error"]


def test_apache_blocked_by_beyondtrust():
    config = {"host": "srv1", "remote_cert_path": "/etc/ssl/c.crt", "remote_key_path": "/etc/ssl/c.key"}
    result = providers.ApacheSshProvider().install(
        location={}, req=REQ, config=config, credential_ref="ref-apache")
    assert result["ok"] is False
    assert "BeyondTrust" in result["error"]
    assert "ref-apache" in result["error"]
    assert "srv1" in result["error"]


def test_nginx_blocked_by_beyondtrust():
    config = {"host": "srv2", "remote_cert_path": "/etc/ssl/c.crt", "remote_key_path": "/etc/ssl/c.key"}
    result = providers.NginxSshProvider().install(
        location={}, req=REQ, config=config, credential_ref="ref-nginx")
    assert result["ok"] is False
    assert "BeyondTrust" in result["error"]


def test_iis_blocked_by_beyondtrust():
    result = providers.IisWinrmProvider().install(
        location={}, req=REQ, config={"host": "winsrv"}, credential_ref="ref-iis")
    assert result["ok"] is False
    assert "BeyondTrust" in result["error"]


def test_mainframe_blocked_by_beyondtrust():
    config = {"host": "usshost", "keyring": "RING1", "userid_label": "LBL"}
    result = providers.MainframeRacdcertProvider().install(
        location={}, req=REQ, config=config, credential_ref="ref-mf")
    assert result["ok"] is False
    assert "BeyondTrust" in result["error"]


def test_balanceador_missing_fields():
    result = providers.BalanceadorProvider().install(
        location={}, req=REQ, config={"tipo": "CTC"}, credential_ref="")
    assert result["ok"] is False
    assert "Campos obrigatórios" in result["error"]


def test_balanceador_no_known_protocol():
    config = {"tipo": "CTC", "certificate_name": "c", "host": "lb1"}
    result = providers.BalanceadorProvider().install(
        location={}, req=REQ, config=config, credential_ref="")
    assert result["ok"] is False
    assert "CTC" in result["error"]
    assert "nenhuma API conhecida" in result["error"]
