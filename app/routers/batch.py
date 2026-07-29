"""Operações em lote: múltiplas demandas simultâneas com geração de senha e fluxo Mermaid."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..db import get_db, log_activity
from ..services import passwordgen
import json

router = APIRouter(tags=["batch"])


# --------------- Mermaid flows por tipo de demanda ---------------

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


# --------------- Models ---------------

class BatchIn(BaseModel):
    name: str = ""


class BatchItemIn(BaseModel):
    req_number: str = ""
    cn: str = ""
    req_id: int | None = None
    demand_type: str = "emissao"
    notes: str = ""
    auto_password: bool = True
    password: str | None = None


class BatchItemUpdate(BaseModel):
    req_number: str | None = None
    cn: str | None = None
    demand_type: str | None = None
    notes: str | None = None
    status: str | None = None
    password: str | None = None
    req_id: int | None = None


# --------------- Endpoints ---------------

@router.get("/batch")
def list_batches():
    conn = get_db()
    rows = [dict(r) for r in conn.execute(
        """SELECT b.*, COUNT(i.id) AS item_count
           FROM batch_ops b
           LEFT JOIN batch_op_items i ON i.batch_id = b.id
           GROUP BY b.id ORDER BY b.created_at DESC"""
    ).fetchall()]
    conn.close()
    return rows


@router.get("/batch/flows")
def get_flows():
    return FLOWS


@router.get("/batch/flows/{demand_type}")
def get_flow(demand_type: str):
    flow = FLOWS.get(demand_type)
    if not flow:
        raise HTTPException(404, f"Fluxo não encontrado para tipo '{demand_type}'")
    return {"demand_type": demand_type, "mermaid": flow}


@router.post("/batch")
def create_batch(body: BatchIn):
    conn = get_db()
    cur = conn.execute("INSERT INTO batch_ops (name) VALUES (?)", (body.name or "Lote sem nome",))
    batch_id = cur.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM batch_ops WHERE id=?", (batch_id,)).fetchone())
    conn.close()
    return row


@router.get("/batch/{batch_id}")
def get_batch(batch_id: int):
    conn = get_db()
    batch = conn.execute("SELECT * FROM batch_ops WHERE id=?", (batch_id,)).fetchone()
    if not batch:
        conn.close()
        raise HTTPException(404, "Lote não encontrado")
    items = [dict(r) for r in conn.execute(
        """SELECT i.*, r.req_number AS linked_req_number, r.status AS req_status,
                  r.env AS env
           FROM batch_op_items i
           LEFT JOIN reqs r ON r.id = i.req_id
           WHERE i.batch_id = ?
           ORDER BY i.position, i.id""", (batch_id,)
    ).fetchall()]
    result = dict(batch)
    result["items"] = items
    conn.close()
    return result


@router.delete("/batch/{batch_id}")
def delete_batch(batch_id: int):
    conn = get_db()
    row = conn.execute("SELECT id FROM batch_ops WHERE id=?", (batch_id,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Lote não encontrado")
    conn.execute("DELETE FROM batch_ops WHERE id=?", (batch_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/batch/{batch_id}/items")
def add_batch_item(batch_id: int, body: BatchItemIn):
    conn = get_db()
    if not conn.execute("SELECT id FROM batch_ops WHERE id=?", (batch_id,)).fetchone():
        conn.close()
        raise HTTPException(404, "Lote não encontrado")

    # generate password
    if body.auto_password and not body.password:
        try:
            from ..services import passwordgen as pwdgen
            import json as _json
            from ..db import get_setting
            policy = _json.loads(get_setting(conn, "password_policy"))
            password = pwdgen.generate(**policy)
        except Exception:
            import secrets, string
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
    else:
        password = body.password or None

    pos = (conn.execute(
        "SELECT COALESCE(MAX(position),0) FROM batch_op_items WHERE batch_id=?", (batch_id,)
    ).fetchone()[0] or 0) + 1

    cur = conn.execute(
        """INSERT INTO batch_op_items
           (batch_id, req_id, req_number, cn, password, status, notes, position)
           VALUES (?,?,?,?,?,?,?,?)""",
        (batch_id, body.req_id, body.req_number.strip().upper(),
         body.cn.strip(), password, "pendente", body.notes, pos),
    )
    item_id = cur.lastrowid
    conn.commit()
    row = dict(conn.execute("SELECT * FROM batch_op_items WHERE id=?", (item_id,)).fetchone())
    conn.close()
    return row


@router.put("/batch/{batch_id}/items/{item_id}")
def update_batch_item(batch_id: int, item_id: int, body: BatchItemUpdate):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM batch_op_items WHERE id=? AND batch_id=?", (item_id, batch_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Item não encontrado")
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if fields:
        sets = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE batch_op_items SET {sets} WHERE id=?",
            (*fields.values(), item_id),
        )
        conn.commit()
    updated = dict(conn.execute("SELECT * FROM batch_op_items WHERE id=?", (item_id,)).fetchone())
    conn.close()
    return updated


@router.delete("/batch/{batch_id}/items/{item_id}")
def delete_batch_item(batch_id: int, item_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM batch_op_items WHERE id=? AND batch_id=?", (item_id, batch_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Item não encontrado")
    conn.execute("DELETE FROM batch_op_items WHERE id=?", (item_id,))
    conn.commit()
    conn.close()
    return {"ok": True}


@router.post("/batch/{batch_id}/items/{item_id}/regen-password")
def regen_batch_item_password(batch_id: int, item_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM batch_op_items WHERE id=? AND batch_id=?", (item_id, batch_id)
    ).fetchone()
    if not row:
        conn.close()
        raise HTTPException(404, "Item não encontrado")
    try:
        import json as _json
        from ..db import get_setting
        from ..services import passwordgen as pwdgen
        policy = _json.loads(get_setting(conn, "password_policy"))
        password = pwdgen.generate(**policy)
    except Exception:
        import secrets, string
        alphabet = string.ascii_letters + string.digits + "!@#$%"
        password = "".join(secrets.choice(alphabet) for _ in range(16))
    conn.execute("UPDATE batch_op_items SET password=? WHERE id=?", (password, item_id))
    conn.commit()
    conn.close()
    return {"password": password}


@router.post("/batch/regen-all-passwords/{batch_id}")
def regen_all_passwords(batch_id: int):
    conn = get_db()
    items = conn.execute(
        "SELECT id FROM batch_op_items WHERE batch_id=?", (batch_id,)
    ).fetchall()
    if not items:
        conn.close()
        raise HTTPException(404, "Lote vazio ou não encontrado")
    try:
        import json as _json
        from ..db import get_setting
        from ..services import passwordgen as pwdgen
        policy = _json.loads(get_setting(conn, "password_policy"))
    except Exception:
        policy = {"length": 16, "upper": True, "lower": True,
                  "digits": True, "symbols": True, "exclude_ambiguous": True}
    count = 0
    for item in items:
        try:
            password = pwdgen.generate(**policy)
        except Exception:
            import secrets, string
            alphabet = string.ascii_letters + string.digits + "!@#$%"
            password = "".join(secrets.choice(alphabet) for _ in range(16))
        conn.execute("UPDATE batch_op_items SET password=? WHERE id=?", (password, item["id"]))
        count += 1
    conn.commit()
    conn.close()
    return {"updated": count}
