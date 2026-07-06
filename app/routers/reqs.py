"""Demandas (REQ): CRUD, status, locais de instalação, pastas e histórico."""
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import REQ_STATUSES, get_db, get_setting, log_activity
from ..services import folders, passwordgen

router = APIRouter(tags=["reqs"])

REQ_FORMAT = re.compile(r"^REQ\d{7}$", re.IGNORECASE)


class ReqIn(BaseModel):
    req_number: str
    cn: str
    env: str
    notes: str = ""
    password: str | None = None
    auto_password: bool = True


class ReqUpdate(BaseModel):
    cn: str | None = None
    env: str | None = None
    notes: str | None = None
    password: str | None = None
    status: str | None = None


class LocationIn(BaseModel):
    server: str
    path_or_store: str = ""
    installed_at: str | None = None
    notes: str = ""
    cert_id: int | None = None


def _auto_password(conn) -> str:
    policy = json.loads(get_setting(conn, "password_policy"))
    return passwordgen.generate(**policy)


@router.get("/reqs")
def list_reqs(search: str = "", env: str = "", status: str = ""):
    conn = get_db()
    sql = """SELECT r.*,
                    (SELECT COUNT(*) FROM certificates c WHERE c.req_id = r.id) AS cert_count,
                    (SELECT COUNT(*) FROM install_locations l WHERE l.req_id = r.id) AS location_count
             FROM reqs r WHERE 1=1"""
    params = []
    if search:
        sql += " AND (r.req_number LIKE ? OR r.cn LIKE ? OR r.notes LIKE ?)"
        params += [f"%{search}%"] * 3
    if env:
        sql += " AND r.env = ?"
        params.append(env)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.created_at DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


@router.post("/reqs")
def create_req(body: ReqIn):
    req_number = body.req_number.strip().upper()
    if not REQ_FORMAT.match(req_number):
        raise HTTPException(400, "Número de REQ inválido — formato esperado: REQ0012345")
    conn = get_db()
    password = body.password or (_auto_password(conn) if body.auto_password else None)
    try:
        cur = conn.execute(
            "INSERT INTO reqs (req_number, cn, env, password, notes) VALUES (?,?,?,?,?)",
            (req_number, body.cn.strip(), body.env, password, body.notes),
        )
    except Exception:
        conn.close()
        raise HTTPException(409, f"Já existe uma demanda {req_number}.")
    req_id = cur.lastrowid
    log_activity(conn, "req_criada", f"{req_number} · CN {body.cn} · {body.env}", req_id)
    if password and body.auto_password and not body.password:
        log_activity(conn, "senha_gerada", "Senha gerada automaticamente na criação", req_id)
    conn.commit()
    row = dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())
    conn.close()
    return row


@router.get("/reqs/{req_id}")
def get_req(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    req = dict(row)
    req["locations"] = [dict(r) for r in conn.execute(
        "SELECT * FROM install_locations WHERE req_id=? ORDER BY id", (req_id,))]
    req["certificates"] = [dict(r) for r in conn.execute(
        "SELECT * FROM certificates WHERE req_id=? ORDER BY created_at DESC", (req_id,))]
    req["activity"] = [dict(r) for r in conn.execute(
        "SELECT * FROM activity_log WHERE req_id=? ORDER BY id DESC LIMIT 50", (req_id,))]
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"])
    req["folder"] = str(folder)
    req["folder_exists"] = folder.exists()
    conn.close()
    return req


@router.put("/reqs/{req_id}")
def update_req(req_id: int, body: ReqUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if "status" in fields and fields["status"] not in REQ_STATUSES:
        conn.close()
        raise HTTPException(400, f"Status inválido. Use: {', '.join(REQ_STATUSES)}")
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE reqs SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
            (*fields.values(), req_id),
        )
        if "status" in fields:
            log_activity(conn, "status_alterado", f"{row['status']} → {fields['status']}", req_id)
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())
    conn.close()
    return updated


@router.delete("/reqs/{req_id}")
def delete_req(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT req_number FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    conn.execute("DELETE FROM reqs WHERE id=?", (req_id,))
    log_activity(conn, "req_excluida", row["req_number"])
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/reqs/{req_id}/password/regenerate")
def regenerate_password(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    password = _auto_password(conn)
    conn.execute("UPDATE reqs SET password=?, updated_at=datetime('now','localtime') WHERE id=?",
                 (password, req_id))
    log_activity(conn, "senha_gerada", "Senha regenerada", req_id)
    conn.commit()
    conn.close()
    return {"password": password}


@router.post("/reqs/{req_id}/folder")
def create_folder(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.create_structure(base, template, row["req_number"], row["cn"], row["env"])
    log_activity(conn, "pasta_criada", str(folder), req_id)
    conn.commit()
    conn.close()
    return {"folder": str(folder)}


@router.post("/reqs/{req_id}/locations")
def add_location(req_id: int, body: LocationIn):
    conn = get_db()
    if not conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    cur = conn.execute(
        "INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes) "
        "VALUES (?,?,?,?,?,?)",
        (req_id, body.cert_id, body.server, body.path_or_store, body.installed_at, body.notes),
    )
    log_activity(conn, "local_adicionado", f"{body.server} · {body.path_or_store}", req_id)
    conn.commit()
    row = dict(conn.execute("SELECT * FROM install_locations WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.delete("/locations/{loc_id}")
def delete_location(loc_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Local não encontrado")
    conn.execute("DELETE FROM install_locations WHERE id=?", (loc_id,))
    log_activity(conn, "local_removido", f"{row['server']} · {row['path_or_store']}", row["req_id"])
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/activity")
def recent_activity(limit: int = 30):
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT a.*, r.req_number FROM activity_log a
           LEFT JOIN reqs r ON r.id = a.req_id
           ORDER BY a.id DESC LIMIT ?""", (min(limit, 200),))]
    conn.close()
    return rows
