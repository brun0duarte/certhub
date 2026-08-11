from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from app.db import get_db
from app.services.auth import verify_password, create_session, delete_session, get_serializer, get_session_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

def get_current_user(request: Request):
    cookie_val = request.cookies.get("certhub_session")
    if not cookie_val:
        return None

    conn = get_db()
    try:
        serializer = get_serializer(conn)
        try:
            session_id = serializer.loads(cookie_val, max_age=8*3600)
        except Exception:
            return None

        return get_session_user(conn, session_id)
    finally:
        conn.close()

def require_auth(user=Depends(get_current_user)):
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    return user
    
def require_admin(user=Depends(require_auth)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    return user

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
def login(req: LoginRequest, response: Response, request: Request):
    conn = get_db()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (req.username,)).fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        user = dict(row)
        if not user["active"]:
            raise HTTPException(status_code=401, detail="Usuário inativo")

        if not verify_password(req.password, user["password_hash"], user["salt"]):
            raise HTTPException(status_code=401, detail="Credenciais inválidas")

        session_id = create_session(conn, user["id"], request.client.host if request.client else "")

        serializer = get_serializer(conn)
        cookie_val = serializer.dumps(session_id)
    finally:
        conn.close()

    response.set_cookie(
        key="certhub_session",
        value=cookie_val,
        httponly=True,
        samesite="lax"
    )

    return {
        "user_id": user["id"],
        "display_name": user["display_name"],
        "role": user["role"]
    }

@router.post("/logout")
def logout(response: Response, request: Request):
    cookie_val = request.cookies.get("certhub_session")
    if cookie_val:
        conn = get_db()
        try:
            serializer = get_serializer(conn)
            try:
                session_id = serializer.loads(cookie_val, max_age=8*3600)
                delete_session(conn, session_id)
            except Exception:
                pass
        finally:
            conn.close()

    response.delete_cookie("certhub_session")
    return {"message": "ok"}
    
@router.get("/me")
def get_me(user=Depends(require_auth)):
    return user
