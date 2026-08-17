import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers import dashboard as dashboard_router


class _KeepAliveConnection:
    """Sobrevive ao conn.close() do router pra permitir múltiplas chamadas no teste."""
    def __init__(self, real):
        self._real = real

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._real, name)


SCHEMA = """
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT, cn TEXT, env TEXT,
    status TEXT, demand_type TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, cn TEXT,
    not_after TEXT, key_type TEXT, issuer TEXT, lifecycle_status TEXT DEFAULT 'em_inventario',
    ownership TEXT DEFAULT 'interno', external_partner TEXT DEFAULT '', partner_email TEXT DEFAULT ''
);
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, user_id INTEGER,
    action TEXT, detail TEXT, created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, display_name TEXT);
CREATE TABLE tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, lane TEXT NOT NULL DEFAULT 'backlog');
"""


def _make_conn():
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.executescript(SCHEMA)
    real.commit()
    return real, _KeepAliveConnection(real)


# ---------------- US6 (specs/009-dashboard-hierarquia-clareza): campos novos de next_expiring ----------------

def test_next_expiring_includes_ownership_and_partner_fields(monkeypatch):
    real, conn = _make_conn()
    real.execute(
        "INSERT INTO certificates (cn, not_after, ownership, external_partner, partner_email) "
        "VALUES ('vpn.exemplo.com.br', date('now','+10 days'), 'externo', 'Parceiro X', 'contato@parceiro.com')"
    )
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.dashboard()

    row = result["next_expiring"][0]
    assert row["ownership"] == "externo"
    assert row["external_partner"] == "Parceiro X"
    assert row["partner_email"] == "contato@parceiro.com"


def test_next_expiring_has_active_demand_true_when_open_req_exists_for_cn(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO certificates (cn, not_after) VALUES ('www.exemplo.com.br', date('now','+5 days'))")
    real.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) "
        "VALUES ('REQ0000001', 'www.exemplo.com.br', 'PRD', 'aberta', 'geracao')"
    )
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.dashboard()

    assert result["next_expiring"][0]["has_active_demand"] == 1


def test_next_expiring_has_active_demand_false_without_open_req(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO certificates (cn, not_after) VALUES ('www.exemplo.com.br', date('now','+5 days'))")
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.dashboard()

    assert result["next_expiring"][0]["has_active_demand"] == 0


def test_next_expiring_has_active_demand_false_when_req_already_concluded(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO certificates (cn, not_after) VALUES ('www.exemplo.com.br', date('now','+5 days'))")
    real.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) "
        "VALUES ('REQ0000002', 'www.exemplo.com.br', 'PRD', 'concluida', 'geracao')"
    )
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.dashboard()

    assert result["next_expiring"][0]["has_active_demand"] == 0


# ---------------- US5 (specs/010-menu-lateral-reorganizacao): GET /nav-counts ----------------

def test_nav_counts_zero_when_no_pending_items(monkeypatch):
    real, conn = _make_conn()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.nav_counts()

    assert result == {"revogacao_pendente": 0, "kanban_pendente": 0}


def test_nav_counts_counts_open_revogacao_but_not_concluded(monkeypatch):
    real, conn = _make_conn()
    real.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) "
        "VALUES ('REQ0000010', 'a.exemplo.com.br', 'PRD', 'aberta', 'revogacao')"
    )
    real.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) "
        "VALUES ('REQ0000011', 'b.exemplo.com.br', 'PRD', 'concluida', 'revogacao')"
    )
    real.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) "
        "VALUES ('REQ0000012', 'c.exemplo.com.br', 'PRD', 'aberta', 'geracao')"
    )
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.nav_counts()

    assert result["revogacao_pendente"] == 1


def test_nav_counts_counts_tasks_outside_concluido_lane(monkeypatch):
    real, conn = _make_conn()
    real.execute("INSERT INTO tasks (lane) VALUES ('backlog')")
    real.execute("INSERT INTO tasks (lane) VALUES ('em_andamento')")
    real.execute("INSERT INTO tasks (lane) VALUES ('concluido')")
    real.commit()
    monkeypatch.setattr(dashboard_router, "get_db", lambda: conn)

    result = dashboard_router.nav_counts()

    assert result["kanban_pendente"] == 2
