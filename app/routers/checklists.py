"""Checklist de ativação (CRQ): templates de tarefas de preparação de mudança,
tarefas concretas por demanda de instalação e evidências anexadas."""
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from ..db import INSTALL_TASK_STATUSES, get_db, get_setting, log_activity
from ..services import folders

router = APIRouter(tags=["checklists"])


# ---------------- templates (administração) ----------------

DEFAULT_MESSAGE_TEMPLATE = (
    "📋 {tarefa} — {status}\n"
    "Demanda: {req} · {cn} ({env})\n"
    "Instruções: {instrucoes}\n"
    "Notas: {notas}\n"
    "Evidências: {evidencias}\n"
    "Atualizado em {data}"
)


class ChecklistTemplateIn(BaseModel):
    title: str
    instructions: str = ""
    message_template: str = ""
    position: int = 0
    active: bool = True


@router.get("/checklist-templates")
def list_checklist_templates():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM checklist_task_templates ORDER BY position, id").fetchall()]
    conn.close()
    return rows


@router.post("/checklist-templates")
def create_checklist_template(body: ChecklistTemplateIn):
    if not body.title.strip():
        raise HTTPException(400, "Informe o título da tarefa")
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO checklist_task_templates (title, instructions, message_template, position, active) "
        "VALUES (?,?,?,?,?)",
        (body.title.strip(), body.instructions, body.message_template or DEFAULT_MESSAGE_TEMPLATE,
         body.position, int(body.active)))
    conn.commit()
    row = dict(conn.execute("SELECT * FROM checklist_task_templates WHERE id=?",
                            (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.put("/checklist-templates/{tpl_id}")
def update_checklist_template(tpl_id: int, body: ChecklistTemplateIn):
    if not body.title.strip():
        raise HTTPException(400, "Informe o título da tarefa")
    conn = get_db()
    if not conn.execute("SELECT id FROM checklist_task_templates WHERE id=?", (tpl_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Modelo de tarefa não encontrado")
    conn.execute(
        "UPDATE checklist_task_templates SET title=?, instructions=?, message_template=?, position=?, "
        "active=?, updated_at=datetime('now','localtime') WHERE id=?",
        (body.title.strip(), body.instructions, body.message_template or DEFAULT_MESSAGE_TEMPLATE,
         body.position, int(body.active), tpl_id))
    conn.commit()
    row = dict(conn.execute("SELECT * FROM checklist_task_templates WHERE id=?", (tpl_id,)).fetchone())
    conn.close()
    return row


@router.delete("/checklist-templates/{tpl_id}")
def delete_checklist_template(tpl_id: int):
    conn = get_db()
    if not conn.execute("SELECT id FROM checklist_task_templates WHERE id=?", (tpl_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Modelo de tarefa não encontrado")
    conn.execute("DELETE FROM checklist_task_templates WHERE id=?", (tpl_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


# ---------------- tarefas concretas (por demanda de instalação) ----------------

class InstallTaskUpdate(BaseModel):
    status: str | None = None
    notes: str | None = None


def _task_and_req(conn, task_id: int):
    task = conn.execute("SELECT * FROM install_tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        raise HTTPException(404, "Tarefa não encontrada")
    req = conn.execute("SELECT * FROM reqs WHERE id=?", (task["req_id"],)).fetchone()
    return task, req


@router.put("/install-tasks/{task_id}")
def update_install_task(task_id: int, body: InstallTaskUpdate):
    conn = get_db()
    task, req = _task_and_req(conn, task_id)
    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
    if "status" in fields and fields["status"] not in INSTALL_TASK_STATUSES:
        conn.close()
        raise HTTPException(400, f"Status inválido. Use: {', '.join(INSTALL_TASK_STATUSES)}")
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE install_tasks SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
                     (*fields.values(), task_id))
        if "status" in fields:
            log_activity(conn, "checklist_tarefa_status",
                         f"{task['title']} → {fields['status']}", task["req_id"])
        conn.commit()
    row = dict(conn.execute("SELECT * FROM install_tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return row


def _evidence_folder(conn, req, task_id: int) -> Path:
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"])
    dest = folder / "evidencias" / str(task_id)
    dest.mkdir(parents=True, exist_ok=True)
    return dest


@router.post("/install-tasks/{task_id}/evidence")
async def upload_evidence(task_id: int, file: UploadFile = File(...)):
    conn = get_db()
    task, req = _task_and_req(conn, task_id)
    dest_folder = _evidence_folder(conn, req, task_id)
    safe_name = folders.sanitize(Path(file.filename or "evidencia").name)
    dest = dest_folder / safe_name
    dest.write_bytes(await file.read())
    cur = conn.execute(
        "INSERT INTO install_task_evidence (task_id, filename, file_path) VALUES (?,?,?)",
        (task_id, safe_name, str(dest)))
    log_activity(conn, "checklist_evidencia_anexada", f"{task['title']} · {safe_name}", task["req_id"])
    conn.commit()
    row = dict(conn.execute("SELECT * FROM install_task_evidence WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.get("/install-tasks/{task_id}/evidence/{evidence_id}")
def download_evidence(task_id: int, evidence_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM install_task_evidence WHERE id=? AND task_id=?",
                       (evidence_id, task_id)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Evidência não encontrada")
    path = Path(row["file_path"])
    if not path.exists():
        raise HTTPException(404, "Arquivo não encontrado no disco")
    return FileResponse(path, filename=row["filename"])


@router.delete("/install-tasks/{task_id}/evidence/{evidence_id}")
def delete_evidence(task_id: int, evidence_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM install_task_evidence WHERE id=? AND task_id=?",
                       (evidence_id, task_id)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Evidência não encontrada")
    conn.execute("DELETE FROM install_task_evidence WHERE id=?", (evidence_id,))
    conn.commit()
    conn.close()
    path = Path(row["file_path"])
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass
    return {"ok": True}
