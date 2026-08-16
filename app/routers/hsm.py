"""Integração com HSM (Dinamo Networks): criar chave, gerar CSR, importar
certificado, exportar PFX/P12 e buscar objetos na partição do HSM.
Ver specs/001-integracao-hsm-dinamo/."""
import json
from sqlite3 import Connection

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from pydantic import BaseModel

from ..db import get_db, get_hsm_profiles, get_setting, log_activity
from ..services import certparse, folders, passwordgen
from ..services.hsm.base import KeyProvider
from ..services.hsm.dinamo_js import DinamoJsProvider
from ..services.hsm.hsmutil import HsmUtilProvider
from ..services.hsm.simulated import SimulatedHsmProvider
from .auth import require_auth
from .csr import _req_and_folder

router = APIRouter(prefix="/hsm", tags=["hsm"])


def _active_profile(conn: Connection) -> dict:
    config = get_hsm_profiles(conn)
    profile = next((p for p in config.get("profiles", []) if p["name"] == config.get("active")), None)
    if not profile:
        raise HTTPException(400, "Nenhum perfil de HSM configurado — cadastre um em Configurações.")
    return profile


def _provider(conn: Connection) -> KeyProvider:
    profile = _active_profile(conn)
    if profile.get("engine", "dinamo_js") == "simulated":
        return SimulatedHsmProvider(conn)
    connection = {k: v for k, v in profile.items() if k not in ("name", "engine")}
    return DinamoJsProvider(connection)


def _raise_for_error(result: dict):
    """Converte um resultado de provider com ok=False no HTTPException correspondente."""
    status = result.get("http_status", 502)
    raise HTTPException(status, result.get("output", "Falha na operação com o HSM."))


def _to_pem(data: bytes) -> str:
    if data.strip().startswith(b"-----BEGIN"):
        return data.decode("utf-8")
    cert = x509.load_der_x509_certificate(data)
    return cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")


class HsmKeyIn(BaseModel):
    label: str
    key_type: str = "rsa2048"


@router.post("/keys")
def create_key(body: HsmKeyIn, user=Depends(require_auth)):
    label = body.label.strip()
    if not label:
        raise HTTPException(400, "Informe o rótulo da chave")
    conn = get_db()
    provider = _provider(conn)
    result = provider.gen_key(label, body.key_type)
    if not result["ok"]:
        conn.close()
        _raise_for_error(result)
    log_activity(conn, "hsm_chave_criada", f"{label} · {body.key_type}", None, user["id"])
    conn.commit()
    conn.close()
    return {"ok": True, "label": label, "key_type": body.key_type}


class HsmGenerateIn(BaseModel):
    req_id: int
    engine: str = "api"        # api (Dinamo real ou simulado, conforme perfil ativo) | hsmutil (CLI)
    cn: str
    sans: list[str] = []
    org: str = ""
    ou: str = ""
    country: str = ""
    state: str = ""
    locality: str = ""
    email: str = ""
    key_type: str = "rsa2048"


