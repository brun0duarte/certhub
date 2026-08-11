"""Reset de dados do CertHub mantendo schema, config e usuários."""
import os
import sys
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "certhub.db")

from app.db import init_db

# Garante que o schema atual exista antes de limpar os dados.
init_db()

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA foreign_keys = ON")

TABLES_TO_CLEAR = [
    "install_task_evidence",
    "install_tasks",
    "install_locations",
    "certificates",
    "activity_log",
    "csrs",
    "reqs",
    "sessions",
]

# Limpa tabelas legado se ainda existirem (schemas antigos/parciais)
tables_in_db = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
for legacy in ("crq_tasks", "wo_tasks", "work_orders"):
    if legacy in tables_in_db:
        conn.execute(f"DELETE FROM {legacy}")

for table in TABLES_TO_CLEAR:
    if table in tables_in_db:
        conn.execute(f"DELETE FROM {table}")

# Remove contadores autoincremento das tabelas limpas.
all_cleared = TABLES_TO_CLEAR + [t for t in ("crq_tasks", "wo_tasks", "work_orders") if t in tables_in_db]
conn.execute(
    "DELETE FROM sqlite_sequence WHERE name IN ({})".format(
        ",".join("?" for _ in all_cleared)
    ),
    all_cleared,
)

conn.commit()
conn.close()

print("✅ Dados operacionais removidos. Schema, settings, docs, templates e usuários preservados.")
