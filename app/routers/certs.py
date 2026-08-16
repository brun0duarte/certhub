"""Certificados: importação com parsing automático, listagem, tipos e cadeia."""
import re
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from ..db import CERT_TYPES, get_db, get_setting, log_activity, LIFECYCLE_STATUSES
from ..services import certparse, folders
from .auth import require_auth


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
               cert_type: str = "", issuer_cn: str = "", lifecycle: str = "", env: str = "",
               page: int = 1, page_size: int = 50):
    conn = get_db()
    where = """FROM certificates c
             LEFT JOIN reqs r ON r.id = c.req_id
             LEFT JOIN certificates p ON p.id = c.parent_id
             WHERE 1=1"""
    params = []
    if search:
        where += " AND (c.cn LIKE ? OR c.sans LIKE ? OR c.issuer LIKE ? OR r.req_number LIKE ?)"
        params += [f"%{search}%"] * 4
    if expiring_days is not None:
        where += " AND julianday(c.not_after) - julianday('now','localtime') <= ?"
        params.append(expiring_days)
    if cert_type:
        where += " AND c.cert_type = ?"
        params.append(cert_type)
    if issuer_cn:
        where += " AND c.issuer_cn = ?"
        params.append(issuer_cn)
    if lifecycle:
        where += " AND c.lifecycle_status = ?"
        params.append(lifecycle)
    if env:
        where += " AND r.env = ?"
        params.append(env)
    total = conn.execute("SELECT COUNT(*) " + where, params).fetchone()[0]
    sql = ("""SELECT c.*, r.req_number, r.env,
                     p.cn AS parent_cn,
                     (SELECT COUNT(*) FROM certificates f WHERE f.parent_id = c.id) AS issued_count,
                     CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) AS days_left
              """ + where + " ORDER BY c.not_after ASC LIMIT ? OFFSET ?")
    page = max(page, 1)
    rows = [dict(r) for r in conn.execute(
        sql, params + [min(page_size, 1000), (page - 1) * page_size]).fetchall()]
    issuers = [r[0] for r in conn.execute(
        """SELECT DISTINCT issuer_cn FROM certificates
           WHERE issuer_cn <> '' ORDER BY issuer_cn""").fetchall()]
    conn.close()
    return {"certs": rows, "issuers": issuers, "total": total}


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
                      req_id: int | None = Form(None),
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
        info = certparse.parse_certificate(data, filename, password or None)
    except ValueError as e:
        raise HTTPException(400, str(e))

    conn = get_db()
    req = None
    if req_id:
        req = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not req:
            conn.close()
            raise HTTPException(404, "Demanda não encontrada")

    existing = conn.execute(
        "SELECT * FROM certificates WHERE thumbprint_sha1=?", (info["thumbprint_sha1"],)
    ).fetchone()

    if existing:
        cert_id = existing["id"]
        already_imported = True
        if req_id and existing["req_id"] != req_id:
            conn.execute("UPDATE certificates SET req_id=? WHERE id=?", (req_id, cert_id))
    else:
        already_imported = False
        # salva o arquivo: na pasta cert/ da REQ, ou em data/files/certs/
        base = get_setting(conn, "base_dir")
        if req:
            template = get_setting(conn, "folder_template")
            folder = folders.create_structure(base, template, req["req_number"], req["cn"], req["env"]) / "cert"
        else:
            folder = Path(base) / "certs"
            folder.mkdir(parents=True, exist_ok=True)
        safe_name = folders.sanitize(Path(filename or "certificado.crt").name)

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

    log_activity(conn, "cert_relinkado" if already_imported else "cert_importado",
                 f"{info['cn']} · vence {info['not_after'][:10]}", req_id, user["id"])
    if req:
        conn.execute("UPDATE reqs SET status='cert_emitido', "
                     "updated_at=datetime('now','localtime') WHERE id=? AND status IN ('aberta','csr_gerada')",
                     (req_id,))

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

    # Confere se a chave pública do certificado corresponde à CSR gerada nesta demanda
    csr_match = None
    if req_id:
        csr_row = conn.execute("SELECT csr_pem FROM reqs WHERE id=?", (req_id,)).fetchone()
        csr_pem = csr_row["csr_pem"] if csr_row and csr_row["csr_pem"] else None
        if not csr_pem:
            c_row = conn.execute("SELECT pem FROM csrs WHERE req_id=? ORDER BY id DESC LIMIT 1", (req_id,)).fetchone()
            csr_pem = c_row["pem"] if c_row else None

        if csr_pem:
            try:
                cert_obj = certparse._load_x509(data)
                csr_obj = x509.load_pem_x509_csr(csr_pem.encode())
                cert_pub = cert_obj.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
                csr_pub = csr_obj.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
                csr_match = (cert_pub == csr_pub)
            except Exception:
                csr_match = None

    row = dict(conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone())
    row["chain_found"] = chain_found
    row["issuer_name"] = issuer_cn or issuer_dn or "Desconhecido"
    row["chain_ca"] = dict(ca_row) if ca_row else None
    row["csr_match"] = csr_match
    row["already_imported"] = already_imported
    conn.commit()
    conn.close()
    return row




@router.put("/certs/{cert_id}")
def update_cert(cert_id: int, body: CertUpdate, user=Depends(require_auth)):
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
                         fields["req_id"], user["id"])
        other_fields = [k for k in fields if k != "req_id"]
        if other_fields:
            row = conn.execute("SELECT req_id FROM certificates WHERE id=?", (cert_id,)).fetchone()
            log_activity(conn, "cert_editado", f"Campos alterados: {', '.join(other_fields)}",
                         row["req_id"], user["id"])
        conn.commit()
    conn.close()
    return {"ok": True}

class LifecycleUpdate(BaseModel):
    lifecycle_status: str