@router.post("/keys/generate")
def generate_key_and_csr(body: HsmGenerateIn, user=Depends(require_auth)):
    """Cria a chave + gera a CSR no HSM num só passo, pra uma demanda (REQ) —
    o rótulo é sempre o número da REQ. Fluxo de geração integrado ao HSM."""
    cn = body.cn.strip()
    if not cn:
        raise HTTPException(400, "Informe o CN")
    if body.engine not in ("api", "hsmutil"):
        raise HTTPException(400, "Mecanismo inválido (use 'api' ou 'hsmutil')")
    conn = get_db()
    req, folder = _req_and_folder(conn, body.req_id)
    label = req["req_number"]

    if body.engine == "hsmutil":
        templates = json.loads(get_setting(conn, "hsmutil_templates"))
        provider = HsmUtilProvider(templates)
        key_result = provider.gen_key(label, body.key_type)
        if not key_result.get("ok"):
            conn.close()
            raise HTTPException(key_result.get("http_status", 502),
                                 key_result.get("output") or "Falha ao criar chave via hsmutil.")
        out = str(folder / "csr" / f"{label}.csr")
        csr_result = provider.gen_csr(label, cn, body.sans, body.key_type, out=out)
        if not csr_result.get("ok") or not csr_result.get("csr_pem"):
            conn.close()
            raise HTTPException(csr_result.get("http_status", 502),
                                 csr_result.get("output") or "Falha ao gerar CSR via hsmutil "
                                 "(chave já foi criada no HSM — repita usando o mesmo rótulo).")
        csr_pem = csr_result["csr_pem"]
    else:
        provider = _provider(conn)
        key_result = provider.gen_key(label, body.key_type)
        if not key_result["ok"]:
            conn.close()
            _raise_for_error(key_result)
        csr_result = provider.gen_csr(label, cn, body.sans, org=body.org, ou=body.ou,
                                       country=body.country, state=body.state,
                                       locality=body.locality, email=body.email)
        if not csr_result["ok"]:
            conn.close()
            raise HTTPException(csr_result.get("http_status", 502),
                                 csr_result.get("output") or "Chave criada no HSM, mas falhou ao "
                                 "gerar a CSR — repita a geração usando o mesmo rótulo.")
        csr_pem = csr_result["csr_pem"]

    conn.execute(
        """INSERT INTO csrs (cn, sans, subject, key_type, req_id, pem)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (cn, ", ".join(body.sans), f"CN={cn}", "hsm", body.req_id, csr_pem))
    conn.execute("UPDATE reqs SET csr_pem=?, hsm_label=?, hsm_engine=? WHERE id=?",
                 (csr_pem, label, body.engine, body.req_id))
    conn.execute("UPDATE reqs SET status='csr_gerada', "
                 "updated_at=datetime('now','localtime') WHERE id=? AND status='aberta'",
                 (body.req_id,))
    log_activity(conn, "csr_gerada", f"CSR HSM ({body.engine}) · {cn} · label {label}",
                 body.req_id, user["id"])
    conn.commit()
    conn.close()
    return {"ok": True, "engine": body.engine, "cn": cn, "label": label, "csr_pem": csr_pem}


class HsmCsrIn(BaseModel):
    cn: str
    sans: list[str] = []
    org: str = ""
    ou: str = ""
    country: str = ""
    state: str = ""
    locality: str = ""
    email: str = ""
    req_id: int | None = None


@router.post("/keys/{label}/csr")
def generate_csr(label: str, body: HsmCsrIn, user=Depends(require_auth)):
    cn = body.cn.strip()
    if not cn:
        raise HTTPException(400, "Informe o CN")
    conn = get_db()
    req, folder = (None, None)
    if body.req_id:
        req, folder = _req_and_folder(conn, body.req_id)

    provider = _provider(conn)
    result = provider.gen_csr(label, cn, body.sans, org=body.org, ou=body.ou,
                               country=body.country, state=body.state,
                               locality=body.locality, email=body.email)
    if not result["ok"]:
        conn.close()
        _raise_for_error(result)

    csr_pem = result["csr_pem"]
    response = {"engine": "dinamo_js", "cn": cn, "label": label, "csr_pem": csr_pem, "ok": True}
    if folder is not None:
        fname = folders.sanitize(cn)
        csr_file = folder / "csr" / f"{fname}.csr"
        csr_file.write_text(csr_pem)
        response["saved"] = {"csr": str(csr_file)}

    conn.execute(
        """INSERT INTO csrs (cn, sans, subject, key_type, req_id, pem)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (cn, ", ".join(body.sans), f"CN={cn}", "hsm", body.req_id, csr_pem))
    if req:
        conn.execute("UPDATE reqs SET csr_pem=? WHERE id=?", (csr_pem, body.req_id))
        conn.execute("UPDATE reqs SET status='csr_gerada', "
                     "updated_at=datetime('now','localtime') WHERE id=? AND status='aberta'",
                     (body.req_id,))
    log_activity(conn, "csr_gerada", f"CSR HSM · {cn} · label {label}", body.req_id, user["id"])
    conn.commit()
    conn.close()
    return response


