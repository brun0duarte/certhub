"""Certificados: importação com parsing automático, listagem, tipos e cadeia."""
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from datetime import datetime, timezone

from ..db import CERT_TYPES, get_db, get_setting, log_activity, LIFECYCLE_STATUSES
from ..services import certparse, folders

router = APIRouter(tags=["certs"])


class CertUpdate(BaseModel):
    req_id: int | None = None
    cert_type: str | None = None
    lifecycle_status: str | None = None


def _issuer_cn_from_dn(dn: str) -> str:
    m = re.search(r"CN=([^,]+)", dn or "")
    return m.group(1) if m else (dn or "")


def _link_parent(conn, cert_id: int, issuer_dn: str, subject_dn: str):
    """Vincula o certificado ao emissor no repositório e adota filhos órfãos."""
    parent = conn.execute(
        "SELECT id FROM certificates WHERE subject=? AND id<>? LIMIT 1",
        (issuer_dn, cert_id)).fetchone()
    if parent and issuer_dn != subject_dn:
        conn.execute("UPDATE certificates SET parent_id=? WHERE id=?",
                     (parent["id"], cert_id))
    conn.execute(
        "UPDATE certificates SET parent_id=? WHERE issuer=? AND id<>? AND parent_id IS NULL",
        (cert_id, subject_dn, cert_id))


@router.get("/certs")
def list_certs(search: str = "", expiring_days: int | None = None,
               cert_type: str = "", issuer_cn: str = "", lifecycle: str = ""):
    conn = get_db()
    sql = """SELECT c.*, r.req_number, r.env,
                    p.cn AS parent_cn,
                    (SELECT COUNT(*) FROM certificates f WHERE f.parent_id = c.id) AS issued_count,
                    CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) AS days_left
             FROM certificates c
             LEFT JOIN reqs r ON r.id = c.req_id
             LEFT JOIN certificates p ON p.id = c.parent_id
             WHERE 1=1"""
    params = []
    if search:
        sql += " AND (c.cn LIKE ? OR c.sans LIKE ? OR c.issuer LIKE ? OR r.req_number LIKE ?)"
        params += [f"%{search}%"] * 4
    if expiring_days is not None:
        sql += " AND julianday(c.not_after) - julianday('now','localtime') <= ?"
        params.append(expiring_days)
    if cert_type:
        sql += " AND c.cert_type = ?"
        params.append(cert_type)
    if issuer_cn:
        sql += " AND c.issuer_cn = ?"
        params.append(issuer_cn)
    if lifecycle:
        sql += " AND c.lifecycle_status = ?"
        params.append(lifecycle)
    sql += " ORDER BY c.not_after ASC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    issuers = [r[0] for r in conn.execute(
        """SELECT DISTINCT issuer_cn FROM certificates
           WHERE issuer_cn <> '' ORDER BY issuer_cn""").fetchall()]
    conn.close()
    return {"certs": rows, "issuers": issuers}


