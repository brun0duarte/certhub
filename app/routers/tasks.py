"""Kanban de tarefas: CRUD, prioridades e movimentação entre colunas."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import TASK_LANES, TASK_PRIORITIES, get_db, log_activity

router = APIRouter(tags=["tasks"])

PRIORITY_ORDER = "CASE priority WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END"


class TaskIn(BaseModel):
    title: str
    description: str = ""
    category: str = "geral"
    priority: str = "media"
    lane: str = "backlog"


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    priority: str | None = None
    lane: str | None = None


class TaskMove(BaseModel):
    lane: str


def _validate(priority: str | None = None, lane: str | None = None):
    if priority is not None and priority not in TASK_PRIORITIES:
        raise HTTPException(400, f"Prioridade inválida. Use: {', '.join(TASK_PRIORITIES)}")
    if lane is not None and lane not in TASK_LANES:
        raise HTTPException(400, f"Coluna inválida. Use: {', '.join(TASK_LANES)}")


def _next_position(conn, lane: str) -> int:
    row = conn.execute("SELECT COALESCE(MAX(position), 0) + 1 FROM tasks WHERE lane=?", (lane,))
    return row.fetchone()[0]


@router.get("/tasks")
def list_tasks(category: str = ""):
    conn = get_db()
    sql = "SELECT * FROM tasks"
    params = []
    if category:
        sql += " WHERE category = ?"
        params.append(category)
    sql += f" ORDER BY {PRIORITY_ORDER}, position, id"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    categories = [r[0] for r in conn.execute(
        "SELECT DISTINCT category FROM tasks ORDER BY category").fetchall()]
    conn.close()
    return {"tasks": rows, "categories": categories}


@router.post("/tasks")
def create_task(body: TaskIn):
    if not body.title.strip():
        raise HTTPException(400, "Informe o título da tarefa")
    _validate(body.priority, body.lane)
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO tasks (title, description, category, priority, lane, position) "
        "VALUES (?,?,?,?,?,?)",
        (body.title.strip(), body.description, body.category.strip().lower() or "geral",
         body.priority, body.lane, _next_position(conn, body.lane)),
    )
    log_activity(conn, "tarefa_criada", f"{body.title.strip()} · {body.priority}")
    conn.commit()
    row = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.put("/tasks/{task_id}")
def update_task(task_id: int, body: TaskUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Tarefa não encontrada")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        _validate(fields.get("priority"), fields.get("lane"))
    except HTTPException:
        conn.close()
        raise
    if "category" in fields:
        fields["category"] = fields["category"].strip().lower() or "geral"
    if "lane" in fields and fields["lane"] != row["lane"]:
        fields["position"] = _next_position(conn, fields["lane"])
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE tasks SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
            (*fields.values(), task_id),
        )
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return updated


@router.post("/tasks/{task_id}/move")
def move_task(task_id: int, body: TaskMove):
    _validate(lane=body.lane)
    conn = get_db()
    row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Tarefa não encontrada")
    if body.lane != row["lane"]:
        conn.execute(
            "UPDATE tasks SET lane=?, position=?, updated_at=datetime('now','localtime') "
            "WHERE id=?",
            (body.lane, _next_position(conn, body.lane), task_id),
        )
        log_activity(conn, "tarefa_movida", f"{row['title']}: {row['lane']} → {body.lane}")
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return updated


@router.delete("/tasks/{task_id}")
def delete_task(task_id: int):
    conn = get_db()
    row = conn.execute("SELECT title FROM tasks WHERE id=?", (task_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Tarefa não encontrada")
    conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
    log_activity(conn, "tarefa_excluida", row["title"])
    conn.commit()
    conn.close()
    return {"ok": True}
