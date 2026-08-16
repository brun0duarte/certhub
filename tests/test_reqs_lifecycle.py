import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers import reqs as reqs_router
from app.routers.reqs import find_existing_active_req


def test_find_existing_active_req_returns_existing_req_for_same_certificate():
    conn = sqlite3.connect(':memory:')
    conn.execute(
        "CREATE TABLE reqs (id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT, cn TEXT, env TEXT, status TEXT, demand_type TEXT)"
    )
    conn.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) VALUES (?, ?, ?, ?, ?)",
        ('REQ0000001', 'www.exemplo.com.br', 'PRD', 'aberta', 'geracao')
    )
    conn.commit()

    existing = find_existing_active_req(conn, 'www.exemplo.com.br', 'PRD', 'geracao')

    assert existing is not None
    assert existing['req_number'] == 'REQ0000001'


def test_find_existing_active_req_ignores_concluded_reqs():
    conn = sqlite3.connect(':memory:')
    conn.execute(
        "CREATE TABLE reqs (id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT, cn TEXT, env TEXT, status TEXT, demand_type TEXT)"
    )
    conn.execute(
        "INSERT INTO reqs (req_number, cn, env, status, demand_type) VALUES (?, ?, ?, ?, ?)",
        ('REQ0000002', 'www.exemplo.com.br', 'PRD', 'concluida', 'geracao')
    )
    conn.commit()

    existing = find_existing_active_req(conn, 'www.exemplo.com.br', 'PRD', 'geracao')

    assert existing is None


# ---------------- US2 (specs/002-busca-filtro-hsm-perfis): ordenação de GET /reqs ----------------

REQS_SCHEMA = """
CREATE TABLE reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT, cn TEXT, env TEXT,
    status TEXT, demand_type TEXT, notes TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE certificates (id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER);
CREATE TABLE install_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER);
"""


class _KeepAliveConnection:
    """Sobrevive ao conn.close() do db_conn() do router pra permitir múltiplas chamadas no teste."""
    def __init__(self, real):
        self._real = real

    def close(self):
        pass

    def __getattr__(self, name):
        return getattr(self._real, name)


def _make_reqs_conn():
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.executescript(REQS_SCHEMA)
    rows = [
        ('REQ0000003', 'c.exemplo.com.br', 'DES', 'aberta', 'geracao'),
        ('REQ0000001', 'a.exemplo.com.br', 'PRD', 'concluida', 'geracao'),
        ('REQ0000002', 'b.exemplo.com.br', 'HMP', 'aberta', 'instalacao'),
    ]
    for req_number, cn, env, status, demand_type in rows:
        real.execute(
            "INSERT INTO reqs (req_number, cn, env, status, demand_type) VALUES (?,?,?,?,?)",
            (req_number, cn, env, status, demand_type))
    real.commit()
    return real, _KeepAliveConnection(real)


def test_list_reqs_sorts_by_req_number_ascending(monkeypatch):
    real, conn = _make_reqs_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    result = reqs_router.list_reqs(sort="req_number", dir="asc")

    assert [r["req_number"] for r in result["items"]] == ['REQ0000001', 'REQ0000002', 'REQ0000003']


def test_list_reqs_sorts_by_env_descending(monkeypatch):
    real, conn = _make_reqs_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    result = reqs_router.list_reqs(sort="env", dir="desc")

    assert [r["env"] for r in result["items"]] == ['PRD', 'HMP', 'DES']


def test_list_reqs_unknown_sort_falls_back_to_created_at(monkeypatch):
    real, conn = _make_reqs_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    default_result = reqs_router.list_reqs()
    fallback_result = reqs_router.list_reqs(sort="not_a_real_column")

    assert [r["id"] for r in fallback_result["items"]] == [r["id"] for r in default_result["items"]]


def test_list_reqs_sort_combines_with_existing_filters(monkeypatch):
    real, conn = _make_reqs_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    result = reqs_router.list_reqs(exclude_status="concluida", sort="req_number", dir="asc")

    assert [r["req_number"] for r in result["items"]] == ['REQ0000002', 'REQ0000003']


# ---------------- US4 (specs/004-revogacao-certificados): demandas de revogação ----------------

