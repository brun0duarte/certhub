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
    
    lifecycle_counts = {r['lifecycle_status']: r['n'] for r in conn.execute(
        'SELECT lifecycle_status, COUNT(*) n FROM certificates GROUP BY lifecycle_status'
    ).fetchall()}
    
    reqs_by_month = [dict(r) for r in conn.execute(
        """SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) n
           FROM reqs WHERE created_at >= date('now','localtime','-12 months')
           GROUP BY month ORDER BY month""")]

    key_types = [dict(r) for r in conn.execute(
        """SELECT COALESCE(NULLIF(key_type,''),'desconhecido') AS label, COUNT(*) n
           FROM certificates GROUP BY label ORDER BY n DESC""")]

    issuers = [dict(r) for r in conn.execute(
        """SELECT COALESCE(NULLIF(issuer,''),'desconhecido') AS label, COUNT(*) n
           FROM certificates GROUP BY label ORDER BY n DESC LIMIT 6""")]

    activity_by_day = [dict(r) for r in conn.execute(
        """SELECT strftime('%Y-%m-%d', created_at) AS day, COUNT(*) n
           FROM activity_log WHERE created_at >= date('now','localtime','-30 days')
           GROUP BY day ORDER BY day""")]

    cert_health = {
        "vencidos": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} < 0").fetchone()[0],
        "ate_30": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} BETWEEN 0 AND 30").fetchone()[0],
        "ate_90": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} BETWEEN 31 AND 90").fetchone()[0],
        "ok": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} > 90").fetchone()[0],
    }
    
    conn.close()
    return {"alert_days": alert_days, "expiring": expiring, "by_env": by_env,
            "by_status": by_status, "next_expiring": next_expiring,
            "activity": activity, "totals": totals, "lifecycle": lifecycle_counts,
            "reqs_by_month": reqs_by_month, "key_types": key_types,
            "issuers": issuers, "activity_by_day": activity_by_day,
            "cert_health": cert_health}


@router.get("/analytics")
def analytics():
    conn = get_db()
    days_left_sql = "CAST(julianday(not_after) - julianday('now','localtime') AS INTEGER)"

    expiring_by_month = [dict(r) for r in conn.execute(
        f"""SELECT strftime('%Y-%m', not_after) AS month, COUNT(*) n
            FROM certificates
            WHERE {days_left_sql} >= 0 AND not_after <= date('now','localtime','+12 months')
            GROUP BY month ORDER BY month""")]

    reqs_by_month = [dict(r) for r in conn.execute(
        """SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) n
           FROM reqs WHERE created_at >= date('now','localtime','-12 months')
           GROUP BY month ORDER BY month""")]

    by_env = {r["env"]: r["n"] for r in conn.execute(
        "SELECT env, COUNT(*) n FROM reqs GROUP BY env")}
    by_status = {r["status"]: r["n"] for r in conn.execute(
        "SELECT status, COUNT(*) n FROM reqs GROUP BY status")}

    key_types = [dict(r) for r in conn.execute(
        """SELECT COALESCE(NULLIF(key_type,''),'desconhecido') AS label, COUNT(*) n
           FROM certificates GROUP BY label ORDER BY n DESC""")]

    issuers = [dict(r) for r in conn.execute(
        """SELECT COALESCE(NULLIF(issuer,''),'desconhecido') AS label, COUNT(*) n
           FROM certificates GROUP BY label ORDER BY n DESC LIMIT 6""")]

    cert_health = {
        "vencidos": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} < 0").fetchone()[0],
        "ate_30": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} BETWEEN 0 AND 30").fetchone()[0],
        "ate_90": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} BETWEEN 31 AND 90").fetchone()[0],
        "ok": conn.execute(
            f"SELECT COUNT(*) FROM certificates WHERE {days_left_sql} > 90").fetchone()[0],
    }

    tasks_by_lane = [dict(r) for r in conn.execute(
        "SELECT lane, priority, COUNT(*) n FROM tasks GROUP BY lane, priority")]

    activity_by_day = [dict(r) for r in conn.execute(
        """SELECT strftime('%Y-%m-%d', created_at) AS day, COUNT(*) n
           FROM activity_log WHERE created_at >= date('now','localtime','-30 days')
           GROUP BY day ORDER BY day""")]

    conn.close()
    return {"expiring_by_month": expiring_by_month, "reqs_by_month": reqs_by_month,
            "by_env": by_env, "by_status": by_status, "key_types": key_types,
            "issuers": issuers, "cert_health": cert_health,
            "tasks_by_lane": tasks_by_lane, "activity_by_day": activity_by_day}
