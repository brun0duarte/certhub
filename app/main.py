"""CertHub — aplicação FastAPI."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db
from .routers import (certs, csr, dashboard, docs, files, passwords, reqs,
                      settings, tasks, templates, validate)

STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="CertHub", version="2.0")

init_db()

for router in (reqs.router, certs.router, csr.router, passwords.router,
               dashboard.router, docs.router, files.router, settings.router,
               tasks.router, templates.router, validate.router):
    app.include_router(router, prefix="/api")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")