@router.put('/certs/{cert_id}/lifecycle')
def update_lifecycle(cert_id: int, body: LifecycleUpdate, user=Depends(require_auth)):
    if body.lifecycle_status not in LIFECYCLE_STATUSES:
        raise HTTPException(400, f'Status inválido. Use: {LIFECYCLE_STATUSES}')
    conn = get_db()
    row = conn.execute('SELECT req_id FROM certificates WHERE id=?', (cert_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, 'Certificado não encontrado')
    conn.execute(
        "UPDATE certificates SET lifecycle_status=? WHERE id=?",
        (body.lifecycle_status, cert_id)
    )
    log_activity(conn, 'lifecycle_alterado', f'{body.lifecycle_status}', row["req_id"], user["id"])
    conn.commit()
    conn.close()
    return {'ok': True, 'lifecycle_status': body.lifecycle_status}


@router.delete("/certs/{cert_id}")
def delete_cert(cert_id: int, user=Depends(require_auth)):
    conn = get_db()
    row = conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    conn.execute("DELETE FROM certificates WHERE id=?", (cert_id,))
    log_activity(conn, "cert_removido", row["cn"] or "", row["req_id"], user["id"])
    conn.commit()
    conn.close()
    return {"ok": True}

def _load_cert_object(row):
    """Relê o arquivo salvo na importação (ou o PEM guardado no banco, pra certificados
    importados via HSM — que não têm arquivo local) e devolve o objeto x509.Certificate
    carregado. Lança HTTPException se não houver arquivo nem PEM, o arquivo não existir em
    disco, ou não for legível sem senha."""
    if not row["file_path"]:
        cert_pem = row["cert_pem"] if "cert_pem" in row.keys() else None
        if not cert_pem:
            raise HTTPException(404, "Este certificado não tem arquivo salvo (ex.: CA cadastrada manualmente).")
        return certparse._load_x509(cert_pem.encode())
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(404, "Arquivo do certificado não foi encontrado em disco.")
    data = path.read_bytes()
    try:
        return certparse._load_x509(data)
    except ValueError:
        try:
            _key, cert, _extra = pkcs12.load_key_and_certificates(data, None)
            if cert is None:
                raise ValueError
            return cert
        except Exception:
            raise HTTPException(400,
                "Não consegui ler o certificado salvo (PFX protegido por senha ou formato não "
                "reconhecido) — use o Decoder para abrir o arquivo original com a senha.")


def _read_cert_pem(row) -> str:
    """Devolve o PEM normalizado do certificado salvo na importação."""
    cert = _load_cert_object(row)
    return cert.public_bytes(serialization.Encoding.PEM).decode()


@router.get("/certs/{cert_id}/pem")
def get_cert_pem(cert_id: int):
    """Recupera o PEM normalizado do certificado a partir do arquivo salvo na importação."""
    conn = get_db()
    row = conn.execute("SELECT file_path, cert_pem, cn FROM certificates WHERE id=?", (cert_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Certificado não encontrado")
    return {"pem": _read_cert_pem(row)}


@router.get("/certs/{cert_id}/full")
def get_cert_full(cert_id: int):
    """Dados estendidos do X.509 (versão, signature algorithm, SHA256, Key Usage, EKU, etc.)
    pra exibição de detalhe — não persistidos em banco, extraídos sob demanda do arquivo."""
    conn = get_db()
    row = conn.execute("SELECT file_path, cert_pem, cn FROM certificates WHERE id=?", (cert_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Certificado não encontrado")
    cert = _load_cert_object(row)
    return certparse.extract_extended(cert)


def _walk_chain(conn, cert_id: int) -> list[dict]:
    """Sobe a cadeia via parent_id (folha → ... → raiz), até faltar link ou detectar ciclo."""
    chain = []
    seen = set()
    row = conn.execute("SELECT * FROM certificates WHERE id=?", (cert_id,)).fetchone()
    while row and row["id"] not in seen:
        seen.add(row["id"])
        chain.append(dict(row))
        if not row["parent_id"]:
            break
        row = conn.execute("SELECT * FROM certificates WHERE id=?", (row["parent_id"],)).fetchone()
    return chain


@router.get("/certs/{cert_id}/chain")
def get_cert_chain(cert_id: int):
    """Cadeia completa do certificado (folha → intermediárias → raiz), a partir do
    que já está vinculado via parent_id (ver /certs/relink)."""
    conn = get_db()
    if not conn.execute("SELECT 1 FROM certificates WHERE id=?", (cert_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    chain = _walk_chain(conn, cert_id)
    conn.close()
    last = chain[-1] if chain else None
    complete = bool(last) and last["issuer"] == last["subject"]
    return {"chain": chain, "complete": complete}


@router.get("/certs/{cert_id}/chain-pem")
def get_cert_chain_pem(cert_id: int):
    """Bundle PEM com toda a cadeia (folha primeiro) montado a partir dos certificados
    já em inventário — pula (e reporta) elos sem arquivo salvo ou ilegíveis."""
    conn = get_db()
    if not conn.execute("SELECT 1 FROM certificates WHERE id=?", (cert_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    chain = _walk_chain(conn, cert_id)
    conn.close()
    parts, missing = [], []
    for c in chain:
        try:
            parts.append(_read_cert_pem(c))
        except HTTPException:
            missing.append(c["cn"])
    last = chain[-1] if chain else None
    complete = bool(last) and last["issuer"] == last["subject"]
    return {"pem": "".join(parts), "count": len(parts), "missing": missing, "complete": complete}


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
        "SELECT al.*, r.req_number, u.display_name AS user_name FROM activity_log al "
        "LEFT JOIN reqs r ON r.id = al.req_id "
        "LEFT JOIN users u ON u.id = al.user_id "
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
