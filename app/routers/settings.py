"""Configurações da aplicação (chave/valor)."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import DEFAULT_SETTINGS, get_db, get_hsm_profiles

router = APIRouter(tags=["settings"])

JSON_KEYS = {"password_policy", "hsmutil_templates", "hsm_dinamo_config", "hsm_dinamo_profiles",
             "installer_credentials"}

# Campos de installer_credentials que nunca devem sair em texto puro na resposta
# de GET /settings — identificadores (tenant_id, client_id, access_key_id, region,
# akamai.client_token, akamai.host) continuam visíveis, mesmo padrão já usado hoje
# pra AWS access key (par público/privado).
INSTALLER_SECRET_FIELDS = {
    "keyvault_azure": ["client_secret"],
    "aws": ["secret_access_key"],
    "azion": ["api_token"],
    "akamai": ["client_secret", "access_token"],
}


class SettingsIn(BaseModel):
    values: dict[str, str]


def _redact_installer_credentials(raw: str) -> str:
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return raw
    for provider, fields in INSTALLER_SECRET_FIELDS.items():
        block = parsed.get(provider)
        if not isinstance(block, dict):
            continue
        for field in fields:
            if block.get(field):
                block[field] = ""
    return json.dumps(parsed)


def _merge_installer_credentials(conn, value: str) -> str:
    """Campo secreto enviado em branco mantém o valor já salvo — permite editar só um
    provedor em Configurações sem precisar redigitar (ou apagar) os outros segredos."""
    try:
        incoming = json.loads(value)
    except (TypeError, ValueError):
        return value
    row = conn.execute("SELECT value FROM settings WHERE key='installer_credentials'").fetchone()
    current = json.loads(row["value"]) if row else {}
    for provider, fields in INSTALLER_SECRET_FIELDS.items():
        if provider not in incoming:
            continue
        for field in fields:
            if not str(incoming[provider].get(field) or "").strip():
                incoming[provider][field] = (current.get(provider) or {}).get(field, "")
    return json.dumps(incoming)


@router.get("/settings")
def get_settings():
    conn = get_db()
    rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}
    rows["hsm_dinamo_profiles"] = json.dumps(get_hsm_profiles(conn))
    conn.close()
    for k, v in DEFAULT_SETTINGS.items():
        rows.setdefault(k, v)
    rows["installer_credentials"] = _redact_installer_credentials(
        rows.get("installer_credentials", DEFAULT_SETTINGS["installer_credentials"]))
    return rows


def _validate_hsm_profiles(conn, value: str):
    """Nome duplicado, `active` sem correspondência, e remoção do último perfil restante
    são rejeitados (FR-011, FR-012 — specs/002-busca-filtro-hsm-perfis)."""
    parsed = json.loads(value)
    profiles = parsed.get("profiles", [])
    names = [p.get("name", "") for p in profiles]
    if len(names) != len(set(names)):
        raise HTTPException(400, "Já existe um perfil de HSM com esse nome.")
    for p in profiles:
        if p.get("engine", "dinamo_js") not in ("dinamo_js", "simulated"):
            raise HTTPException(400, f"Mecanismo de HSM inválido no perfil \"{p.get('name', '')}\".")
    active = parsed.get("active", "")
    if profiles and active not in names:
        raise HTTPException(400, "Selecione um perfil de HSM ativo válido.")
    if not profiles:
        current = get_hsm_profiles(conn)
        if current.get("profiles"):
            raise HTTPException(400, "Não é possível remover o último perfil de HSM — cadastre outro antes.")


@router.put("/settings")
def update_settings(body: SettingsIn):
    conn = get_db()
    for key, value in body.values.items():
        if key not in DEFAULT_SETTINGS:
            conn.close()
            raise HTTPException(400, f"Configuração desconhecida: {key}")
        if key in JSON_KEYS:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                conn.close()
                raise HTTPException(400, f"Valor de '{key}' precisa ser JSON válido.")
        if key == "hsm_dinamo_profiles":
            try:
                _validate_hsm_profiles(conn, value)
            except HTTPException:
                conn.close()
                raise
    values_to_store = dict(body.values)
    if "installer_credentials" in values_to_store:
        values_to_store["installer_credentials"] = _merge_installer_credentials(
            conn, values_to_store["installer_credentials"])
    for key, value in values_to_store.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value))
    conn.commit()
    conn.close()
    return get_settings()
