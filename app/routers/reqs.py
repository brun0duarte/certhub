"""Demandas (REQ): CRUD, status, locais de instalação, pastas e histórico."""
import json
import re

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import REQ_STATUSES, get_db, get_setting, log_activity
from ..services import folders, passwordgen

router = APIRouter(tags=["reqs"])

REQ_FORMAT = re.compile(r"^REQ\d{7}$", re.IGNORECASE)


class ReqIn(BaseModel):
    req_number: str
    cn: str
    env: str
    notes: str = ""
    password: str | None = None
    auto_password: bool = True
    demand_type: str = "emissao"


class ReqUpdate(BaseModel):
    cn: str | None = None
    env: str | None = None
    notes: str | None = None
    password: str | None = None
    status: str | None = None
    demand_type: str | None = None


class LocationIn(BaseModel):
    server: str
    path_or_store: str = ""
    installed_at: str | None = None
    notes: str = ""
    cert_id: int | None = None


def _auto_password(conn) -> str:
    policy = json.loads(get_setting(conn, "password_policy"))
    return passwordgen.generate(**policy)


@router.get("/reqs")
def list_reqs(search: str = "", env: str = "", status: str = ""):
    conn = get_db()
    sql = """SELECT r.*,
                    (SELECT COUNT(*) FROM certificates c WHERE c.req_id = r.id) AS cert_count,
                    (SELECT COUNT(*) FROM install_locations l WHERE l.req_id = r.id) AS location_count
             FROM reqs r WHERE 1=1"""
    params = []
    if search:
        sql += " AND (r.req_number LIKE ? OR r.cn LIKE ? OR r.notes LIKE ?)"
        params += [f"%{search}%"] * 3
    if env:
        sql += " AND r.env = ?"
        params.append(env)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.created_at DESC"
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows


@router.post("/reqs")
def create_req(body: ReqIn):
    req_number = body.req_number.strip().upper()
    if not REQ_FORMAT.match(req_number):
        raise HTTPException(400, "Número de REQ inválido — formato esperado: REQ0012345")
    conn = get_db()
    password = body.password or (_auto_password(conn) if body.auto_password else None)
    try:
        cur = conn.execute(
            "INSERT INTO reqs (req_number, cn, env, password, notes, demand_type) VALUES (?,?,?,?,?,?)",
            (req_number, body.cn.strip(), body.env, password, body.notes, body.demand_type),
        )
    except Exception:
        conn.close()
        raise HTTPException(409, f"Já existe uma demanda {req_number}.")
    req_id = cur.lastrowid
    log_activity(conn, "req_criada", f"{req_number} · CN {body.cn} · {body.env}", req_id)
    if password and body.auto_password and not body.password:
        log_activity(conn, "senha_gerada", "Senha gerada automaticamente na criação", req_id)
    conn.commit()
    row = dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())
    conn.close()
    return row


@router.get("/reqs/{req_id}")
def get_req(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    req = dict(row)
    req["locations"] = [dict(r) for r in conn.execute(
        "SELECT * FROM install_locations WHERE req_id=? ORDER BY id", (req_id,))]
    req["certificates"] = [dict(r) for r in conn.execute(
        "SELECT * FROM certificates WHERE req_id=? ORDER BY created_at DESC", (req_id,))]
    req["activity"] = [dict(r) for r in conn.execute(
        "SELECT * FROM activity_log WHERE req_id=? ORDER BY id DESC LIMIT 50", (req_id,))]
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"])
    req["folder"] = str(folder)
    req["folder_exists"] = folder.exists()
    conn.close()
    return req


@router.put("/reqs/{req_id}")
def update_req(req_id: int, body: ReqUpdate):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if "status" in fields and fields["status"] not in REQ_STATUSES:
        conn.close()
        raise HTTPException(400, f"Status inválido. Use: {', '.join(REQ_STATUSES)}")
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE reqs SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
            (*fields.values(), req_id),
        )
        if "status" in fields:
            log_activity(conn, "status_alterado", f"{row['status']} → {fields['status']}", req_id)
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())
    
    if updated["status"] == "cert_emitido":
        existing_wo = conn.execute("SELECT id FROM work_orders WHERE parent_req_id=?", (req_id,)).fetchone()
        if not existing_wo:
            updated["suggest_wo"] = True
            updated["suggested_wo_type"] = "CRQ" if updated["env"] == "PRD" else "WO"

    conn.close()
    return updated


@router.delete("/reqs/{req_id}")
def delete_req(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT req_number FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    conn.execute("DELETE FROM reqs WHERE id=?", (req_id,))
    log_activity(conn, "req_excluida", row["req_number"])
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/reqs/{req_id}/password/regenerate")
def regenerate_password(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    password = _auto_password(conn)
    conn.execute("UPDATE reqs SET password=?, updated_at=datetime('now','localtime') WHERE id=?",
                 (password, req_id))
    log_activity(conn, "senha_gerada", "Senha regenerada", req_id)
    conn.commit()
    conn.close()
    return {"password": password}


@router.post("/reqs/{req_id}/folder")
def create_folder(req_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.create_structure(base, template, row["req_number"], row["cn"], row["env"])
    log_activity(conn, "pasta_criada", str(folder), req_id)
    conn.commit()
    conn.close()
    return {"folder": str(folder)}


@router.post("/reqs/{req_id}/locations")
def add_location(req_id: int, body: LocationIn):
    conn = get_db()
    if not conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Demanda não encontrada")
    cur = conn.execute(
        "INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes) "
        "VALUES (?,?,?,?,?,?)",
        (req_id, body.cert_id, body.server, body.path_or_store, body.installed_at, body.notes),
    )
    log_activity(conn, "local_adicionado", f"{body.server} · {body.path_or_store}", req_id)
    conn.commit()
    row = dict(conn.execute("SELECT * FROM install_locations WHERE id=?", (cur.lastrowid,)).fetchone())
    conn.close()
    return row


@router.delete("/locations/{loc_id}")
def delete_location(loc_id: int):
    conn = get_db()
    row = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Local não encontrado")
    conn.execute("DELETE FROM install_locations WHERE id=?", (loc_id,))
    log_activity(conn, "local_removido", f"{row['server']} · {row['path_or_store']}", row["req_id"])
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/activity")
def recent_activity(limit: int = 30):
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT a.*, r.req_number FROM activity_log a
           LEFT JOIN reqs r ON r.id = a.req_id
           ORDER BY a.id DESC LIMIT ?""", (min(limit, 200),))]
    conn.close()
    return rows

FLOWS: dict[str, str] = {
    "emissao": """\
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

@router.get("/reqs/flows")
def get_flows():
    return FLOWS

@router.get("/reqs/flows/{demand_type}")
def get_flow(demand_type: str):
    flow = FLOWS.get(demand_type)
    if not flow:
        raise HTTPException(404, f"Fluxo não encontrado para tipo '{demand_type}'")
    return {"demand_type": demand_type, "mermaid": flow}
