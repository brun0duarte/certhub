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
    ownership: str | None = None


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
async def import_cert(file: UploadFile | None = File(None),
                      pem_text: str = Form(""),
                      password: str = Form(""),
                      req_id: int | None = Form(None)):
    if pem_text and pem_text.strip():
        data = pem_text.strip().encode("utf-8")
        filename = "certificado.pem"
    elif file and file.filename:
        data = await file.read()
        filename = file.filename
    else:
        raise HTTPException(400, "Envie um arquivo de certificado ou cole o conteúdo PEM.")

    try:
        info = certparse.parse_certificate(data, filename, password or None)
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

    # Verifica se a cadeia do emissor (CA) já está cadastrada no sistema
    issuer_dn = info.get("issuer", "")
    issuer_cn = info.get("issuer_cn", "")
    ca_row = conn.execute("""
        SELECT id, cn, issuer_cn, cert_type, thumbprint_sha1 FROM certificates
        WHERE (subject=? OR cn=? OR (issuer_cn=? AND issuer_cn != ''))
          AND (cert_type='ca' OR cert_category LIKE '%ac%' OR cert_category LIKE '%ca%')
        ORDER BY id DESC LIMIT 1
    """, (issuer_dn, issuer_cn, issuer_cn)).fetchone()

    chain_found = ca_row is not None

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
    row["chain_found"] = chain_found
    row["issuer_name"] = issuer_cn or issuer_dn or "Desconhecido"
    row["chain_ca"] = dict(ca_row) if ca_row else None
    conn.close()
    return row



@router.put("/certs/{cert_id}")
def update_cert(cert_id: int, body: CertUpdate):
    fields = body.model_dump(exclude_unset=True)
    if "cert_type" in fields and fields["cert_type"] not in CERT_TYPES + [""]:
        raise HTTPException(400, f"Tipo inválido. Use: {', '.join(CERT_TYPES)} ou vazio")
    if "lifecycle_status" in fields and fields["lifecycle_status"] not in LIFECYCLE_STATUSES:
        raise HTTPException(400, f"Status inválido. Use: {LIFECYCLE_STATUSES}")
    if "ownership" in fields and fields["ownership"] not in ['interno', 'externo', '']:
        raise HTTPException(400, "ownership inválido. Use: interno, externo")
        
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

@router.get("/certs/{cert_id}/history")
def get_cert_history(cert_id: int):
    """Retorna histórico completo de um certificado."""
    conn = get_db()
    cert = conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone()
    if not cert:
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    cert = dict(cert)
    cn = cert['cn']
    
    reqs = [dict(r) for r in conn.execute(
        "SELECT * FROM reqs WHERE cn=? ORDER BY created_at DESC", (cn,)
    ).fetchall()]
    
    req_ids = [r['id'] for r in reqs]
    locations = []
    if req_ids:
        placeholders = ','.join('?' * len(req_ids))
        locations = [dict(l) for l in conn.execute(
            f"SELECT il.*, r.req_number FROM install_locations il "
            f"LEFT JOIN reqs r ON r.id = il.req_id "
            f"WHERE il.req_id IN ({placeholders}) ORDER BY il.id",
            req_ids
        ).fetchall()]
    
    activity = [dict(a) for a in conn.execute(
        "SELECT al.*, r.req_number FROM activity_log al "
        "LEFT JOIN reqs r ON r.id = al.req_id "
        "WHERE al.req_id IN (SELECT id FROM reqs WHERE cn=?) "
        "ORDER BY al.created_at DESC LIMIT 50",
        (cn,)
    ).fetchall()]
    
    related_certs = [dict(c) for c in conn.execute(
        "SELECT id, cn, not_before, not_after, serial, thumbprint_sha1, lifecycle_status, source "
        "FROM certificates WHERE cn=? ORDER BY not_after DESC",
        (cn,)
    ).fetchall()]
    
    conn.close()
    return {
        "certificate": cert,
        "reqs": reqs,
        "locations": locations,
        "activity": activity,
        "related_certs": related_certs,
    }
