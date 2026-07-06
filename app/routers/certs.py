"""Certificados: importação com parsing automático, listagem e vínculo com REQ."""
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import get_db, get_setting, log_activity
from ..services import certparse, folders

router = APIRouter(tags=["certs"])


class CertUpdate(BaseModel):
    req_id: int | None = None


@router.get("/certs")
def list_certs(search: str = "", expiring_days: int | None = None):
    conn = get_db()
    sql = """SELECT c.*, r.req_number, r.env,
                    CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) AS days_left
             FROM certificates c LEFT JOIN reqs r ON r.id = c.req_id WHERE 1=1"""
    params = []
    if search:
        sql += " AND (c.cn LIKE ? OR c.sans LIKE ? OR c.issuer LIKE ? OR r.req_number LIKE ?)"
        params += [f"%{search}%"] * 4
    if expiring_days is not None:
        sql += " AND julianday(c.not_after) - julianday('now','localtime') <= ?"
        params.append(expiring_days)
    sql += " ORDER BY c.not_after ASC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


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

    cur = conn.execute(
        """INSERT INTO certificates
           (req_id, cn, sans, subject, issuer, serial, thumbprint_sha1,
            not_before, not_after, key_type, source, file_path)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (req_id, info["cn"], info["sans"], info["subject"], info["issuer"],
         info["serial"], info["thumbprint_sha1"], info["not_before"],
         info["not_after"], info["key_type"], "importado", file_path),
    )
    cert_id = cur.lastrowid
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
    conn = get_db()
    if not conn.execute("SELECT id FROM certificates WHERE id=?", (cert_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    conn.execute("UPDATE certificates SET req_id=? WHERE id=?", (body.req_id, cert_id))
    log_activity(conn, "cert_vinculado", f"Certificado #{cert_id} vinculado", body.req_id)
    conn.commit()
    conn.close()
    return {"ok": True}


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
