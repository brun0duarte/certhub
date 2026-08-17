import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException

from app.routers import settings as settings_router


class _KeepAliveConnection:
    """Sobrevive ao conn.close() do router pra permitir múltiplas chamadas no teste."""
    def __init__(self, real):
        self._real = real

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._real, name)


def _make_conn(hsm_dinamo_profiles=None):
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    if hsm_dinamo_profiles is not None:
        real.execute("INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?)",
                      (json.dumps(hsm_dinamo_profiles),))
    real.commit()
    return real, _KeepAliveConnection(real)


# ---------------- US4 (specs/002-busca-filtro-hsm-perfis): validação de perfis de HSM ----------------

def test_update_settings_accepts_valid_hsm_profiles(monkeypatch):
    real, conn = _make_conn({"active": "", "profiles": []})
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    body = settings_router.SettingsIn(values={"hsm_dinamo_profiles": json.dumps({
        "active": "PRD",
        "profiles": [{"name": "PRD", "host": "10.0.0.1", "port": "4433", "username": "m", "password": "p"}],
    })})
    result = settings_router.update_settings(body)

    stored = json.loads(result["hsm_dinamo_profiles"])
    assert stored["active"] == "PRD"
    assert stored["profiles"][0]["name"] == "PRD"


def test_update_settings_rejects_duplicate_profile_name(monkeypatch):
    real, conn = _make_conn({"active": "", "profiles": []})
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    body = settings_router.SettingsIn(values={"hsm_dinamo_profiles": json.dumps({
        "active": "PRD",
        "profiles": [
            {"name": "PRD", "host": "a", "port": "1", "username": "u", "password": "p"},
            {"name": "PRD", "host": "b", "port": "2", "username": "u", "password": "p"},
        ],
    })})
    try:
        settings_router.update_settings(body)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_update_settings_rejects_active_without_matching_profile(monkeypatch):
    real, conn = _make_conn({"active": "", "profiles": []})
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    body = settings_router.SettingsIn(values={"hsm_dinamo_profiles": json.dumps({
        "active": "NOPE",
        "profiles": [{"name": "PRD", "host": "a", "port": "1", "username": "u", "password": "p"}],
    })})
    try:
        settings_router.update_settings(body)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_update_settings_rejects_removing_last_remaining_profile(monkeypatch):
    real, conn = _make_conn({
        "active": "PRD",
        "profiles": [{"name": "PRD", "host": "a", "port": "1", "username": "u", "password": "p"}],
    })
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    body = settings_router.SettingsIn(values={"hsm_dinamo_profiles": json.dumps({"active": "", "profiles": []})})
    try:
        settings_router.update_settings(body)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_update_settings_allows_switching_active_while_removing_previous_active(monkeypatch):
    real, conn = _make_conn({
        "active": "PRD",
        "profiles": [
            {"name": "PRD", "host": "a", "port": "1", "username": "u", "password": "p"},
            {"name": "NPRD", "host": "b", "port": "2", "username": "u", "password": "p"},
        ],
    })
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    body = settings_router.SettingsIn(values={"hsm_dinamo_profiles": json.dumps({
        "active": "NPRD",
        "profiles": [{"name": "NPRD", "host": "b", "port": "2", "username": "u", "password": "p"}],
    })})
    result = settings_router.update_settings(body)

    stored = json.loads(result["hsm_dinamo_profiles"])
    assert stored["active"] == "NPRD"
    assert [p["name"] for p in stored["profiles"]] == ["NPRD"]


# ---------------- installer_credentials: mascaramento de segredos ----------------

def test_get_settings_redacts_installer_credential_secrets(monkeypatch):
    real, conn = _make_conn({"active": "", "profiles": []})
    conn.execute("INSERT INTO settings (key, value) VALUES ('installer_credentials', ?)", (json.dumps({
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "SECRET1"},
        "aws": {"access_key_id": "AK", "secret_access_key": "SECRET2", "region": "sa-east-1"},
        "azion": {"api_token": "SECRET3"},
        "akamai": {"client_token": "ct", "client_secret": "SECRET4", "access_token": "SECRET5", "host": "h"},
    }),))
    conn.commit()
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    result = settings_router.get_settings()
    creds = json.loads(result["installer_credentials"])

    assert creds["keyvault_azure"]["client_secret"] == ""
    assert creds["aws"]["secret_access_key"] == ""
    assert creds["azion"]["api_token"] == ""
    assert creds["akamai"]["client_secret"] == ""
    assert creds["akamai"]["access_token"] == ""
    # Identificadores não-secretos continuam visíveis
    assert creds["keyvault_azure"]["tenant_id"] == "t"
    assert creds["aws"]["access_key_id"] == "AK"
    assert creds["akamai"]["client_token"] == "ct"
    assert creds["akamai"]["host"] == "h"


def test_update_settings_keeps_secret_when_blank_and_overwrites_when_provided(monkeypatch):
    real, conn = _make_conn({"active": "", "profiles": []})
    conn.execute("INSERT INTO settings (key, value) VALUES ('installer_credentials', ?)", (json.dumps({
        "keyvault_azure": {"tenant_id": "t", "client_id": "c", "client_secret": "OLD_SECRET"},
        "aws": {}, "azion": {}, "akamai": {},
    }),))
    conn.commit()
    monkeypatch.setattr(settings_router, "get_db", lambda: conn)

    # Envia tenant_id novo mas client_secret em branco — deve manter o segredo salvo
    body = settings_router.SettingsIn(values={"installer_credentials": json.dumps({
        "keyvault_azure": {"tenant_id": "t2", "client_id": "c", "client_secret": ""},
        "aws": {}, "azion": {}, "akamai": {},
    })})
    settings_router.update_settings(body)

    stored = json.loads(conn.execute(
        "SELECT value FROM settings WHERE key='installer_credentials'").fetchone()["value"])
    assert stored["keyvault_azure"]["tenant_id"] == "t2"
    assert stored["keyvault_azure"]["client_secret"] == "OLD_SECRET"

    # Agora envia um novo segredo — deve sobrescrever
    body2 = settings_router.SettingsIn(values={"installer_credentials": json.dumps({
        "keyvault_azure": {"tenant_id": "t2", "client_id": "c", "client_secret": "NEW_SECRET"},
        "aws": {}, "azion": {}, "akamai": {},
    })})
    settings_router.update_settings(body2)

    stored2 = json.loads(conn.execute(
        "SELECT value FROM settings WHERE key='installer_credentials'").fetchone()["value"])
    assert stored2["keyvault_azure"]["client_secret"] == "NEW_SECRET"