@router.post("/certs/relink")
def relink_certs():
    """Recalcula issuer_cn e os vínculos de cadeia de todos os certificados."""
    conn = get_db()
    rows = conn.execute("SELECT id, subject, issuer FROM certificates").fetchall()
    by_subject = {}
    for r in rows:
        by_subject.setdefault(r["subject"], r["id"])
    linked = 0
    for r in rows:
        conn.execute("UPDATE certificates SET issuer_cn=? WHERE id=?",
                     (_issuer_cn_from_dn(r["issuer"]), r["id"]))
        parent_id = by_subject.get(r["issuer"])
        if parent_id and parent_id != r["id"]:
            conn.execute("UPDATE certificates SET parent_id=? WHERE id=?",
                         (parent_id, r["id"]))
            linked += 1
        elif r["issuer"] == r["subject"]:
            conn.execute("UPDATE certificates SET parent_id=NULL WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()
    return {"total": len(rows), "linked": linked}


@router.post("/certs/import")
async def import_cert(file: UploadFile = File(...), password: str = Form(""),
                      req_id: int | None = Form(None)):
    data = await file.read()
    try:
        info = certparse.parse_certificate(data, file.filename or "", password or None)
    except ValueError as e:
        raise HTTPException(400, str(e))

    conn = get_db()
    file_path = ""
    req = None
    if req_id:
        req = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not req:
            conn.close()
            raise HTTPException(404, "Demanda não encontrada")

    # salva o arquivo: na pasta cert/ da REQ, ou em data/files/certs/
    base = get_setting(conn, "base_dir")
    if req:
        template = get_setting(conn, "folder_template")
        folder = folders.create_structure(base, template, req["req_number"], req["cn"], req["env"]) / "cert"
    else:
        folder = Path(base) / "certs"
        folder.mkdir(parents=True, exist_ok=True)
    safe_name = folders.sanitize(Path(file.filename or "certificado").name)
    dest = folder / safe_name
    dest.write_bytes(data)
    file_path = str(dest)

    now = datetime.now()
    try:
        not_after_dt = datetime.fromisoformat(info['not_after'].replace('Z', '+00:00'))
        if not_after_dt.replace(tzinfo=None) < now:
            lifecycle = 'fim_de_vida'
        else:
            lifecycle = 'em_inventario'
    except Exception:
        lifecycle = 'em_inventario'
        
    if lifecycle != 'fim_de_vida' and req_id:
        has_install = conn.execute("SELECT 1 FROM install_locations WHERE req_id=?", (req_id,)).fetchone()
        if has_install:
            lifecycle = 'instalado'

    cur = conn.execute(
        """INSERT INTO certificates
           (req_id, cn, sans, subject, issuer, issuer_cn, cert_type, serial,
            thumbprint_sha1, not_before, not_after, key_type, source, file_path, lifecycle_status)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (req_id, info["cn"], info["sans"], info["subject"], info["issuer"],
         info["issuer_cn"], info["cert_type"], info["serial"],
         info["thumbprint_sha1"], info["not_before"],
         info["not_after"], info["key_type"], "importado", file_path, lifecycle),
    )
    cert_id = cur.lastrowid
    _link_parent(conn, cert_id, info["issuer"], info["subject"])
    log_activity(conn, "cert_importado",
                 f"{info['cn']} · vence {info['not_after'][:10]}", req_id)
    if req:
        conn.execute("UPDATE reqs SET status='cert_emitido', "
                     "updated_at=datetime('now','localtime') WHERE id=? AND status IN ('aberta','csr_gerada')",
                     (req_id,))
    conn.commit()
    row = dict(conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone())
    conn.close()
    return row


@router.put("/certs/{cert_id}")
def update_cert(cert_id: int, body: CertUpdate):
    fields = body.model_dump(exclude_unset=True)
    if "cert_type" in fields and fields["cert_type"] not in CERT_TYPES + [""]:
        raise HTTPException(400, f"Tipo inválido. Use: {', '.join(CERT_TYPES)} ou vazio")
    if "lifecycle_status" in fields and fields["lifecycle_status"] not in LIFECYCLE_STATUSES:
        raise HTTPException(400, f"Status inválido. Use: {LIFECYCLE_STATUSES}")
        
    conn = get_db()
    if not conn.execute("SELECT id FROM certificates WHERE id=?", (cert_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE certificates SET {sets} WHERE id=?",
                     (*fields.values(), cert_id))
        if "req_id" in fields:
            log_activity(conn, "cert_vinculado", f"Certificado #{cert_id} vinculado",
                         fields["req_id"])
        conn.commit()
    conn.close()
    return {"ok": True}

class LifecycleUpdate(BaseModel):
    lifecycle_status: str

@router.put('/certs/{cert_id}/lifecycle')
def update_lifecycle(cert_id: int, body: LifecycleUpdate):
    if body.lifecycle_status not in LIFECYCLE_STATUSES:
        raise HTTPException(400, f'Status inválido. Use: {LIFECYCLE_STATUSES}')
    conn = get_db()
    if not conn.execute('SELECT id FROM certificates WHERE id=?', (cert_id,)).fetchone():
        conn.close()
        raise HTTPException(404, 'Certificado não encontrado')
    conn.execute(
        "UPDATE certificates SET lifecycle_status=? WHERE id=?",
        (body.lifecycle_status, cert_id)
    )
    log_activity(conn, 'lifecycle_alterado', f'{body.lifecycle_status}', None)
    conn.commit()
    conn.close()
    return {'ok': True, 'lifecycle_status': body.lifecycle_status}


@router.delete("/certs/{cert_id}")
def delete_cert(cert_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    conn.execute("DELETE FROM certificates WHERE id=?", (cert_id,))
    log_activity(conn, "cert_removido", row["cn"] or "", row["req_id"])
    conn.commit()
    conn.close()
    return {"ok": True}
