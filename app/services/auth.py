import hashlib
import secrets
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer

def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(32)
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return h.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    h = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 260000)
    return secrets.compare_digest(h.hex(), stored_hash)

def get_or_create_secret(conn) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key='session_secret'").fetchone()
    if row:
        return row["value"]
    
    secret = secrets.token_hex(64)
    conn.execute("INSERT INTO settings (key, value) VALUES (?, ?)", ("session_secret", secret))
    conn.commit()
    return secret

def get_serializer(conn):
    secret = get_or_create_secret(conn)
    return URLSafeTimedSerializer(secret)

def create_session(conn, user_id: int, ip: str = '') -> str:
    session_id = secrets.token_hex(32)
    expires_at = (datetime.now() + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO sessions (id, user_id, expires_at, ip_addr) VALUES (?, ?, ?, ?)",
        (session_id, user_id, expires_at, ip)
    )
    conn.commit()
    return session_id

def get_session_user(conn, session_id: str) -> dict | None:
    row = conn.execute(
        """
        SELECT s.expires_at, u.id, u.username, u.display_name, u.role, u.active 
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.id = ?
        """,
        (session_id,)
    ).fetchone()
    
    if not row:
        return None
        
    expires_at = datetime.strptime(row["expires_at"], "%Y-%m-%d %H:%M:%S")
    if datetime.now() > expires_at:
        delete_session(conn, session_id)
        return None
        
    if not row["active"]:
        return None
        
    return dict(row)

def delete_session(conn, session_id: str):
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
