import datetime
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.routers import hsm as hsm_router

USER = {"id": 1}

SCHEMA = """
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, action TEXT NOT NULL,
    detail TEXT DEFAULT '', user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
CREATE TABLE reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT, cn TEXT, env TEXT,
    status TEXT, csr_pem TEXT DEFAULT '', hsm_label TEXT DEFAULT '', hsm_engine TEXT DEFAULT '',
    updated_at TEXT
);
CREATE TABLE csrs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, cn TEXT, sans TEXT, subject TEXT,
    key_type TEXT, sig_algo TEXT, req_id INTEGER, pem TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, cn TEXT, sans TEXT, subject TEXT,
    issuer TEXT, serial TEXT, thumbprint_sha1 TEXT, not_before TEXT, not_after TEXT,
    key_type TEXT, source TEXT, hsm_label TEXT, file_path TEXT, cert_pem TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE hsm_sim_keys (
    label TEXT PRIMARY KEY, key_type TEXT NOT NULL DEFAULT 'rsa2048',
    key_pem TEXT NOT NULL, cert_pem TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


class _KeepAliveConnection:
    """Envolve a conexão in-memory pra sobreviver ao conn.close() do router,
    assim o teste consegue inspecionar o estado gravado depois da chamada."""
    def __init__(self, real):
        self._real = real

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._real, name)


def _make_conn():
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.executescript(SCHEMA)
    real.execute("INSERT INTO settings (key, value) VALUES ('password_policy', "
                  "'{\"length\": 16, \"upper\": true, \"lower\": true, \"digits\": true, "
                  "\"symbols\": true, \"exclude_ambiguous\": true}')")
    real.commit()
    return real, _KeepAliveConnection(real)


class FakeProvider:
    def __init__(self, **results):
        self._results = results

    def _result(self, name):
        value = self._results[name]
        return value() if callable(value) else value

    def gen_key(self, label, key_type="rsa2048", **kwargs):
        return self._result("gen_key")

    def gen_csr(self, label, cn, sans=None, **kwargs):
        return self._result("gen_csr")

    def import_cert(self, label, cert_pem):
        return self._result("import_cert")

    def export_pfx(self, label, password):
        return self._result("export_pfx")

    def search_objects(self, query=""):
        return self._result("search_objects")


def _self_signed_cert_pem(cn="hsm-test.example.com"):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, cn)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=365))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


# ---------------- US1: criar chave ----------------

def test_create_key_success(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        gen_key={"ok": True, "output": "ok", "label": "svc-01", "key_type": "rsa2048"}))

    result = hsm_router.create_key(hsm_router.HsmKeyIn(label="svc-01", key_type="rsa2048"), user=USER)

    assert result["ok"] is True
    logged = real.execute("SELECT * FROM activity_log").fetchone()
    assert logged["action"] == "hsm_chave_criada"
    assert logged["user_id"] == 1


def test_create_key_duplicate_label_raises_409(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        gen_key={"ok": False, "code": "ALREADY_EXISTS", "http_status": 409, "output": "Rótulo em uso."}))

    from fastapi import HTTPException
    try:
        hsm_router.create_key(hsm_router.HsmKeyIn(label="svc-01"), user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 409


# ---------------- US2: gerar CSR ----------------

def test_generate_csr_success(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        gen_csr={"ok": True, "output": "ok",
                 "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\nMIIB\n-----END CERTIFICATE REQUEST-----"}))

    body = hsm_router.HsmCsrIn(cn="www.exemplo.com.br", sans=["www.exemplo.com.br"])
    result = hsm_router.generate_csr("svc-01", body, user=USER)

    assert result["ok"] is True
    assert "BEGIN CERTIFICATE REQUEST" in result["csr_pem"]
    saved = real.execute("SELECT * FROM csrs").fetchone()
    assert saved["cn"] == "www.exemplo.com.br"


def test_generate_csr_unknown_label_raises_404(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        gen_csr={"ok": False, "code": "NOT_FOUND", "http_status": 404, "output": "Chave não encontrada."}))

    from fastapi import HTTPException
    body = hsm_router.HsmCsrIn(cn="www.exemplo.com.br")
    try:
        hsm_router.generate_csr("nope", body, user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 404


# ---------------- US3: importar certificado ----------------

def test_import_certificate_success(monkeypatch):
    import asyncio
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        import_cert={"ok": True, "output": "ok", "label": "svc-01", "imported": True}))

    cert_pem = _self_signed_cert_pem("svc-01.exemplo.com.br")
    result = asyncio.run(hsm_router.import_certificate(
        "svc-01", file=None, pem_text=cert_pem, req_id=None, user=USER))

    assert result["source"] == "hsm"
    assert result["hsm_label"] == "svc-01"
    assert result["cn"] == "svc-01.exemplo.com.br"


def test_import_certificate_key_mismatch_raises_422(monkeypatch):
    import asyncio
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        import_cert={"ok": False, "code": "KEY_MISMATCH", "http_status": 422,
                     "output": "Chave pública não confere."}))

    from fastapi import HTTPException
    cert_pem = _self_signed_cert_pem()
    try:
        asyncio.run(hsm_router.import_certificate("svc-01", file=None, pem_text=cert_pem, req_id=None, user=USER))
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 422


# ---------------- US4: exportar PFX/P12 ----------------

def test_export_pfx_success_returns_binary_and_password_header(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        export_pfx={"ok": True, "output": "ok", "pfx_bytes": b"conteudo-binario"}))

    response = hsm_router.export_pfx("svc-01", format="pfx", user=USER)

    assert response.body == b"conteudo-binario"
    assert response.headers["X-Export-Password"]
    assert response.media_type == "application/x-pkcs12"


def test_export_pfx_not_exportable_raises_403(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        export_pfx={"ok": False, "code": "NOT_EXPORTABLE", "http_status": 403,
                    "output": "Chave não exportável."}))

    from fastapi import HTTPException
    try:
        hsm_router.export_pfx("svc-01", format="pfx", user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 403


# ---------------- US5: buscar ----------------

def test_search_returns_results(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        search_objects={"ok": True, "output": "ok", "results": [
            {"label": "svc-01", "key_type": "rsa2048", "has_certificate": True,
             "cn": "svc-01.exemplo.com.br", "not_after": "2027-01-01T00:00:00"}]}))

    result = hsm_router.search_objects(q="svc-01", user=USER)

    assert len(result["results"]) == 1
    assert result["results"][0]["label"] == "svc-01"


def test_search_no_results_is_not_an_error(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        search_objects={"ok": True, "output": "ok", "results": []}))

    result = hsm_router.search_objects(q="nada-encontrado", user=USER)

    assert result["results"] == []


# ---------------- US4 (specs/002-busca-filtro-hsm-perfis): perfis de HSM ----------------

def test_get_hsm_profiles_lists_host_and_username_without_password(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)", (json.dumps({
        "active": "PRD",
        "profiles": [
            {"name": "PRD", "host": "10.0.0.1", "port": "4433", "username": "master", "password": "secreta"},
            {"name": "NPRD", "host": "10.0.1.1", "port": "4433", "username": "master", "password": "secreta2"},
        ],
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    result = hsm_router.list_profiles(user=USER)

    assert result == {"active": "PRD", "profiles": [
        {"name": "PRD", "host": "10.0.0.1", "username": "master", "engine": "dinamo_js"},
        {"name": "NPRD", "host": "10.0.1.1", "username": "master", "engine": "dinamo_js"},
    ]}
    assert "secreta" not in str(result) and "secreta2" not in str(result)


def test_set_active_profile_switches_active(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)", (json.dumps({
        "active": "PRD",
        "profiles": [
            {"name": "PRD", "host": "10.0.0.1", "port": "4433", "username": "m", "password": "p"},
            {"name": "NPRD", "host": "10.0.1.1", "port": "4433", "username": "m", "password": "p"},
        ],
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    result = hsm_router.set_active_profile(hsm_router.HsmActiveProfileIn(name="NPRD"), user=USER)

    assert result == {"ok": True, "active": "NPRD"}
    stored = json.loads(real.execute(
        "SELECT value FROM settings WHERE key='hsm_dinamo_profiles'").fetchone()["value"])
    assert stored["active"] == "NPRD"


def test_set_active_profile_unknown_name_raises_404(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)", (json.dumps({
        "active": "PRD",
        "profiles": [{"name": "PRD", "host": "x", "port": "1", "username": "u", "password": "p"}],
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    from fastapi import HTTPException
    try:
        hsm_router.set_active_profile(hsm_router.HsmActiveProfileIn(name="NOPE"), user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 404


def test_legacy_hsm_dinamo_config_migrates_to_profile_on_first_read(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_config', ?)", (json.dumps({
        "host": "10.0.0.9", "port": "4433", "username": "master", "password": "segredo",
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    profile = hsm_router._active_profile(conn)

    assert profile["name"] == "Padrão"
    assert profile["host"] == "10.0.0.9"
    stored = json.loads(real.execute(
        "SELECT value FROM settings WHERE key='hsm_dinamo_profiles'").fetchone()["value"])
    assert stored["active"] == "Padrão"
    assert stored["profiles"][0]["host"] == "10.0.0.9"


def test_provider_raises_400_when_no_profile_configured(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    from fastapi import HTTPException
    try:
        hsm_router._provider(conn)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


# ---------------- geração integrada ao HSM (specs: fluxo criar chave + CSR + importar) ----------------

def test_provider_returns_simulated_when_profile_engine_is_simulated(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)", (json.dumps({
        "active": "DEV", "profiles": [{"name": "DEV", "engine": "simulated"}],
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    from app.services.hsm.simulated import SimulatedHsmProvider
    provider = hsm_router._provider(conn)

    assert isinstance(provider, SimulatedHsmProvider)


def test_provider_returns_dinamo_js_when_engine_absent(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)", (json.dumps({
        "active": "PRD", "profiles": [{"name": "PRD", "host": "10.0.0.1", "port": "4433",
                                        "username": "master", "password": "x"}],
    }),))
    real.commit()
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    provider = hsm_router._provider(conn)

    assert isinstance(provider, hsm_router.DinamoJsProvider)


def test_generate_key_and_csr_api_engine_creates_key_then_csr(monkeypatch, tmp_path):
    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('base_dir', ?)", (str(tmp_path),))
    real.execute("INSERT INTO settings (key, value) VALUES ('folder_template', '{env}/{req}_{cn}')")
    real.execute("INSERT INTO reqs (req_number, cn, env, status) VALUES "
                 "('REQ0000099', 'svc.exemplo.com.br', 'PRD', 'aberta')")
    real.commit()
    req_id = real.execute("SELECT id FROM reqs WHERE req_number='REQ0000099'").fetchone()[0]
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        gen_key={"ok": True, "output": "ok", "label": "REQ0000099", "key_type": "rsa2048"},
        gen_csr={"ok": True, "output": "ok",
                 "csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\nMIIB\n-----END CERTIFICATE REQUEST-----"}))

    body = hsm_router.HsmGenerateIn(req_id=req_id, engine="api", cn="svc.exemplo.com.br")
    result = hsm_router.generate_key_and_csr(body, user=USER)

    assert result["ok"] is True
    assert result["label"] == "REQ0000099"
    row = real.execute("SELECT status, hsm_label, hsm_engine, csr_pem FROM reqs WHERE id=?", (req_id,)).fetchone()
    assert row["status"] == "csr_gerada"
    assert row["hsm_label"] == "REQ0000099"
    assert row["hsm_engine"] == "api"
    assert "BEGIN CERTIFICATE REQUEST" in row["csr_pem"]


def test_generate_key_and_csr_hsmutil_engine_calls_gen_key_then_gen_csr(monkeypatch, tmp_path):
    from app.services.hsm import hsmutil as hsmutil_module

    real, conn = _make_conn()
    real.execute("INSERT INTO settings (key, value) VALUES ('base_dir', ?)", (str(tmp_path),))
    real.execute("INSERT INTO settings (key, value) VALUES ('folder_template', '{env}/{req}_{cn}')")
    real.execute("INSERT INTO settings (key, value) VALUES ('hsmutil_templates', ?)", (json.dumps({
        "gen_key": "true --genkey {label}", "gen_csr": "true --gencsr {label} {cn}", "export_key": "",
    }),))
    real.execute("INSERT INTO reqs (req_number, cn, env, status) VALUES "
                 "('REQ0000100', 'svc2.exemplo.com.br', 'PRD', 'aberta')")
    real.commit()
    req_id = real.execute("SELECT id FROM reqs WHERE req_number='REQ0000100'").fetchone()[0]
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)

    calls = []

    class _Result:
        def __init__(self, stdout):
            self.stdout, self.stderr, self.returncode = stdout, "", 0

    def fake_run(args, capture_output=None, text=None, timeout=None):
        calls.append(args)
        if "--gencsr" in args:
            return _Result("-----BEGIN CERTIFICATE REQUEST-----\nMIIB\n-----END CERTIFICATE REQUEST-----")
        return _Result("chave criada")

    monkeypatch.setattr(hsmutil_module.subprocess, "run", fake_run)

    body = hsm_router.HsmGenerateIn(req_id=req_id, engine="hsmutil", cn="svc2.exemplo.com.br")
    result = hsm_router.generate_key_and_csr(body, user=USER)

    assert result["ok"] is True
    assert len(calls) == 2
    assert "--genkey" in calls[0]
    assert "--gencsr" in calls[1]
    row = real.execute("SELECT status, hsm_label, hsm_engine, csr_pem FROM reqs WHERE id=?", (req_id,)).fetchone()
    assert row["status"] == "csr_gerada"
    assert row["hsm_label"] == "REQ0000100"
    assert row["hsm_engine"] == "hsmutil"
    assert "BEGIN CERTIFICATE REQUEST" in row["csr_pem"]


def test_import_certificate_with_req_id_transitions_status_and_links_cert(monkeypatch):
    import asyncio
    real, conn = _make_conn()
    real.execute("INSERT INTO reqs (req_number, cn, env, status) VALUES "
                 "('REQ0000101', 'svc3.exemplo.com.br', 'PRD', 'csr_gerada')")
    real.commit()
    req_id = real.execute("SELECT id FROM reqs WHERE req_number='REQ0000101'").fetchone()[0]
    monkeypatch.setattr(hsm_router, "get_db", lambda: conn)
    monkeypatch.setattr(hsm_router, "_provider", lambda c: FakeProvider(
        import_cert={"ok": True, "output": "ok", "label": "REQ0000101", "imported": True}))

    cert_pem = _self_signed_cert_pem("svc3.exemplo.com.br")
    result = asyncio.run(hsm_router.import_certificate(
        "REQ0000101", file=None, pem_text=cert_pem, req_id=req_id, user=USER))

    assert result["req_id"] == req_id
    assert result["cert_pem"].strip() == cert_pem.strip()
    row = real.execute("SELECT status FROM reqs WHERE id=?", (req_id,)).fetchone()
    assert row["status"] == "cert_emitido"
