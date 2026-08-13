"""Monitor de vencimentos de certificados."""
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db import get_db, log_activity, LIFECYCLE_STATUSES
from app.routers.auth import require_auth

router = APIRouter(prefix="/monitor", tags=["monitor"])

@router.get("/expiring")
def get_expiring_certs(days: int = Query(90, ge=0), pending_only: bool = False):
    """Lista certificados próximos do vencimento."""
    conn = get_db()
    where_clause = "AND (julianday(c.not_after) - julianday('now','localtime') <= ? OR julianday(c.not_after) < julianday('now','localtime'))"
    if pending_only:
        where_clause += " AND active_req.id IS NULL"

    query = f"""
        SELECT c.*, r.req_number, r.env,
               CAST(julianday(c.not_after) - julianday('now','localtime') AS INTEGER) as days_left,
               CASE WHEN active_req.id IS NOT NULL THEN 1 ELSE 0 END as has_active_demand
        FROM certificates c
        LEFT JOIN reqs r ON c.req_id = r.id
        LEFT JOIN reqs active_req ON active_req.cn = c.cn
            AND active_req.demand_type IN ('geracao','recebimento')
            AND active_req.status NOT IN ('concluida','cancelada')
        WHERE c.lifecycle_status IN ('instalado', 'em_inventario', 'reservado')
        {where_clause}
        ORDER BY c.not_after ASC
    """
    rows = conn.execute(query, (days,)).fetchall()
    result = [dict(r) for r in rows]
    conn.close()
    return result

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
