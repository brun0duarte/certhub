"""Abrir pastas no gerenciador de arquivos (restrito à pasta base)."""
import platform
import subprocess
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_db, get_setting

router = APIRouter(tags=["files"])


class OpenIn(BaseModel):
    path: str


@router.post("/files/open")
def open_folder(body: OpenIn):
    conn = get_db()
    base = Path(get_setting(conn, "base_dir")).resolve()
    conn.close()
    target = Path(body.path).resolve()
    if base not in target.parents and target != base:
        raise HTTPException(403, "Só é permitido abrir pastas dentro da pasta base configurada.")
    if not target.exists():
        raise HTTPException(404, "Pasta não existe — use 'Criar pasta' na demanda primeiro.")
    system = platform.system()
    try:
        if system == "Windows":
            subprocess.Popen(["explorer", str(target)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
    except FileNotFoundError:
        raise HTTPException(500, "Gerenciador de arquivos não disponível neste sistema.")
    return {"ok": True}
