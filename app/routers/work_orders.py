"""Work Orders e Change Requests."""
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import WO_TYPES, WO_STATUSES, get_db, log_activity

router = APIRouter(tags=["work_orders"])

WO_FORMAT = re.compile(r"^(WO|CRQ)\d+$", re.IGNORECASE)

class WorkOrderIn(BaseModel):
    wo_number: str
    wo_type: str = 'WO'
    req_id: int | None = None
    parent_req_id: int | None = None
    title: str = ''
    description: str = ''
    status: str = 'aberta'
    scheduled_at: str | None = None
    assigned_to: int | None = None
    external_number: str = ''

class WorkOrderUpdate(BaseModel):
    wo_number: str | None = None
    wo_type: str | None = None
    title: str | None = None
    description: str | None = None
    status: str | None = None
    scheduled_at: str | None = None
    completed_at: str | None = None
    assigned_to: int | None = None
    external_number: str | None = None

@router.get("/work-orders")
def list_work_orders(req_id: int | None = None, status: str = "", wo_type: str = ""):
    conn = get_db()
    sql = """
        SELECT w.*, r.req_number, r.cn, r.env, u.display_name,
               (SELECT COUNT(*) FROM wo_tasks WHERE wo_id=w.id) as task_count, (SELECT COUNT(*) FROM wo_tasks WHERE wo_id=w.id AND status='concluida') as tasks_done
        FROM work_orders w
        LEFT JOIN reqs r ON r.id = w.parent_req_id
        LEFT JOIN users u ON u.id = w.assigned_to
        WHERE 1=1
    """
    params = []
    if req_id is not None:
        sql += " AND w.parent_req_id = ?"
        params.append(req_id)
    if status:
        sql += " AND w.status = ?"
        params.append(status)
    if wo_type:
        sql += " AND w.wo_type = ?"
        params.append(wo_type)
    sql += " ORDER BY w.created_at DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows

