"""CertHub — aplicação FastAPI."""
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import (certs, checklists, csr, dashboard, decoder, docs, files, hsm, monitor,
                      passwords, reqs, settings, tasks, templates, validate, auth, users)
from .routers.auth import require_auth

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CertHub", version="2.1")

init_db()

for router in (reqs.router, certs.router, csr.router, passwords.router,
               dashboard.router, docs.router, files.router, monitor.router,
               settings.router, tasks.router, templates.router, validate.router,
               decoder.router, checklists.router, hsm.router):
    app.include_router(router, prefix="/api", dependencies=[Depends(require_auth)])

# login/logout precisam ficar públicos — auth.router não leva a dependência global
app.include_router(auth.router)
app.include_router(users.router, dependencies=[Depends(require_auth)])

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _versioned_html(path: Path) -> str:
    """Injeta ?v={mtime} em /static/... para o navegador não servir JS/CSS em cache
    depois de um deploy novo."""
    html = path.read_text(encoding="utf-8")
    for asset in ("app.js", "styles.css"):
        asset_path = STATIC_DIR / asset
        if asset_path.exists():
            v = int(asset_path.stat().st_mtime)
            html = html.replace(f"/static/{asset}", f"/static/{asset}?v={v}")
    return html


@app.get("/", include_in_schema=False)
def index():
    return HTMLResponse(_versioned_html(STATIC_DIR / "index.html"))

@app.get("/login", include_in_schema=False)
def login_page():
    return HTMLResponse(_versioned_html(STATIC_DIR / "login.html"))
