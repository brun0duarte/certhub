"""Demandas (REQ): CRUD, status, locais de instalação, pastas e histórico."""
import json
import re
from contextlib import contextmanager

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import REQ_STATUSES, get_db, get_setting, log_activity
from ..services import folders, passwordgen

router = APIRouter(tags=["reqs"])
REQ_FORMAT = re.compile(r"^[A-Z0-9_\-\.]{3,30}$", re.IGNORECASE)


@contextmanager
def db_conn():
    """Context manager que garante fechamento da conexão mesmo em exceções."""
    conn = get_db()
    try:
        yield conn
    finally:
        conn.close()


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
def list_reqs(search: str = "", env: str = "", status: str = "", demand_type: str = ""):
    with db_conn() as conn:
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
        if demand_type:
            types = [t.strip() for t in demand_type.split(',')]
            sql += " AND r.demand_type IN (" + ",".join("?" for _ in types) + ")"
            params.extend(types)
        sql += " ORDER BY r.created_at DESC"
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


@router.post("/reqs")
def create_req(body: ReqIn):
    with db_conn() as conn:
        # Auto-generate REQ number if not provided
        if not body.req_number:
            cur = conn.execute(
                "SELECT req_number FROM reqs WHERE req_number LIKE 'REQ%' "
                "ORDER BY CAST(SUBSTR(req_number, 4) AS INTEGER) DESC LIMIT 1"
            )
            row = cur.fetchone()
            next_num = int(row[0][3:]) + 1 if row else 1
            req_number = f"REQ{next_num:07d}"
        else:
            req_number = body.req_number.strip().upper()
            if not REQ_FORMAT.match(req_number):
                raise HTTPException(400, "Número inválido — use letras, números, hifens ou pontos (3–30 caracteres)")

        # Block duplicate active demands for geracao/recebimento
        if body.demand_type in ('geracao', 'recebimento'):
            dup = conn.execute(
                "SELECT req_number FROM reqs WHERE cn=? AND env=? AND demand_type=? "
                "AND status NOT IN ('concluida','cancelada')",
                (body.cn.strip(), body.env, body.demand_type)
            ).fetchone()
            if dup:
                raise HTTPException(409,
                    f"Já existe demanda ativa ({dup[0]}) para este CN/ambiente. "
                    f"Conclua ou cancele a anterior antes de criar nova.")

        # Check for duplicate req_number
        existing = conn.execute("SELECT id FROM reqs WHERE req_number=?", (req_number,)).fetchone()
        if existing:
            raise HTTPException(409, f"Já existe uma demanda com número {req_number}.")

        password = body.password or (_auto_password(conn) if body.auto_password else None)
        cur = conn.execute(
            "INSERT INTO reqs (req_number, cn, env, password, notes, demand_type, parent_req_id, external_wo, external_crq, external_partner, partner_email, partner_registration) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (req_number, body.cn.strip(), body.env, password, body.notes,
             body.demand_type, body.parent_req_id, body.external_wo, body.external_crq, body.external_partner, body.partner_email, body.partner_registration),
        )


        req_id = cur.lastrowid
        log_activity(conn, "req_criada", f"{req_number} · CN {body.cn} · {body.env}", req_id)
        if password and body.auto_password and not body.password:
            log_activity(conn, "senha_gerada", "Senha gerada automaticamente na criação", req_id)
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
        if not certs and req.get("cn"):
            certs = [dict(r) for r in conn.execute(
                "SELECT * FROM certificates WHERE cn=? ORDER BY created_at DESC", (req["cn"],))]
        if not certs:
            certs = [dict(r) for r in conn.execute(
                """SELECT c.* FROM certificates c
                   JOIN install_locations l ON l.cert_id = c.id
                   WHERE l.req_id=? ORDER BY c.created_at DESC""", (req_id,))]
        req["certificates"] = certs

        req["activity"] = [dict(r) for r in conn.execute(
            "SELECT * FROM activity_log WHERE req_id=? ORDER BY id DESC LIMIT 50", (req_id,))]
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
def update_req(req_id: int, body: ReqUpdate):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        fields = {k: v for k, v in body.model_dump(exclude_unset=True).items()}
        if "status" in fields and fields["status"] not in REQ_STATUSES:
            raise HTTPException(400, f"Status inválido. Use: {', '.join(REQ_STATUSES)}")
        if "status" in fields and fields["status"] == "concluida":
            demand_type = row["demand_type"] if "demand_type" in row.keys() else "geracao"
            if demand_type in ("geracao", "recebimento", "renovacao"):
                cert_count = conn.execute("SELECT COUNT(*) FROM certificates WHERE req_id=?", (req_id,)).fetchone()[0]
                if cert_count == 0:
                    raise HTTPException(400, "🔒 Não é possível concluir esta demanda sem antes importar e vincular o certificado emitido.")

        if fields:
            sets = ", ".join(f"{k}=?" for k in fields)
            conn.execute(
                f"UPDATE reqs SET {sets}, updated_at=datetime('now','localtime') WHERE id=?",
                (*fields.values(), req_id),
            )
            if "status" in fields:
                log_activity(conn, "status_alterado", f"{row['status']} → {fields['status']}", req_id)
            conn.commit()
        return dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())


