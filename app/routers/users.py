from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.db import get_db
from app.routers.auth import require_admin, require_auth
from app.services.auth import hash_password

router = APIRouter(prefix="/api/users", tags=["users"])

class UserCreate(BaseModel):
    username: str
    display_name: str
    email: str
    role: str
    password: str

class UserUpdate(BaseModel):
    display_name: str
    email: str
    role: str
    active: int

class ResetPassword(BaseModel):
    new_password: str

class MyProfileUpdate(BaseModel):
    display_name: str
    email: str
    current_password: Optional[str] = None
    new_password: Optional[str] = None

@router.get("")
def list_users(conn=Depends(get_db), admin=Depends(require_admin)):
    rows = conn.execute("SELECT id, username, display_name, email, role, active, created_at, updated_at FROM users").fetchall()
    return [dict(r) for r in rows]

@router.post("")
def create_user(req: UserCreate, conn=Depends(get_db), admin=Depends(require_admin)):
    pwd_hash, pwd_salt = hash_password(req.password)
    try:
        conn.execute(
            """
            INSERT INTO users (username, display_name, email, role, password_hash, salt)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (req.username, req.display_name, req.email, req.role, pwd_hash, pwd_salt)
        )
        conn.commit()
    except Exception as e:
        if "UNIQUE constraint failed: users.username" in str(e):
            raise HTTPException(status_code=400, detail="Username já existe")
        raise HTTPException(status_code=500, detail=str(e))
    return {"message": "ok"}

@router.put("/{user_id}")
def update_user(user_id: int, req: UserUpdate, conn=Depends(get_db), admin=Depends(require_admin)):
    conn.execute(
        """
        UPDATE users 
        SET display_name = ?, email = ?, role = ?, active = ?, updated_at = datetime('now','localtime')
        WHERE id = ?
        """,
        (req.display_name, req.email, req.role, req.active, user_id)
    )
    conn.commit()
    return {"message": "ok"}

@router.delete("/{user_id}")
def deactivate_user(user_id: int, conn=Depends(get_db), admin=Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Não pode desativar a si mesmo")
    conn.execute("UPDATE users SET active = 0, updated_at = datetime('now','localtime') WHERE id = ?", (user_id,))
    conn.commit()
    return {"message": "ok"}

@router.post("/{user_id}/reset-password")
def reset_password(user_id: int, req: ResetPassword, conn=Depends(get_db), admin=Depends(require_admin)):
    pwd_hash, pwd_salt = hash_password(req.new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ?, updated_at = datetime('now','localtime') WHERE id = ?",
        (pwd_hash, pwd_salt, user_id)
    )
    conn.commit()
    return {"message": "ok"}

@router.get("/me")
def get_my_profile(user=Depends(require_auth)):
    return user

@router.put("/me")
def update_my_profile(req: MyProfileUpdate, conn=Depends(get_db), user=Depends(require_auth)):
    if req.new_password:
        from app.services.auth import verify_password
        row = conn.execute("SELECT password_hash, salt FROM users WHERE id = ?", (user["id"],)).fetchone()
        if not verify_password(req.current_password or "", row["password_hash"], row["salt"]):
            raise HTTPException(status_code=400, detail="Senha atual incorreta")
            
        pwd_hash, pwd_salt = hash_password(req.new_password)
        conn.execute(
            """
            UPDATE users 
            SET display_name = ?, email = ?, password_hash = ?, salt = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
            """,
            (req.display_name, req.email, pwd_hash, pwd_salt, user["id"])
        )
    else:
        conn.execute(
            """
            UPDATE users 
            SET display_name = ?, email = ?, updated_at = datetime('now','localtime')
            WHERE id = ?
            """,
            (req.display_name, req.email, user["id"])
        )
    conn.commit()
    return {"message": "ok"}

@router.get("/lookup")
def lookup_users(conn=Depends(get_db)):
    """Returns active users for assignment dropdowns (no admin required)."""
    rows = conn.execute(
        "SELECT id, username, display_name, email, role FROM users WHERE active=1 ORDER BY display_name"
    ).fetchall()
    return [dict(r) for r in rows]
