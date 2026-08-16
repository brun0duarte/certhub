"""Demandas (REQ): CRUD, status, locais de instalação, pastas e histórico."""
import json
import re
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..db import (INSTALL_LOCATIONS, INSTALL_LOCATION_LABELS, REQ_STATUSES, REVOKE_DESTINATIONS,
                   get_db, get_setting, log_activity)
from ..services import folders, passwordgen
from ..services.installers.registry import PROVIDERS
from ..services.revocation.ac_interna import AcInternaRevocationProvider
from ..services.revocation.internacional import InternacionalRevocationProvider
from ..services.revocation.outros import OutrosRevocationProvider
from ..services.revocation.serpro import SerproRevocationProvider
from .auth import require_auth

router = APIRouter(tags=["reqs"])
REQ_FORMAT = re.compile(r"^[A-Z0-9_\-\.]{3,30}$", re.IGNORECASE)

SORT_COLUMNS = {
    "req_number": "r.req_number",
    "env": "r.env",
    "status": "r.status",
    "created_at": "r.created_at",
}


@contextmanager
def db_conn():
    """Context manager que garante fechamento da conexão mesmo em exceções."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


def find_existing_active_req(conn, cn: str, env: str, demand_type: str) -> dict | None:
    """Demanda ativa (não concluída/cancelada) com mesmo CN+ambiente+tipo, se houver."""
    row = conn.execute(
        "SELECT id, req_number, cn, env, status, demand_type FROM reqs "
        "WHERE cn=? AND env=? AND demand_type=? AND status NOT IN ('concluida','cancelada')",
        (cn, env, demand_type)
    ).fetchone()
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        return dict(row)
    return dict(zip(("id", "req_number", "cn", "env", "status", "demand_type"), row))


def find_existing_active_revocation(conn, cn: str, env: str, revoke_cert_id: int | None) -> dict | None:
    """Demanda de revogação em aberto (não concluída/cancelada) pro mesmo certificado
    (revoke_cert_id) ou, na ausência de vínculo, mesmo CN+ambiente — aviso não-bloqueante
    (FR-010, diferente do bloqueio rígido de geracao/recebimento)."""
    if revoke_cert_id:
        row = conn.execute(
            "SELECT id, req_number, cn, env, status, created_at FROM reqs "
            "WHERE demand_type='revogacao' AND revoke_cert_id=? AND status NOT IN ('concluida','cancelada')",
            (revoke_cert_id,)
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT id, req_number, cn, env, status, created_at FROM reqs "
            "WHERE demand_type='revogacao' AND cn=? AND env=? AND revoke_cert_id IS NULL "
            "AND status NOT IN ('concluida','cancelada')",
            (cn, env)
        ).fetchone()
    return dict(row) if row else None


class ReqIn(BaseModel):
    req_number: str | None = None
    cn: str
    env: str
    notes: str = ""
    password: str | None = None
    auto_password: bool = True
    demand_type: str = "geracao"
    parent_req_id: int | None = None
    external_wo: str = ""
    external_crq: str = ""
    external_partner: str = ""
    partner_email: str = ""
    partner_registration: str = ""
    ownership: str = "interno"
    revoke_destination: str = ""
    revoke_destination_other: str = ""
    revoke_cert_id: int | None = None
    force_duplicate: bool = False


class ReqUpdate(BaseModel):
    cn: str | None = None
    env: str | None = None
    notes: str | None = None
    password: str | None = None
    status: str | None = None
    demand_type: str | None = None
    external_wo: str | None = None
    external_crq: str | None = None
    external_partner: str | None = None
    partner_email: str | None = None
    partner_registration: str | None = None
    ownership: str | None = None
    revoke_destination: str | None = None
    revoke_destination_other: str | None = None
    revoke_cert_id: int | None = None





class LocationIn(BaseModel):
    server: str
    path_or_store: str = ""
    installed_at: str | None = None
    notes: str = ""
    cert_id: int | None = None


class LocationStatusUpdate(BaseModel):
    status: str  # 'pendente', 'instalado', 'falhou'




def _auto_password(conn) -> str:
    policy = json.loads(get_setting(conn, "password_policy"))
    return passwordgen.generate(**policy)


@router.get("/reqs")
def list_reqs(search: str = "", env: str = "", status: str = "", demand_type: str = "",
              exclude_status: str = "", revoke_destination: str = "",
              sort: str = "created_at", dir: str = "desc",
              page: int = 1, page_size: int = 1000):
    with db_conn() as conn:
        where = " WHERE 1=1"
        params = []
        if search:
            where += " AND (r.req_number LIKE ? OR r.cn LIKE ? OR r.notes LIKE ?)"
            params += [f"%{search}%"] * 3
        if env:
            where += " AND r.env = ?"
            params.append(env)
        if status:
            where += " AND r.status = ?"
            params.append(status)
        if revoke_destination:
            where += " AND r.revoke_destination = ?"
            params.append(revoke_destination)
        if demand_type:
            types = [t.strip() for t in demand_type.split(',')]
            where += " AND r.demand_type IN (" + ",".join("?" for _ in types) + ")"
            params.extend(types)
        if exclude_status:
            statuses = [s.strip() for s in exclude_status.split(',')]
            where += " AND r.status NOT IN (" + ",".join("?" for _ in statuses) + ")"
            params.extend(statuses)
        total = conn.execute("SELECT COUNT(*) FROM reqs r" + where, params).fetchone()[0]
        sort_col = SORT_COLUMNS.get(sort, SORT_COLUMNS["created_at"])
        sort_dir = "DESC" if dir.lower() == "desc" else "ASC"
        sql = ("""SELECT r.*,
                         (SELECT COUNT(*) FROM certificates c WHERE c.req_id = r.id) AS cert_count,
                         (SELECT COUNT(*) FROM install_locations l WHERE l.req_id = r.id) AS location_count
                  FROM reqs r""" + where + f" ORDER BY {sort_col} {sort_dir} LIMIT ? OFFSET ?")
        page = max(page, 1)
        items = [dict(r) for r in conn.execute(
            sql, params + [min(page_size, 1000), (page - 1) * page_size]).fetchall()]
        return {"items": items, "total": total}


def _seed_install_tasks(conn, req_id: int):
    """Clona o checklist de tarefas ativo pra essa demanda de instalação em PRD (mudança/CRQ)."""
    if conn.execute("SELECT 1 FROM install_tasks WHERE req_id=?", (req_id,)).fetchone():
        return
    templates = conn.execute(
        "SELECT title, instructions, message_template, position FROM checklist_task_templates "
        "WHERE active=1 ORDER BY position, id").fetchall()
    for t in templates:
        conn.execute(
            "INSERT INTO install_tasks (req_id, title, instructions, message_template, position) "
            "VALUES (?,?,?,?,?)",
            (req_id, t["title"], t["instructions"], t["message_template"], t["position"]))


def _next_req_number(conn) -> str:
    row = conn.execute(
        "SELECT req_number FROM reqs WHERE req_number LIKE 'REQ%' "
        "ORDER BY CAST(SUBSTR(req_number, 4) AS INTEGER) DESC LIMIT 1"
    ).fetchone()
    next_num = int(row[0][3:]) + 1 if row else 1
    return f"REQ{next_num:07d}"


@router.post("/reqs")
def create_req(body: ReqIn, user=Depends(require_auth)):
    with db_conn() as conn:
        # Auto-generate REQ number if not provided
        if not body.req_number:
            req_number = _next_req_number(conn)
        else:
            req_number = body.req_number.strip().upper()
            if not REQ_FORMAT.match(req_number):
                raise HTTPException(400, "Número inválido — use letras, números, hifens ou pontos (3–30 caracteres)")

        # Block duplicate active demands for geracao/recebimento
        if body.demand_type in ('geracao', 'recebimento'):
            dup = find_existing_active_req(conn, body.cn.strip(), body.env, body.demand_type)
            if dup:
                raise HTTPException(409,
                    f"Já existe demanda ativa ({dup['req_number']}) para este CN/ambiente. "
                    f"Conclua ou cancele a anterior antes de criar nova.")

        # Demanda de revogação: destino obrigatório, texto livre quando 'outros',
        # e aviso não-bloqueante de duplicidade (FR-004/FR-005/FR-010)
        if body.demand_type == 'revogacao':
            if body.revoke_destination not in REVOKE_DESTINATIONS:
                raise HTTPException(400, "Escolha o destino da revogação.")
            if body.revoke_destination == 'outros' and not body.revoke_destination_other.strip():
                raise HTTPException(400, "Descreva o destino quando escolher 'Outros'.")
            if body.revoke_cert_id:
                cert = conn.execute("SELECT lifecycle_status FROM certificates WHERE id=?",
                                     (body.revoke_cert_id,)).fetchone()
                if cert and cert["lifecycle_status"] == "revogado":
                    raise HTTPException(400, "Este certificado já foi revogado.")
            if not body.force_duplicate:
                dup = find_existing_active_revocation(conn, body.cn.strip(), body.env, body.revoke_cert_id)
                if dup:
                    raise HTTPException(409,
                        f"Já existe uma demanda de revogação em aberto ({dup['req_number']}) para este "
                        f"certificado/CN. Confirme novamente para criar mesmo assim.")

        # Check for duplicate req_number
        existing = conn.execute("SELECT id FROM reqs WHERE req_number=?", (req_number,)).fetchone()
        if existing:
            raise HTTPException(409, f"Já existe uma demanda com número {req_number}.")

        password = body.password or (_auto_password(conn) if body.auto_password else None)
        cur = conn.execute(
            "INSERT INTO reqs (req_number, cn, env, password, notes, demand_type, parent_req_id, external_wo, external_crq, external_partner, partner_email, partner_registration, ownership, "
            "revoke_destination, revoke_destination_other, revoke_cert_id) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (req_number, body.cn.strip(), body.env, password, body.notes,
             body.demand_type, body.parent_req_id, body.external_wo, body.external_crq, body.external_partner, body.partner_email, body.partner_registration, body.ownership,
             body.revoke_destination, body.revoke_destination_other, body.revoke_cert_id),
        )



        req_id = cur.lastrowid
        log_activity(conn, "req_criada", f"{req_number} · CN {body.cn} · {body.env}", req_id, user["id"])
        if password and body.auto_password and not body.password:
            log_activity(conn, "senha_gerada", "Senha gerada automaticamente na criação", req_id, user["id"])
        if body.demand_type == 'instalacao' and body.env == 'PRD':
            _seed_install_tasks(conn, req_id)
        conn.commit()
        return dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())


@router.get("/reqs/flows")
def get_flows():
    return FLOWS


@router.get("/reqs/flows/{demand_type}")
def get_flow(demand_type: str):
    flow = FLOWS.get(demand_type)
    if not flow:
        raise HTTPException(404, f"Fluxo não encontrado para tipo '{demand_type}'")
    return {"demand_type": demand_type, "mermaid": flow}


@router.get("/reqs/{req_id}")
def get_req(req_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        req = dict(row)
        req["locations"] = [dict(r) for r in conn.execute(
            "SELECT * FROM install_locations WHERE req_id=? ORDER BY id", (req_id,))]
        certs = [dict(r) for r in conn.execute(
            "SELECT * FROM certificates WHERE req_id=? ORDER BY created_at DESC", (req_id,))]
        if not certs:
            certs = [dict(r) for r in conn.execute(
                """SELECT c.* FROM certificates c
                   JOIN install_locations l ON l.cert_id = c.id
                   WHERE l.req_id=? ORDER BY c.created_at DESC""", (req_id,))]
        req["certificates"] = certs
        if certs:
            c = certs[0]
            req["not_after"] = c.get("not_after", "")
            req["vencimento"] = c.get("not_after", "")
            req["issuer"] = c.get("issuer_cn") or c.get("issuer") or ""
            req["issuer_cn"] = c.get("issuer_cn") or c.get("issuer") or ""
            req["emissor"] = c.get("issuer_cn") or c.get("issuer") or ""


        tasks = [dict(r) for r in conn.execute(
            "SELECT * FROM install_tasks WHERE req_id=? ORDER BY position, id", (req_id,))]
        for t in tasks:
            t["evidence"] = [dict(r) for r in conn.execute(
                "SELECT * FROM install_task_evidence WHERE task_id=? ORDER BY id", (t["id"],))]
        req["install_tasks"] = tasks

        req["activity"] = [dict(r) for r in conn.execute(
            """SELECT a.*, u.display_name AS user_name FROM activity_log a
               LEFT JOIN users u ON u.id = a.user_id
               WHERE a.req_id=? ORDER BY a.id DESC LIMIT 50""", (req_id,))]
        req["past_reqs"] = [dict(r) for r in conn.execute(
            "SELECT id, req_number, demand_type, env, status, created_at, external_partner, partner_email, partner_registration FROM reqs WHERE cn=? AND id!=? ORDER BY id DESC LIMIT 10",
            (req["cn"], req_id)
        ).fetchall()]
        base = get_setting(conn, "base_dir")
        template = get_setting(conn, "folder_template")
        folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"])
        req["folder"] = str(folder)
        req["folder_exists"] = folder.exists()
        return req


@router.get("/reqs/history-by-cn")
def get_cn_history(cn: str):
    """Retorna histórico de demandas anteriores e dados preenchidos para um CN."""
    if not cn or not cn.strip():
        return {"reqs": [], "latest": None, "locations": []}
    with db_conn() as conn:
        clean_cn = cn.strip()
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM reqs WHERE cn=? ORDER BY id DESC LIMIT 20", (clean_cn,)
        ).fetchall()]
        
        latest = None
        for r in rows:
            if r.get("external_partner") or r.get("partner_email") or r.get("partner_registration"):
                latest = {
                    "external_partner": r.get("external_partner", ""),
                    "partner_email": r.get("partner_email", ""),
                    "partner_registration": r.get("partner_registration", ""),
                    "notes": r.get("notes", "")
                }
                break
        
        locations = [dict(r) for r in conn.execute("""
            SELECT DISTINCT l.server, l.path_or_store, l.location_type, l.notes
            FROM install_locations l
            JOIN reqs r ON r.id = l.req_id
            WHERE r.cn=?
            ORDER BY l.id DESC
        """, (clean_cn,)).fetchall()]
        
        return {
            "reqs": rows,
            "latest": latest,
            "locations": locations
        }



@router.put("/reqs/{req_id}")
def update_req(req_id: int, body: ReqUpdate, user=Depends(require_auth)):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
        if "status" in fields and fields["status"] not in REQ_STATUSES:
            raise HTTPException(400, f"Status inválido. Use: {', '.join(REQ_STATUSES)}")
        if "status" in fields and fields["status"] == "instalado":
            demand_type = fields.get("demand_type", row["demand_type"])
            if demand_type != "instalacao":
                raise HTTPException(400,
                    "🔒 Status 'Instalado' só se aplica a demandas de instalação — "
                    "conclua a geração/recebimento primeiro para avançar para instalação.")
        if "status" in fields and fields["status"] == "concluida":
            demand_type = row["demand_type"] if "demand_type" in row.keys() else "geracao"
            if demand_type in ("geracao", "recebimento", "renovacao"):
                cert_count = conn.execute("SELECT COUNT(*) FROM certificates WHERE req_id=?", (req_id,)).fetchone()[0]
                if cert_count == 0:
                    raise HTTPException(400, "🔒 Não é possível concluir esta demanda sem antes importar e vincular o certificado emitido.")
            if demand_type == "revogacao":
                revoke_cert_id = row["revoke_cert_id"] if "revoke_cert_id" in row.keys() else None
                if revoke_cert_id:
                    conn.execute("UPDATE certificates SET lifecycle_status='revogado' WHERE id=?", (revoke_cert_id,))

        if ("revoke_destination" in fields or "revoke_destination_other" in fields):
            demand_type = fields.get("demand_type", row["demand_type"])
            if demand_type == "revogacao":
                destination = fields.get("revoke_destination",
                                          row["revoke_destination"] if "revoke_destination" in row.keys() else "")
                if destination not in REVOKE_DESTINATIONS:
                    raise HTTPException(400, "Escolha o destino da revogação.")
                other = fields.get("revoke_destination_other",
                                    row["revoke_destination_other"] if "revoke_destination_other" in row.keys() else "")
                if destination == "outros" and not (other or "").strip():
                    raise HTTPException(400, "Descreva o destino quando escolher 'Outros'.")

        if fields:
            sets = ", ".join(f"{k}=?" for k in fields)
            conn.execute(
                f"UPDATE reqs SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
                (*fields.values(), req_id),
            )
            if "status" in fields:
                log_activity(conn, "status_alterado", f"{row['status']} → {fields['status']}", req_id, user["id"])
            other_fields = [k for k in fields if k != "status"]
            if other_fields:
                log_activity(conn, "demanda_editada", f"Campos alterados: {', '.join(other_fields)}",
                             req_id, user["id"])
            conn.commit()
        return dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())


def _revocation_provider(destination: str):
    """Resolve o provider de revogação pelo destino salvo na demanda
    (contracts/revocation-provider.md — specs/004-revogacao-certificados)."""
    return {
        "internacional": lambda: InternacionalRevocationProvider(),
        "serpro": lambda: SerproRevocationProvider(),
        "ac_interna_nprd": lambda: AcInternaRevocationProvider(ambiente="nprd"),
        "ac_interna_prd": lambda: AcInternaRevocationProvider(ambiente="prd"),
        "outros": lambda: OutrosRevocationProvider(),
    }[destination]()


@router.post("/reqs/{req_id}/revoke")
def revoke_req(req_id: int, user=Depends(require_auth)):
    """Aciona o provider de revogação do destino da demanda — nesta fase, sempre
    'não conectado' (FR-008), mas a chamada é real e fica registrada em activity_log."""
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        if row["demand_type"] != "revogacao":
            raise HTTPException(404, "Essa ação só se aplica a demandas de revogação.")
        destination = row["revoke_destination"] if "revoke_destination" in row.keys() else ""
        if destination not in REVOKE_DESTINATIONS:
            raise HTTPException(400, "Demanda sem destino de revogação válido.")

        serial, thumbprint = "", ""
        revoke_cert_id = row["revoke_cert_id"] if "revoke_cert_id" in row.keys() else None
        if revoke_cert_id:
            cert = conn.execute("SELECT serial, thumbprint_sha1, lifecycle_status FROM certificates WHERE id=?",
                                 (revoke_cert_id,)).fetchone()
            if cert:
                if cert["lifecycle_status"] == "revogado":
                    raise HTTPException(400, "Este certificado já foi revogado.")
                serial, thumbprint = cert["serial"] or "", cert["thumbprint_sha1"] or ""

        provider = _revocation_provider(destination)
        result = provider.revoke(row["cn"], serial=serial, thumbprint=thumbprint, reason=row["notes"] or "")
        log_activity(conn, "revogacao_solicitada",
                     f"{provider.label} · {'ok' if result['ok'] else result.get('code', 'FALHOU')}",
                     req_id, user["id"])
        conn.commit()
        return {**result, "destination": destination}


@router.delete("/reqs/{req_id}")
def delete_req(req_id: int, user=Depends(require_auth)):
    with db_conn() as conn:
        row = conn.execute("SELECT req_number FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        conn.execute("DELETE FROM reqs WHERE id=?", (req_id,))
        log_activity(conn, "req_excluida", row["req_number"], None, user["id"])
        conn.commit()
        return {"ok": True}


@router.post("/reqs/{req_id}/advance-to-installation")
def advance_to_installation(req_id: int, user=Depends(require_auth)):
    """Avança a MESMA demanda de geração/recebimento/renovação concluída para a fase
    de instalação (demand_type='instalacao'). Não cria uma REQ nova — é a mesma REQ
    seguindo para a próxima fase do ciclo de vida."""
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        if row['demand_type'] not in ('geracao', 'recebimento', 'renovacao'):
            raise HTTPException(400, "Só demandas de geração/recebimento/renovação podem avançar para instalação")
        if row['status'] != 'concluida':
            raise HTTPException(400, "A demanda precisa estar concluída antes de avançar para instalação")
        conn.execute("""
            UPDATE reqs SET demand_type='instalacao', status='aberta',
                           updated_at=datetime('now','localtime')
            WHERE id=?
        """, (req_id,))
        log_activity(conn, "avancou_instalacao",
                     f"Demanda {row['req_number']} avançou para fase de instalação", req_id, user["id"])
        if row['env'] == 'PRD':
            _seed_install_tasks(conn, req_id)
        conn.commit()
        return dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())


@router.post("/reqs/{req_id}/password/regenerate")
def regenerate_password(req_id: int, user=Depends(require_auth)):
    with db_conn() as conn:
        row = conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        password = _auto_password(conn)
        conn.execute("UPDATE reqs SET password=?, updated_at=datetime('now','localtime') WHERE id=?",
                     (password, req_id))
        log_activity(conn, "senha_gerada", "Senha regenerada", req_id, user["id"])
        conn.commit()
        return {"password": password}


@router.post("/reqs/{req_id}/import-previous-locations")
def import_previous_locations(req_id: int, user=Depends(require_auth)):
    """Importa locais de instalação de demandas anteriores do mesmo CN."""
    with db_conn() as conn:
        current = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not current:
            raise HTTPException(404, "Demanda não encontrada")
        
        prev_locs = conn.execute("""
            SELECT l.* FROM install_locations l
            JOIN reqs r ON r.id = l.req_id
            WHERE r.cn = ? AND r.id != ?
            ORDER BY l.id DESC
        """, (current['cn'], req_id)).fetchall()

        if not prev_locs:
            raise HTTPException(404, f"Nenhum local de instalação anterior encontrado para o CN '{current['cn']}'.")

        added = 0
        existing_servers = {
            (r['server'], r['path_or_store']) for r in conn.execute(
                "SELECT server, path_or_store FROM install_locations WHERE req_id=?", (req_id,)
            ).fetchall()
        }

        for loc_row in prev_locs:
            loc = dict(loc_row)
            key = (loc['server'], loc.get('path_or_store', ''))
            if key not in existing_servers:
                conn.execute("""
                    INSERT INTO install_locations (req_id, server, path_or_store, location_type, notes, status)
                    VALUES (?, ?, ?, ?, ?, 'pendente')
                """, (req_id, loc['server'], loc.get('path_or_store', ''), loc.get('location_type', 'outro'), loc.get('notes', '')))
                existing_servers.add(key)
                added += 1


        log_activity(conn, "locais_importados", f"Importados {added} locais de instalação de demandas anteriores do CN {current['cn']}", req_id, user["id"])
        conn.commit()
        return {"added": added}



@router.post("/reqs/{req_id}/folder")
def create_folder(req_id: int, user=Depends(require_auth)):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        base = get_setting(conn, "base_dir")
        template = get_setting(conn, "folder_template")
        folder = folders.create_structure(base, template, row["req_number"], row["cn"], row["env"])
        log_activity(conn, "pasta_criada", str(folder), req_id, user["id"])
        conn.commit()
        return {"folder": str(folder)}


@router.post("/reqs/{req_id}/locations")
def add_location(req_id: int, body: LocationIn, user=Depends(require_auth)):
    with db_conn() as conn:
        if not conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone():
            raise HTTPException(404, "Demanda não encontrada")
        cur = conn.execute(
            "INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes) "
            "VALUES (?,?,?,?,?,?)",
            (req_id, body.cert_id, body.server, body.path_or_store, body.installed_at, body.notes),
        )
        log_activity(conn, "local_adicionado", f"{body.server} · {body.path_or_store}", req_id, user["id"])
        conn.commit()
        return dict(conn.execute("SELECT * FROM install_locations WHERE id=?", (cur.lastrowid,)).fetchone())


@router.delete("/locations/{loc_id}")
def delete_location(loc_id: int, user=Depends(require_auth)):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Local não encontrado")
        conn.execute("DELETE FROM install_locations WHERE id=?", (loc_id,))
        log_activity(conn, "local_removido", f"{row['server']} · {row['path_or_store']}", row["req_id"], user["id"])
        conn.commit()
        return {"ok": True}


@router.put("/locations/{loc_id}/status")
def update_location_status(loc_id: int, body: LocationStatusUpdate, user=Depends(require_auth)):
    """Atualiza status de instalação de um local específico."""
    if body.status not in ('pendente', 'instalado', 'falhou'):
        raise HTTPException(400, "Status inválido. Use: pendente, instalado, falhou")
    with db_conn() as conn:
        loc = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
        if not loc:
            raise HTTPException(404, "Local não encontrado")
        completed = "datetime('now','localtime')" if body.status == 'instalado' else "NULL"
        conn.execute(f"""
            UPDATE install_locations
            SET status = ?, completed_at = {completed}
            WHERE id = ?
        """, (body.status, loc_id))
        log_activity(conn, "local_status_alterado",
                     f"{loc['server']} · {loc['path_or_store']}: {loc['status']} → {body.status}",
                     loc["req_id"], user["id"])
        conn.commit()
        return {"ok": True}


@router.get("/install-providers")
def list_install_providers():
    """Fonte única de verdade pro frontend montar o formulário por tipo de local."""
    result = {}
    for t in INSTALL_LOCATIONS:
        provider = PROVIDERS.get(t)
        result[t] = {
            "label": provider.label if provider else INSTALL_LOCATION_LABELS.get(t, t),
            "config_fields": provider.config_fields if provider else [],
            "available": provider is not None,
            "requires_file": provider.requires_file if provider else False,
            "key_source": provider.key_source if provider else "none",
        }
    return result


@router.get("/locations/field-values")
def location_field_values(field: str, location_type: str = ""):
    """Valores já usados nesse campo, pra autocomplete (datalist) no formulário."""
    with db_conn() as conn:
        if field in ("server", "path_or_store"):
            rows = conn.execute(
                f"SELECT DISTINCT {field} AS v FROM install_locations "
                f"WHERE {field} IS NOT NULL AND {field} != '' LIMIT 20").fetchall()
        else:
            rows = conn.execute(
                """SELECT DISTINCT json_extract(config_json, '$.' || ?) AS v
                   FROM install_locations WHERE location_type = ? LIMIT 20""",
                (field, location_type)).fetchall()
        return [r["v"] for r in rows if r["v"]]


@router.put("/locations/{loc_id}/config")
async def update_location_config(loc_id: int, location_type: str = Form(...),
                                  config_json: str = Form("{}"), credential_ref: str = Form(""),
                                  file: UploadFile | None = File(None),
                                  user=Depends(require_auth)):
    if location_type not in INSTALL_LOCATIONS:
        raise HTTPException(400, f"Tipo inválido. Use: {', '.join(INSTALL_LOCATIONS)}")
    try:
        config = json.loads(config_json)
    except ValueError:
        raise HTTPException(400, "config_json inválido")
    with db_conn() as conn:
        loc = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
        if not loc:
            raise HTTPException(404, "Local não encontrado")
        uploaded_path = loc["uploaded_file_path"]
        if file and file.filename:
            req = conn.execute("SELECT * FROM reqs WHERE id=?", (loc["req_id"],)).fetchone()
            base = get_setting(conn, "base_dir")
            template = get_setting(conn, "folder_template")
            folder = folders.create_structure(base, template, req["req_number"], req["cn"], req["env"]) / "pfx"
            safe_name = folders.sanitize(Path(file.filename).name)
            dest = folder / f"loc{loc_id}_{safe_name}"
            dest.write_bytes(await file.read())
            uploaded_path = str(dest)
        conn.execute(
            """UPDATE install_locations
               SET location_type=?, config_json=?, credential_ref=?, uploaded_file_path=?
               WHERE id=?""",
            (location_type, json.dumps(config), credential_ref, uploaded_path, loc_id))
        log_activity(conn, "local_config_alterada",
                     f"{loc['server']} · tipo {location_type}", loc["req_id"], user["id"])
        conn.commit()
        return dict(conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone())


@router.post("/locations/{loc_id}/install")
def run_install(loc_id: int, user=Depends(require_auth)):
    with db_conn() as conn:
        loc = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
        if not loc:
            raise HTTPException(404, "Local não encontrado")
        provider = PROVIDERS.get(loc["location_type"])
        if not provider:
            raise HTTPException(400, f"Tipo '{loc['location_type']}' não tem automação disponível")
        req = conn.execute("SELECT * FROM reqs WHERE id=?", (loc["req_id"],)).fetchone()
        config = json.loads(loc["config_json"] or "{}")
        result = provider.install(location=dict(loc), req=dict(req), config=config,
                                  credential_ref=loc["credential_ref"])
        run_status = "sucesso" if result.get("ok") else "falha"
        conn.execute(
            "INSERT INTO install_runs (location_id, status, output, error, triggered_by) VALUES (?,?,?,?,?)",
            (loc_id, run_status, result.get("output", ""), result.get("error", ""), user["id"]))
        conn.execute(
            """UPDATE install_locations
               SET status=?, last_error=?, last_run_at=datetime('now','localtime'),
                   completed_at=CASE WHEN ?='instalado' THEN datetime('now','localtime') ELSE completed_at END
               WHERE id=?""",
            ('instalado' if result.get("ok") else 'falhou', result.get("error", ""),
             'instalado' if result.get("ok") else 'falhou', loc_id))
        log_activity(conn, "local_instalacao_executada",
                     f"{loc['server']} · {provider.label}: {run_status}", loc["req_id"], user["id"])
        conn.commit()
        return result


@router.get("/locations/{loc_id}/runs")
def list_install_runs(loc_id: int):
    with db_conn() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT ir.*, u.display_name AS user_name FROM install_runs ir
               LEFT JOIN users u ON u.id = ir.triggered_by
               WHERE ir.location_id=? ORDER BY ir.id DESC""", (loc_id,)).fetchall()]