@router.delete("/reqs/{req_id}")
def delete_req(req_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT req_number FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        conn.execute("DELETE FROM reqs WHERE id=?", (req_id,))
        log_activity(conn, "req_excluida", row["req_number"])
        conn.commit()
        return {"ok": True}


@router.post("/reqs/{req_id}/advance-to-installation")
def advance_to_installation(req_id: int):
    """Avança REQ de geração/recebimento para fase de instalação."""
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        if row['demand_type'] not in ('geracao', 'recebimento'):
            raise HTTPException(400, "Só demandas de geração/recebimento podem avançar para instalação")
        conn.execute("""
            UPDATE reqs SET demand_type='instalacao', status='aberta',
                           updated_at=datetime('now','localtime')
            WHERE id=?
        """, (req_id,))
        log_activity(conn, "avancou_instalacao",
                     f"Demanda {row['req_number']} avançou para fase de instalação", req_id)
        conn.commit()
        return dict(conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone())


@router.post("/reqs/{req_id}/password/regenerate")
def regenerate_password(req_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        password = _auto_password(conn)
        conn.execute("UPDATE reqs SET password=?, updated_at=datetime('now','localtime') WHERE id=?",
                     (password, req_id))
        log_activity(conn, "senha_gerada", "Senha regenerada", req_id)
        conn.commit()
        return {"password": password}


@router.post("/reqs/{req_id}/import-previous-locations")
def import_previous_locations(req_id: int):
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


        log_activity(conn, "locais_importados", f"Importados {added} locais de instalação de demandas anteriores do CN {current['cn']}", req_id)
        conn.commit()
        return {"added": added}



@router.post("/reqs/{req_id}/folder")
def create_folder(req_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Demanda não encontrada")
        base = get_setting(conn, "base_dir")
        template = get_setting(conn, "folder_template")
        folder = folders.create_structure(base, template, row["req_number"], row["cn"], row["env"])
        log_activity(conn, "pasta_criada", str(folder), req_id)
        conn.commit()
        return {"folder": str(folder)}


@router.post("/reqs/{req_id}/locations")
def add_location(req_id: int, body: LocationIn):
    with db_conn() as conn:
        if not conn.execute("SELECT id FROM reqs WHERE id=?", (req_id,)).fetchone():
            raise HTTPException(404, "Demanda não encontrada")
        cur = conn.execute(
            "INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes) "
            "VALUES (?,?,?,?,?,?)",
            (req_id, body.cert_id, body.server, body.path_or_store, body.installed_at, body.notes),
        )
        log_activity(conn, "local_adicionado", f"{body.server} · {body.path_or_store}", req_id)
        conn.commit()
        return dict(conn.execute("SELECT * FROM install_locations WHERE id=?", (cur.lastrowid,)).fetchone())


@router.delete("/locations/{loc_id}")
def delete_location(loc_id: int):
    with db_conn() as conn:
        row = conn.execute("SELECT * FROM install_locations WHERE id=?", (loc_id,)).fetchone()
        if not row:
            raise HTTPException(404, "Local não encontrado")
        conn.execute("DELETE FROM install_locations WHERE id=?", (loc_id,))
        log_activity(conn, "local_removido", f"{row['server']} · {row['path_or_store']}", row["req_id"])
        conn.commit()
        return {"ok": True}


@router.put("/locations/{loc_id}/status")
def update_location_status(loc_id: int, body: LocationStatusUpdate):
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
        conn.commit()
        return {"ok": True}


@router.get("/activity")
def recent_activity(limit: int = 30):
    with db_conn() as conn:
        return [dict(r) for r in conn.execute(
            """SELECT a.*, r.req_number FROM activity_log a
               LEFT JOIN reqs r ON r.id = a.req_id
               ORDER BY a.id DESC LIMIT ?""", (min(limit, 200),))]


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