@router.post("/work-orders")
def create_work_order(body: WorkOrderIn):
    wo_number = body.wo_number.strip().upper()
    if not WO_FORMAT.match(wo_number):
        raise HTTPException(400, "Número inválido — formato esperado: WO ou CRQ seguido de dígitos")
    if body.wo_type not in WO_TYPES:
        raise HTTPException(400, f"Tipo inválido. Use: {', '.join(WO_TYPES)}")
    if body.status not in WO_STATUSES:
        raise HTTPException(400, f"Status inválido. Use: {', '.join(WO_STATUSES)}")

    conn = get_db()
    try:
        cur = conn.execute(
            """INSERT INTO work_orders
               (wo_number, wo_type, req_id, parent_req_id, title, description, status, scheduled_at, assigned_to, external_number)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (wo_number, body.wo_type, body.req_id, body.parent_req_id, body.title, body.description, body.status, body.scheduled_at, body.assigned_to, body.external_number)
        )
    except Exception as e:
        conn.close()
        raise HTTPException(409, f"Já existe uma Work Order com número {wo_number}.")
    
    wo_id = cur.lastrowid
    
    DEFAULT_TASKS = [
        ('preparo', 'Preparação da instalação'),
        ('ativacao', 'Ativação / execução da mudança'),
        ('validacao', 'Validação pós-instalação'),
        ('retorno', 'Plano de retorno (rollback)'),
    ]
    for task_type, title in DEFAULT_TASKS:
        conn.execute(
            "INSERT INTO wo_tasks (wo_id, task_type, title) VALUES (?,?,?)",
            (wo_id, task_type, title)
        )
        
    conn.commit()
    row = dict(conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone())
    conn.close()
    return row

@router.get("/work-orders/{wo_id}")
def get_work_order(wo_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Work Order não encontrada")
    wo = dict(row)
    wo['tasks'] = [dict(t) for t in conn.execute(
        "SELECT * FROM wo_tasks WHERE wo_id=? ORDER BY id", (wo_id,)
    ).fetchall()]
    conn.close()
    return wo

@router.put("/work-orders/{wo_id}")
def update_work_order(wo_id: int, body: WorkOrderUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Work Order não encontrada")
    
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    
    if "wo_number" in fields:
        fields["wo_number"] = fields["wo_number"].strip().upper()
        if not WO_FORMAT.match(fields["wo_number"]):
            conn.close()
            raise HTTPException(400, "Número inválido — formato esperado: WO ou CRQ seguido de dígitos")
    if "wo_type" in fields and fields["wo_type"] not in WO_TYPES:
        conn.close()
        raise HTTPException(400, f"Tipo inválido. Use: {', '.join(WO_TYPES)}")
    if "status" in fields:
        if fields["status"] not in WO_STATUSES:
            conn.close()
            raise HTTPException(400, f"Status inválido. Use: {', '.join(WO_STATUSES)}")
        if fields["status"] == 'concluida' and row["status"] != 'concluida' and "completed_at" not in fields:
            fields["completed_at"] = conn.execute("SELECT datetime('now','localtime')").fetchone()[0]

    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        try:
            conn.execute(
                f"UPDATE work_orders SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
                (*fields.values(), wo_id),
            )
        except Exception:
            conn.close()
            raise HTTPException(409, "Erro ao atualizar Work Order (número duplicado?).")
        conn.commit()
    
    updated = dict(conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone())
    conn.close()
    return updated

@router.delete("/work-orders/{wo_id}")
def delete_work_order(wo_id: int):
    conn = get_db()
    row = conn.execute("SELECT wo_number FROM work_orders WHERE id=?", (wo_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Work Order não encontrada")
    conn.execute("DELETE FROM work_orders WHERE id=?", (wo_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

@router.post("/reqs/{req_id}/create-installation-wo")
def create_installation_wo(req_id: int):
    conn = get_db()
    req = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not req:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    
    # Check if a WO already exists for this REQ as parent
    existing_wo = conn.execute("SELECT id FROM work_orders WHERE parent_req_id=?", (req_id,)).fetchone()
    if existing_wo:
        conn.close()
        raise HTTPException(400, "Já existe uma WO de instalação para esta demanda.")
    
    is_prd = (req["env"] == 'PRD')
    wo_type = 'CRQ' if is_prd else 'WO'
    title = f"Instalação de {req['cn']} em {req['env']}"
    
    # Gerar um numero de WO/CRQ temporario ou placeholder
    # Na vida real pode vir de integracao
    count = conn.execute("SELECT COUNT(*) FROM work_orders").fetchone()[0]
    wo_number = f"{wo_type}{count+1000}"

    try:
        cur = conn.execute(
            """INSERT INTO work_orders
               (wo_number, wo_type, parent_req_id, title)
               VALUES (?,?,?,?)""",
            (wo_number, wo_type, req_id, title)
        )
        wo_id = cur.lastrowid
        log_activity(conn, "wo_criada", f"{wo_type} sugerida para instalação", req_id)
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(500, f"Erro ao criar WO: {e}")

    wo = dict(conn.execute("SELECT * FROM work_orders WHERE id=?", (wo_id,)).fetchone())
    wo["suggested_type"] = wo_type
    wo["is_prd"] = is_prd
    conn.close()
    return wo

class WOTaskIn(BaseModel):
    task_type: str = 'custom'
    title: str = ''
    notes: str = ''

class WOTaskUpdate(BaseModel):
    title: str | None = None
    notes: str | None = None
    status: str | None = None

@router.post("/work-orders/{wo_id}/tasks")
def create_wo_task(wo_id: int, body: WOTaskIn):
    conn = get_db()
    wo = conn.execute("SELECT id FROM work_orders WHERE id=?", (wo_id,)).fetchone()
    if not wo:
        conn.close()
        raise HTTPException(404, "Work Order não encontrada")
    cur = conn.execute(
        "INSERT INTO wo_tasks (wo_id, task_type, title, notes) VALUES (?,?,?,?)",
        (wo_id, body.task_type, body.title, body.notes)
    )
    conn.commit()
    task = dict(conn.execute("SELECT * FROM wo_tasks WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return task

@router.put("/work-orders/tasks/{task_id}")
def update_wo_task(task_id: int, body: WOTaskUpdate):
    conn = get_db()
    task = conn.execute("SELECT * FROM wo_tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        raise HTTPException(404, "Tarefa não encontrada")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if 'status' in fields and fields['status'] not in ('pendente', 'concluida', 'cancelada'):
        conn.close()
        raise HTTPException(400, "Status inválido")
    if 'status' in fields and fields['status'] == 'concluida':
        fields['completed_at'] = conn.execute("SELECT datetime('now','localtime')").fetchone()[0]
    if fields:
        sets = ', '.join(f"{k}=?" for k in fields)
        conn.execute(f"UPDATE wo_tasks SET {sets} WHERE id=?", (*fields.values(), task_id))
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM wo_tasks WHERE id=?", (task_id,)).fetchone())
    conn.close()
    return updated

@router.delete("/work-orders/tasks/{task_id}")
def delete_wo_task(task_id: int):
    conn = get_db()
    task = conn.execute("SELECT * FROM wo_tasks WHERE id=?", (task_id,)).fetchone()
    if not task:
        conn.close()
        raise HTTPException(404, "Tarefa não encontrada")
    conn.execute("DELETE FROM wo_tasks WHERE id=?", (task_id,))
    conn.commit()
    conn.close()
    return {"ok": True}
