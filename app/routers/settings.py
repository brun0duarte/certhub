"""Configurações da aplicação (chave/valor)."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import DEFAULT_SETTINGS, get_db

router = APIRouter(tags=["settings"])

JSON_KEYS = {"password_policy", "hsmutil_templates"}


class SettingsIn(BaseModel):
    values: dict[str, str]


@router.get("/settings")
def get_settings():
    conn = get_db()
    rows = {r["key"]: r["value"] for r in conn.execute("SELECT key, value FROM settings")}
    conn.close()
    for k, v in DEFAULT_SETTINGS.items():
        rows.setdefault(k, v)
    return rows


@router.put("/settings")
def update_settings(body: SettingsIn):
    for key, value in body.values.items():
        if key not in DEFAULT_SETTINGS:
            raise HTTPException(400, f"Configuração desconhecida: {key}")
        if key in JSON_KEYS:
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise HTTPException(400, f"Valor de '{key}' precisa ser JSON válido.")
    conn = get_db()
    for key, value in body.values.items():
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value))
    conn.commit()
    conn.close()
    return get_settings()
