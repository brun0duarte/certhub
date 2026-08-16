import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.hsm.dinamo_js import DinamoJsProvider

CONNECTION = {"host": "10.0.0.1", "port": "4433", "username": "master", "password": "s3gredo"}


class FakeCompletedProcess:
    def __init__(self, stdout, returncode=0):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = returncode


def _bridge_response(payload):
    def fake_run(args, input=None, capture_output=None, text=None, timeout=None):
        fake_run.calls.append({"args": args, "input": input, "timeout": timeout})
        return FakeCompletedProcess(json.dumps(payload))
    fake_run.calls = []
    return fake_run


def test_gen_key_success(monkeypatch):
    fake_run = _bridge_response({"ok": True, "data": {"label": "svc-01", "key_type": "rsa2048"}})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_key("svc-01", "rsa2048")

    assert result["ok"] is True
    assert result["label"] == "svc-01"
    assert fake_run.calls[0]["args"][-1] == "gen-key"


def test_gen_key_already_exists(monkeypatch):
    fake_run = _bridge_response({"ok": False, "error": "Rótulo em uso", "code": "ALREADY_EXISTS"})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_key("svc-01", "rsa2048")

    assert result["ok"] is False
    assert result["code"] == "ALREADY_EXISTS"
    assert result["http_status"] == 409


def test_gen_csr_not_found(monkeypatch):
    fake_run = _bridge_response({"ok": False, "error": "Chave inexistente", "code": "NOT_FOUND"})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_csr("nope", "www.exemplo.com.br")

    assert result["ok"] is False
    assert result["code"] == "NOT_FOUND"
    assert result["http_status"] == 404


def test_gen_csr_success_returns_pem(monkeypatch):
    fake_run = _bridge_response({"ok": True, "data": {"csr_pem": "-----BEGIN CERTIFICATE REQUEST-----\n...\n-----END CERTIFICATE REQUEST-----"}})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_csr("svc-01", "www.exemplo.com.br")

    assert result["ok"] is True
    assert "BEGIN CERTIFICATE REQUEST" in result["csr_pem"]


def test_import_cert_key_mismatch(monkeypatch):
    fake_run = _bridge_response({"ok": False, "error": "Chave pública não confere", "code": "KEY_MISMATCH"})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).import_cert("svc-01", "-----BEGIN CERTIFICATE-----...")

    assert result["ok"] is False
    assert result["code"] == "KEY_MISMATCH"
    assert result["http_status"] == 422


def test_export_pfx_not_exportable(monkeypatch):
    fake_run = _bridge_response({"ok": False, "error": "Chave não exportável", "code": "NOT_EXPORTABLE"})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).export_pfx("svc-01", "senha-forte")

    assert result["ok"] is False
    assert result["code"] == "NOT_EXPORTABLE"
    assert result["http_status"] == 403


def test_export_pfx_success_decodes_bytes(monkeypatch):
    import base64
    raw = b"conteudo-binario-do-pfx"
    fake_run = _bridge_response({"ok": True, "data": {"pfx_base64": base64.b64encode(raw).decode()}})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).export_pfx("svc-01", "senha-forte")

    assert result["ok"] is True
    assert result["pfx_bytes"] == raw


def test_search_empty_results_is_ok(monkeypatch):
    fake_run = _bridge_response({"ok": True, "data": {"results": []}})
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).search_objects("termo-inexistente")

    assert result["ok"] is True
    assert result["results"] == []


def test_conn_failed_when_node_missing(monkeypatch):
    def fake_run(*args, **kwargs):
        raise FileNotFoundError("node")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_key("svc-01")

    assert result["ok"] is False
    assert result["code"] == "CONN_FAILED"


def test_timeout_maps_to_timeout_code(monkeypatch):
    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd="node", timeout=30)
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = DinamoJsProvider(CONNECTION).gen_key("svc-01")

    assert result["ok"] is False
    assert result["code"] == "TIMEOUT"


def test_credentials_never_go_through_argv(monkeypatch):
    fake_run = _bridge_response({"ok": True, "data": {"label": "svc-01", "key_type": "rsa2048"}})
    monkeypatch.setattr(subprocess, "run", fake_run)

    DinamoJsProvider(CONNECTION).gen_key("svc-01", "rsa2048")

    call = fake_run.calls[0]
    assert CONNECTION["password"] not in call["args"]
    assert CONNECTION["password"] in call["input"]  # só via stdin
