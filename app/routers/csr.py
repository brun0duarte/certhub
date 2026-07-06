"""Geração de CSR: engine local (cryptography), certreq (.inf) e HSM (hsmutil)."""
import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_db, get_setting, log_activity
from ..services import crypto, folders
from ..services.hsm.hsmutil import HsmUtilProvider

router = APIRouter(tags=["csr"])


class CsrIn(BaseModel):
    cn: str
    sans: list[str] = []
    key_type: str = "rsa2048"
    org: str = ""
    country: str = ""
    engine: str = "local"          # local | certreq | hsmutil
    req_id: int | None = None
    hsm_label: str = ""


def _req_and_folder(conn, req_id):
    req = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not req:
        raise HTTPException(404, "Demanda não encontrada")
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.create_structure(base, template, req["req_number"], req["cn"], req["env"])
    return req, folder


@router.post("/csr/generate")
def generate_csr(body: CsrIn):
    cn = body.cn.strip()
    if not cn:
        raise HTTPException(400, "Informe o CN")
    conn = get_db()
    req, folder = (None, None)
    if body.req_id:
        req, folder = _req_and_folder(conn, body.req_id)

    result: dict = {"engine": body.engine, "cn": cn}
    fname = folders.sanitize(cn)

    if body.engine == "local":
        key_pem, csr_pem = crypto.generate_key_and_csr(
            cn, body.sans, body.key_type, body.org, body.country)
        result.update({"csr_pem": csr_pem, "ok": True})
        if folder is not None:
            key_file = folder / "csr" / f"{fname}.key"
            csr_file = folder / "csr" / f"{fname}.csr"
            key_file.write_text(key_pem)
            csr_file.write_text(csr_pem)
            result["saved"] = {"key": str(key_file), "csr": str(csr_file)}
        else:
            # sem REQ vinculada a chave é devolvida — o usuário decide onde guardar
            result["key_pem"] = key_pem
        detail = f"CSR local · {cn} · {body.key_type}"

    elif body.engine == "certreq":
        inf = crypto.build_certreq_inf(cn, body.sans, body.key_type, body.org, body.country)
        result.update({
            "inf_content": inf,
            "command": f"certreq -new {fname}.inf {fname}.csr",
            "ok": True,
        })
        if folder is not None:
            inf_file = folder / "csr" / f"{fname}.inf"
            inf_file.write_text(inf)
            result["saved"] = {"inf": str(inf_file)}
        detail = f"CSR certreq (.inf) · {cn}"

    elif body.engine == "hsmutil":
        templates = json.loads(get_setting(conn, "hsmutil_templates"))
        provider = HsmUtilProvider(templates)
        label = body.hsm_label.strip() or fname
        out = str(folder / "csr" / f"{fname}.csr") if folder is not None else f"{fname}.csr"
        hsm_result = provider.gen_csr(label, cn, body.sans, body.key_type, out=out)
        result.update(hsm_result)
        detail = f"CSR HSM · {cn} · label {label} · {'ok' if hsm_result['ok'] else 'FALHOU'}"

    else:
        conn.close()
        raise HTTPException(400, "Engine inválida (local, certreq ou hsmutil)")

    log_activity(conn, "csr_gerada", detail, body.req_id)
    if req and result.get("ok"):
        conn.execute("UPDATE reqs SET status='csr_gerada', "
                     "updated_at=datetime('now','localtime') WHERE id=? AND status='aberta'",
                     (body.req_id,))
    conn.commit()
    conn.close()
    return result
