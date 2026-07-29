"""Templates de resposta: textos prontos com placeholders preenchidos pelos dados da REQ."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_db

router = APIRouter(tags=["templates"])


class TemplateIn(BaseModel):
    name: str
    content: str = ""


@router.get("/templates")
def list_templates():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM reply_templates ORDER BY name").fetchall()]
    conn.close()
    return rows


@router.post("/templates")
def create_template(body: TemplateIn):
    if not body.name.strip():
        raise HTTPException(400, "Informe o nome do template")
    conn = get_db()
    cur = conn.execute("INSERT INTO reply_templates (name, content) VALUES (?,?)",
                       (body.name.strip(), body.content))
    conn.commit()
    row = dict(conn.execute("SELECT * FROM reply_templates WHERE id=?",
                            (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.put("/templates/{tpl_id}")
def update_template(tpl_id: int, body: TemplateIn):
    if not body.name.strip():
        raise HTTPException(400, "Informe o nome do template")
    conn = get_db()
    if not conn.execute("SELECT id FROM reply_templates WHERE id=?", (tpl_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Template não encontrado")
    conn.execute(
        "UPDATE reply_templates SET name=?, content=?, updated_at=datetime('now','localtime') "
        "WHERE id=?", (body.name.strip(), body.content, tpl_id))
    conn.commit()
    row = dict(conn.execute("SELECT * FROM reply_templates WHERE id=?", (tpl_id,)).fetchone())
    conn.close()
    return row


@router.delete("/templates/{tpl_id}")
def delete_template(tpl_id: int):
    conn = get_db()
    if not conn.execute("SELECT id FROM reply_templates WHERE id=?", (tpl_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Template não encontrado")
    conn.execute("DELETE FROM reply_templates WHERE id=?", (tpl_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
