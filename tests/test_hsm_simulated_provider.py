import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.services.hsm.simulated import SimulatedHsmProvider

SCHEMA = """
CREATE TABLE hsm_sim_keys (
    label TEXT PRIMARY KEY, key_type TEXT NOT NULL DEFAULT 'rsa2048',
    key_pem TEXT NOT NULL, cert_pem TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""


def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _self_signed_cert_pem(key, cn="svc-01.exemplo.com.br"):
    import datetime
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


def test_gen_key_then_gen_csr_uses_same_key():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)

    key_result = provider.gen_key("svc-01", "rsa2048")
    assert key_result["ok"] is True

    csr_result = provider.gen_csr("svc-01", "svc-01.exemplo.com.br", ["svc-01.exemplo.com.br"])
    assert csr_result["ok"] is True
    assert "BEGIN CERTIFICATE REQUEST" in csr_result["csr_pem"]


def test_gen_key_duplicate_label_raises_already_exists():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("svc-01")

    result = provider.gen_key("svc-01")

    assert result["ok"] is False
    assert result["code"] == "ALREADY_EXISTS"
    assert result["http_status"] == 409


def test_gen_csr_unknown_label_raises_not_found():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)

    result = provider.gen_csr("nope", "svc-01.exemplo.com.br")

    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    assert result["http_status"] == 404


def test_import_cert_success_when_public_key_matches():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("svc-01")
    row = conn.execute("SELECT key_pem FROM hsm_sim_keys WHERE label='svc-01'").fetchone()
    key = serialization.load_pem_private_key(row["key_pem"].encode(), password=None)
    cert_pem = _self_signed_cert_pem(key)

    result = provider.import_cert("svc-01", cert_pem)

    assert result["ok"] is True
    stored = conn.execute("SELECT cert_pem FROM hsm_sim_keys WHERE label='svc-01'").fetchone()
    assert stored["cert_pem"] == cert_pem


def test_import_cert_key_mismatch_raises_422():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("svc-01")
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert_pem = _self_signed_cert_pem(other_key)

    result = provider.import_cert("svc-01", cert_pem)

    assert result["ok"] is False
    assert result["code"] == "KEY_MISMATCH"
    assert result["http_status"] == 422


def test_export_pfx_success():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("svc-01")
    row = conn.execute("SELECT key_pem FROM hsm_sim_keys WHERE label='svc-01'").fetchone()
    key = serialization.load_pem_private_key(row["key_pem"].encode(), password=None)
    cert_pem = _self_signed_cert_pem(key)
    provider.import_cert("svc-01", cert_pem)

    result = provider.export_pfx("svc-01", "s3nh@Forte123")

    assert result["ok"] is True
    assert isinstance(result["pfx_bytes"], bytes)
    assert len(result["pfx_bytes"]) > 0


def test_export_pfx_without_certificate_raises_not_found():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("svc-01")

    result = provider.export_pfx("svc-01", "s3nh@Forte123")

    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"


def test_search_objects_filters_by_label_substring():
    conn = _make_conn()
    provider = SimulatedHsmProvider(conn)
    provider.gen_key("REQ0000001")
    provider.gen_key("REQ0000002")

    result = provider.search_objects("REQ0000001")

    assert result["ok"] is True
    assert len(result["results"]) == 1
    assert result["results"][0]["label"] == "REQ0000001"
    assert result["results"][0]["has_certificate"] is False