@router.get("/activity")
def recent_activity(limit: int = 50, page: int = 1, search: str = "",
                    user_id: int | None = None, action: str = ""):
    with db_conn() as conn:
        where = " WHERE 1=1"
        params = []
        if search:
            where += " AND (a.detail LIKE ? OR a.action LIKE ? OR r.req_number LIKE ?)"
            params += [f"%{search}%"] * 3
        if user_id is not None:
            where += " AND a.user_id = ?"
            params.append(user_id)
        if action:
            where += " AND a.action = ?"
            params.append(action)
        total = conn.execute(
            "SELECT COUNT(*) FROM activity_log a LEFT JOIN reqs r ON r.id = a.req_id" + where,
            params).fetchone()[0]
        sql = ("""SELECT a.*, r.req_number, u.display_name AS user_name FROM activity_log a
                  LEFT JOIN reqs r ON r.id = a.req_id
                  LEFT JOIN users u ON u.id = a.user_id""" + where
               + " ORDER BY a.id DESC LIMIT ? OFFSET ?")
        page = max(page, 1)
        limit = min(limit, 500)
        items = [dict(r) for r in conn.execute(
            sql, params + [limit, (page - 1) * limit]).fetchall()]
        return {"items": items, "total": total}


FLOWS: dict[str, str] = {
    "geracao": """\
flowchart TD
    A([🟢 Abertura da demanda]) --> B[Coletar informações<br/>CN, SANs, ambiente, solicitante]
    B --> C[Gerar CSR<br/>Aba **Gerar CSR** → engine local / certreq / HSM]
    C --> D[Submeter CSR à CA<br/>Portal Sectigo / AC Interna / ICP]
    D --> E[Download do certificado emitido<br/>.cer / .crt / .pem]
    E --> F[Importar certificado<br/>Aba **Certificados** → Importar]
    F --> G[Instalar certificado<br/>Ver local de instalação abaixo]
    G --> H[Validar cadeia<br/>Aba **Validar cadeia**]
    H --> I[Registrar local de instalação<br/>Aba **Demandas** → Abrir → Locais]
    I --> J[Abrir Processo de Mudança<br/>Se ambiente PRD → obrigatório]
    J --> K([✅ Concluída])

    subgraph Locais de Instalação
        L1[Mainframe — via processo RACF/ACM]
        L2[Balanceador — F5 / NetScaler]
        L3[Key Vault Azure — az keyvault certificate import]
        L4[AWS Cert Manager — aws acm import-certificate]
        L5[Azion / Akamai — portal da CDN]
    end
""",
    "renovacao": """\
flowchart TD
    A([🔄 Início da Renovação]) --> B[Identificar certificado a vencer<br/>Dashboard → Próximos vencimentos]
    B --> C{Mesma chave privada?}
    C -- Sim --> D[Reutilizar CSR existente<br/>Aba CSR Decoder → repositório]
    C -- Não --> E[Gerar nova CSR<br/>Aba Gerar CSR]
    D --> F[Submeter à CA]
    E --> F
    F --> G[Receber novo certificado]
    G --> H[Importar e validar cadeia]
    H --> I[Substituir nos locais de instalação<br/>Mesmo processo que emissão]
    I --> J[Revogar certificado antigo<br/>se necessário]
    J --> K([✅ Renovação concluída])
""",
    "revogacao": """\
flowchart TD
    A([🔴 Solicitação de Revogação]) --> B{Motivo}
    B -- Chave comprometida --> C[URGENTE: revogar imediatamente<br/>Contato direto com a CA]
    B -- Outros motivos --> D[Abrir demanda formal]
    D --> E[Identificar serial e thumbprint<br/>Aba Certificados → Detalhes]
    E --> F[Solicitar revogação à CA<br/>Portal / e-mail / API]
    F --> G[Confirmar CRL/OCSP atualizado<br/>certutil -verify -urlfetch cert.cer]
    G --> H[Remover certificado dos sistemas]
    H --> I[Documentar ocorrência]
    C --> G
    I --> J([✅ Revogação concluída])
""",
    "usuario": """\
flowchart TD
    A([👤 Certificado de Usuário]) --> B[Identificar usuário e sistema<br/>AD, e-mail, token físico?]
    B --> C{Tipo de emissão}
    C -- AC Interna --> D[Gerar CSR para o usuário<br/>ou usar template SCEP/ADCS]
    C -- ICP-Brasil --> E[Dirigir usuário à AR/AC ICP<br/>com documentação pessoal]
    D --> F[Emitir pelo servidor ADCS<br/>ou exportar PFX]
    F --> G[Entregar ao usuário<br/>com senha por canal seguro]
    E --> H[Usuário retira token/smart card]
    G --> I([✅ Certificado entregue])
    H --> I
""",
    "instalacao_existente": """\
flowchart TD
    A([📦 Instalação de Certificado Existente]) --> B[Receber arquivos<br/>.pfx / .pem / .cer + chave]
    B --> C[Importar na plataforma<br/>Aba Certificados → Importar]
    C --> D[Validar cadeia<br/>Aba Validar Cadeia]
    D --> E{Aprovação necessária?}
    E -- PRD --> F[Abrir Processo de Mudança]
    E -- Não-PRD --> G[Instalar diretamente]
    F --> H[Executar no horário aprovado]
    H --> I[Instalar e validar]
    G --> I
    I --> J[Registrar local de instalação]
    J --> K([✅ Instalação concluída])
""",
    "outro": """\
flowchart TD
    A([📋 Demanda Genérica]) --> B[Detalhar escopo]
    B --> C[Executar atividades necessárias]
    C --> D[Documentar resultado]
    D --> E([✅ Concluído])
""",
}