FULL_SCHEMA = """
CREATE TABLE reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_number TEXT UNIQUE, cn TEXT, env TEXT,
    password TEXT, status TEXT DEFAULT 'aberta', notes TEXT DEFAULT '',
    demand_type TEXT DEFAULT 'geracao', parent_req_id INTEGER,
    external_wo TEXT DEFAULT '', external_crq TEXT DEFAULT '',
    external_partner TEXT DEFAULT '', partner_email TEXT DEFAULT '', partner_registration TEXT DEFAULT '',
    ownership TEXT DEFAULT 'interno',
    revoke_destination TEXT DEFAULT '', revoke_destination_other TEXT DEFAULT '', revoke_cert_id INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime')), updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, cn TEXT, serial TEXT, thumbprint_sha1 TEXT,
    lifecycle_status TEXT DEFAULT 'em_inventario'
);
CREATE TABLE install_locations (id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, req_id INTEGER, action TEXT NOT NULL,
    detail TEXT DEFAULT '', user_id INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

USER = {"id": 1}


def _make_full_conn():
    real = sqlite3.connect(":memory:")
    real.row_factory = sqlite3.Row
    real.executescript(FULL_SCHEMA)
    real.commit()
    return real, _KeepAliveConnection(real)


def _revocation_body(**overrides):
    from app.routers.reqs import ReqIn
    fields = dict(cn="www.exemplo.com.br", env="PRD", demand_type="revogacao",
                  auto_password=False, revoke_destination="serpro")
    fields.update(overrides)
    return ReqIn(**fields)


def test_create_req_revogacao_requires_destination(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    from fastapi import HTTPException
    try:
        reqs_router.create_req(_revocation_body(revoke_destination=""), user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_create_req_revogacao_outros_requires_description(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    from fastapi import HTTPException
    try:
        reqs_router.create_req(_revocation_body(revoke_destination="outros", revoke_destination_other=""), user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400


def test_create_req_revogacao_success_persists_destination(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)

    row = reqs_router.create_req(_revocation_body(revoke_destination="ac_interna_prd"), user=USER)

    assert row["demand_type"] == "revogacao"
    assert row["revoke_destination"] == "ac_interna_prd"


def test_create_req_revogacao_duplicate_is_non_blocking_warning_then_forceable(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    reqs_router.create_req(_revocation_body(), user=USER)

    from fastapi import HTTPException
    try:
        reqs_router.create_req(_revocation_body(), user=USER)
        assert False, "deveria ter levantado HTTPException (409, aviso de duplicidade)"
    except HTTPException as e:
        assert e.status_code == 409

    # com force_duplicate=True, a criação é permitida mesmo com uma demanda em aberto
    row = reqs_router.create_req(_revocation_body(force_duplicate=True), user=USER)
    assert row["demand_type"] == "revogacao"
    count = real.execute("SELECT COUNT(*) FROM reqs WHERE demand_type='revogacao'").fetchone()[0]
    assert count == 2


def test_update_req_concluida_sets_certificate_lifecycle_revogado(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    cert_id = real.execute(
        "INSERT INTO certificates (cn, serial, thumbprint_sha1) VALUES ('www.exemplo.com.br', 'AA11', 'BB22')"
    ).lastrowid
    real.commit()
    created = reqs_router.create_req(_revocation_body(revoke_cert_id=cert_id), user=USER)

    reqs_router.update_req(created["id"], reqs_router.ReqUpdate(status="concluida"), user=USER)

    lifecycle = real.execute("SELECT lifecycle_status FROM certificates WHERE id=?", (cert_id,)).fetchone()[0]
    assert lifecycle == "revogado"


def test_revoke_req_calls_provider_and_logs_activity(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    created = reqs_router.create_req(_revocation_body(revoke_destination="ac_interna_nprd"), user=USER)

    result = reqs_router.revoke_req(created["id"], user=USER)

    assert result["ok"] is False
    assert result["code"] == "NOT_CONNECTED"
    assert result["destination"] == "ac_interna_nprd"
    assert "AC Interna NPRD" in result["output"]
    logged = real.execute("SELECT action FROM activity_log WHERE req_id=? ORDER BY id DESC LIMIT 1",
                           (created["id"],)).fetchone()
    assert logged["action"] == "revogacao_solicitada"


def test_revoke_req_rejects_non_revocation_demand(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    from app.routers.reqs import ReqIn
    created = reqs_router.create_req(
        ReqIn(cn="www.exemplo.com.br", env="PRD", demand_type="geracao", auto_password=False), user=USER)

    from fastapi import HTTPException
    try:
        reqs_router.revoke_req(created["id"], user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 404


def test_create_req_revogacao_rejects_already_revoked_certificate(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    cert_id = real.execute(
        "INSERT INTO certificates (cn, serial, thumbprint_sha1, lifecycle_status) "
        "VALUES ('www.exemplo.com.br', 'AA11', 'BB22', 'revogado')"
    ).lastrowid
    real.commit()

    from fastapi import HTTPException
    try:
        reqs_router.create_req(_revocation_body(revoke_cert_id=cert_id), user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400
        assert "já foi revogado" in e.detail


def test_revoke_req_rejects_already_revoked_certificate(monkeypatch):
    real, conn = _make_full_conn()
    monkeypatch.setattr(reqs_router, "get_db", lambda: conn)
    cert_id = real.execute(
        "INSERT INTO certificates (cn, serial, thumbprint_sha1) VALUES ('www.exemplo.com.br', 'AA11', 'BB22')"
    ).lastrowid
    real.commit()
    created = reqs_router.create_req(_revocation_body(revoke_cert_id=cert_id), user=USER)
    real.execute("UPDATE certificates SET lifecycle_status='revogado' WHERE id=?", (cert_id,))
    real.commit()

    from fastapi import HTTPException
    try:
        reqs_router.revoke_req(created["id"], user=USER)
        assert False, "deveria ter levantado HTTPException"
    except HTTPException as e:
        assert e.status_code == 400
        assert "já foi revogado" in e.detail
