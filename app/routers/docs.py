"""Manuais e comandos úteis (markdown editável)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..db import get_db, log_activity
from .auth import require_auth

router = APIRouter(tags=["docs"])

CATEGORIES = ["manual", "certutil", "certreq", "openssl", "keytool", "outros"]


class DocIn(BaseModel):
    title: str
    category: str = "outros"
    content_md: str = ""


@router.get("/docs")
def list_docs():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT id, title, category, updated_at FROM docs ORDER BY category, title")]
    conn.close()
    return rows


@router.get("/docs/{doc_id}")
def get_doc(doc_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM docs WHERE id=?", (doc_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Documento não encontrado")
    return dict(row)


@router.post("/docs")
def create_doc(body: DocIn, user=Depends(require_auth)):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO docs (title, category, content_md) VALUES (?,?,?)",
        (body.title, body.category if body.category in CATEGORIES else "outros", body.content_md))
    log_activity(conn, "doc_criado", body.title, None, user["id"])
    conn.commit()
    row = dict(conn.execute("SELECT * FROM docs WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.put("/docs/{doc_id}")
def update_doc(doc_id: int, body: DocIn, user=Depends(require_auth)):
    conn = get_db()
    if not conn.execute("SELECT id FROM docs WHERE id=?", (doc_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Documento não encontrado")
    conn.execute(
        "UPDATE docs SET title=?, category=?, content_md=?, updated_at=datetime('now','localtime') WHERE id=?",
        (body.title, body.category if body.category in CATEGORIES else "outros",
         body.content_md, doc_id))
    log_activity(conn, "doc_editado", body.title, None, user["id"])
    conn.commit()
    row = dict(conn.execute("SELECT * FROM docs WHERE id=?", (doc_id,)).fetchone())
    conn.close()
    return row


@router.delete("/docs/{doc_id}")
def delete_doc(doc_id: int, user=Depends(require_auth)):
    conn = get_db()
    row = conn.execute("SELECT title FROM docs WHERE id=?", (doc_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Documento não encontrado")
    conn.execute("DELETE FROM docs WHERE id=?", (doc_id,))
    log_activity(conn, "doc_excluido", row["title"], None, user["id"])
    conn.commit()
    conn.close()
    return {"ok": True}
