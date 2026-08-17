"""Monitor de vencimentos de certificados."""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db import get_db, log_activity, LIFECYCLE_STATUSES
from app.routers.auth import require_auth

router = APIRouter(prefix="/monitor", tags=["monitor"])

SORT_COLUMNS = {
    "cn": "c.cn",
    "days_left": "days_left",
    "env": "r.env",
    "lifecycle": "c.lifecycle_status",
    "not_after": "c.not_after",
}

@router.get("/expiring")
def get_expiring_certs(
    days: int = Query(90, ge=0),
    pending_only: bool = False,
    search: str = "",
    ownership: str = "",
    sort: str = "not_after",
    dir: str = "asc",
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
):
    """Lista certificados próximos do vencimento."""
    conn = get_db()
    conditions = [
        "c.lifecycle_status IN ('instalado', 'em_inventario', 'reservado')",
        "(julianday(c.not_after) - julianday('now','localtime') <= ? OR julianday(c.not_after) < julianday('now','localtime'))",
    ]
    params = [days]
    if pending_only:
        conditions.append("active_req.id IS NULL")
    if search:
        conditions.append("(c.cn LIKE ? OR c.sans LIKE ? OR r.req_number LIKE ?)")
        params.extend([f"%{search}%"] * 3)
    if ownership:
        conditions.append("c.ownership = ?")
        params.append(ownership)

    where = "WHERE " + " AND ".join(conditions)

    sort_col = SORT_COLUMNS.get(sort, SORT_COLUMNS["not_after"])
    sort_dir = "DESC" if dir.lower() == "desc" else "ASC"

    joins = """
        FROM certificates c
        LEFT JOIN reqs r ON c.req_id = r.id
        LEFT JOIN reqs active_req ON active_req.cn = c.cn
            AND active_req.demand_type IN ('geracao','recebimento')
            AND active_req.status NOT IN ('concluida','cancelada')
    """

    total = conn.execute(f"SELECT COUNT(*) {joins} {where}", params).fetchone()[0]

    query = f"""
        SELECT c.*, r.req_number, r.env,
               CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) as days_left,
               CASE WHEN active_req.id IS NOT NULL THEN 1 ELSE 0 END as has_active_demand
        {joins}
        {where}
        ORDER BY {sort_col} {sort_dir}
        LIMIT ? OFFSET ?
    """
    rows = conn.execute(query, params + [page_size, (page - 1) * page_size]).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return {"items": result, "total": total, "page": page, "page_size": page_size}

@router.get("/lifecycle")
def get_by_lifecycle(status: str = "", search: str = ""):
    """Lista certificados filtrados por lifecycle."""
    conn = get_db()
    conditions = []
    params = []
    if status:
        conditions.append("c.lifecycle_status = ?")
        params.append(status)
    if search:
        conditions.append("(c.cn LIKE ? OR c.subject LIKE ? OR r.req_number LIKE ?)")
        params.extend([f"%{search}%"] * 3)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = conn.execute(f"""
        SELECT c.*, r.req_number, r.env,
               CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) as days_left
        FROM certificates c
        LEFT JOIN reqs r ON c.req_id = r.id
        {where}
        ORDER BY c.not_after ASC
    """, params).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

@router.get("/summary")
def monitor_summary():
    """Resumo de vencimentos por faixa de dias."""
    from app.db import get_setting
    conn = get_db()
    alert_str = get_setting(conn, "alert_days")
    alert_days = [int(d.strip()) for d in alert_str.split(",")]

    result = {}
    result["vencidos"] = conn.execute(
        """SELECT COUNT(*) FROM certificates
           WHERE lifecycle_status IN ('instalado','em_inventario','reservado')
           AND julianday(not_after) < julianday('now','localtime')"""
    ).fetchone()[0]

    for d in alert_days:
        result[f"ate_{d}"] = conn.execute(
            """SELECT COUNT(*) FROM certificates
               WHERE lifecycle_status IN ('instalado','em_inventario','reservado')
               AND julianday(not_after) >= julianday('now','localtime')
               AND julianday(not_after) - julianday('now','localtime') <= ?""",
            (d,)
        ).fetchone()[0]

    result["alert_days"] = alert_days

    rows = conn.execute(
        "SELECT lifecycle_status, COUNT(*) as n FROM certificates GROUP BY lifecycle_status"
    ).fetchall()
    result["by_lifecycle"] = {r["lifecycle_status"]: r["n"] for r in rows}

    conn.close()
    return result

@router.post("/certs/{cert_id}/flag-renewal")
def flag_for_renewal(cert_id: int, user=Depends(require_auth)):
    """Marca certificado como 'em_renovacao' para iniciar processo de renovação."""
    conn = get_db()
    row = conn.execute("SELECT * FROM certificates WHERE id = ?", (cert_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Certificado não encontrado")
    conn.execute(
        "UPDATE certificates SET lifecycle_status = 'em_renovacao' WHERE id = ?",
        (cert_id,)
    )
    log_activity(conn, "lifecycle_em_renovacao",
                 f"Certificado {row['cn']} marcado para renovação", row['req_id'], user["id"])
    conn.commit()
    conn.close()
    return {"ok": True}
