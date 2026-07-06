"""Estrutura de pastas por demanda: {base}/{env}/{req}_{cn}/ (csr/, cert/, backup/)."""
import re
from pathlib import Path

SUBFOLDERS = ["csr", "cert", "backup"]


def sanitize(value: str) -> str:
    value = value.replace("*", "wildcard")
    return re.sub(r'[<>:"/\\|?%\s]+', "_", value).strip("._") or "sem_nome"


def req_folder(base_dir: str, template: str, req_number: str, cn: str, env: str) -> Path:
    rel = template.format(env=sanitize(env), req=sanitize(req_number), cn=sanitize(cn))
    return Path(base_dir) / rel


def create_structure(base_dir: str, template: str, req_number: str, cn: str, env: str) -> Path:
    folder = req_folder(base_dir, template, req_number, cn, env)
    for sub in SUBFOLDERS:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder
