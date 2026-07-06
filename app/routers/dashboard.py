"""Painel: vencimentos, contagens por ambiente e status, atividade recente."""
from fastapi import APIRouter

from ..db import get_db, get_setting

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard():
    conn = get_db()
    alert_days = [int(d) for d in get_setting(conn, "alert_days").split(",") if d.strip()]
    alert_days = sorted(alert_days) or [30, 60, 90]

    days_left_sql = "CAST(julianday(not_after) - julianday('now','localtime') AS INTEGER)"
    expiring = {}
    expiring["vencidos"] = conn.execute(
        f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} < 0").fetchone()[0]
    for d in alert_days:
        expiring[f"ate_{d}"] = conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} >= 0 AND {days_left_sql} <= ?",
            (d,)).fetchone()[0]

    by_env = {r["env"]: r["n"] for r in conn.execute(
        "SELECT env, COUNT(*) n FROM reqs GROUP BY env")}
    by_status = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) n FROM reqs GROUP BY status")}

    next_expiring = [dict(r) for r in conn.execute(
        f"""SELECT c.id, c.cn, c.not_after, {days_left_sql} AS days_left,
                   r.req_number, r.env
            FROM certificates c LEFT JOIN reqs r ON r.id = c.req_id
            WHERE {days_left_sql} <= ?
            ORDER BY c.not_after ASC LIMIT 10""", (max(alert_days),))]

    activity = [dict(r) for r in conn.execute(
        """SELECT a.*, r.req_number FROM activity_log a
           LEFT JOIN reqs r ON r.id = a.req_id ORDER BY a.id DESC LIMIT 10""")]

    totals = {
        "reqs": conn.execute("SELECT COUNT(*) FROM reqs").fetchone()[0],
        "reqs_abertas": conn.execute(
            "SELECT COUNT(*) FROM reqs WHERE status NOT IN ('concluida','cancelada')").fetchone()[0],
        "certificados": conn.execute("SELECT COUNT(*) FROM certificates").fetchone()[0],
    }
    conn.close()
    return {"alert_days": alert_days, "expiring": expiring, "by_env": by_env,
            "by_status": by_status, "next_expiring": next_expiring,
            "activity": activity, "totals": totals}
