import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

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
