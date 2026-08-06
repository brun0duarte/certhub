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
    "crq_tasks",
    "work_orders",
    "install_locations",
    "certificates",
    "activity_log",
    "csrs",
    "reqs",
    "sessions",
]

for table in TABLES_TO_CLEAR:
    conn.execute(f"DELETE FROM {table}")

# Remove contadores autoincremento das tabelas limpas.
conn.execute(
    "DELETE FROM sqlite_sequence WHERE name IN ({})".format(
        ",".join("?" for _ in TABLES_TO_CLEAR)
    ),
    TABLES_TO_CLEAR,
)

conn.commit()
conn.close()

print("✅ Dados operacionais removidos. Schema, settings, docs, templates e usuários preservados.")