@router.post("/keys/{label}/certificate")
async def import_certificate(label: str, file: UploadFile | None = File(None),
                              pem_text: str = Form(""), req_id: int | None = Form(None),
                              user=Depends(require_auth)):
    if pem_text and pem_text.strip():
        data = pem_text.strip().encode("utf-8")
        filename = "certificado.pem"
    elif file and file.filename:
        data = await file.read()
        filename = file.filename
    else:
        raise HTTPException(400, "Envie um arquivo de certificado ou cole o conteúdo PEM.")

    try:
        info = certparse.parse_certificate(data, filename)
        cert_pem = _to_pem(data)
    except ValueError as e:
        raise HTTPException(400, str(e))

    conn = get_db()
    provider = _provider(conn)
    result = provider.import_cert(label, cert_pem)
    if not result["ok"]:
        conn.close()
        _raise_for_error(result)

    cur = conn.execute(
        """INSERT INTO certificates
           (cn, sans, subject, issuer, serial, thumbprint_sha1, not_before, not_after,
            key_type, source, hsm_label, req_id, cert_pem)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (info["cn"], info["sans"], info["subject"], info["issuer"], info["serial"],
         info["thumbprint_sha1"], info["not_before"], info["not_after"], info["key_type"],
         "hsm", label, req_id, cert_pem))
    cert_id = cur.lastrowid
    if req_id:
        conn.execute("UPDATE reqs SET status='cert_emitido', updated_at=datetime('now','localtime') "
                     "WHERE id=? AND status IN ('aberta','csr_gerada')", (req_id,))
    log_activity(conn, "certificado_importado_hsm", f"{label} · {info['cn']}", req_id, user["id"])
    conn.commit()
    row = dict(conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone())
    conn.close()
    return row


@router.get("/keys/{label}/export")
def export_pfx(label: str, format: str = "pfx", user=Depends(require_auth)):
    if format not in ("pfx", "p12"):
        raise HTTPException(400, "Formato inválido (use pfx ou p12)")
    conn = get_db()
    policy = json.loads(get_setting(conn, "password_policy"))
    password = passwordgen.generate(**policy)
    provider = _provider(conn)
    result = provider.export_pfx(label, password)
    if not result["ok"]:
        conn.close()
        _raise_for_error(result)
    log_activity(conn, "certificado_exportado_hsm", f"{label} · {format}", None, user["id"])
    conn.commit()
    conn.close()
    return Response(
        content=result["pfx_bytes"], media_type="application/x-pkcs12",
        headers={"X-Export-Password": password,
                 "Content-Disposition": f'attachment; filename="{label}.{format}"'})


class HsmActiveProfileIn(BaseModel):
    name: str


@router.get("/profiles")
def list_profiles(user=Depends(require_auth)):
    conn = get_db()
    config = get_hsm_profiles(conn)
    conn.close()
    return {"active": config.get("active", ""),
            "profiles": [{"name": p["name"], "host": p.get("host", ""), "username": p.get("username", ""),
                          "engine": p.get("engine", "dinamo_js")}
                         for p in config.get("profiles", [])]}


@router.put("/active-profile")
def set_active_profile(body: HsmActiveProfileIn, user=Depends(require_auth)):
    conn = get_db()
    config = get_hsm_profiles(conn)
    if not any(p["name"] == body.name for p in config.get("profiles", [])):
        conn.close()
        raise HTTPException(404, f"Perfil de HSM \"{body.name}\" não encontrado.")
    config["active"] = body.name
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('hsm_dinamo_profiles', ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (json.dumps(config),))
    log_activity(conn, "hsm_perfil_alternado", body.name, None, user["id"])
    conn.commit()
    conn.close()
    return {"ok": True, "active": body.name}


@router.get("/search")
def search_objects(q: str = "", user=Depends(require_auth)):
    conn = get_db()
    provider = _provider(conn)
    result = provider.search_objects(q)
    if not result["ok"]:
        conn.close()
        _raise_for_error(result)
    results = result["results"]
    log_activity(conn, "hsm_busca", f"'{q}' · {len(results)} resultado(s)", None, user["id"])
    conn.commit()
    conn.close()
    return {"results": results}
