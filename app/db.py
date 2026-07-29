"""Banco SQLite: conexão, schema versionado e seeds iniciais."""
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "certhub.db"

ENVS = ["PRD", "TQS", "HMP", "DES"]
REQ_STATUSES = ["aberta", "csr_gerada", "cert_emitido", "instalado", "concluida", "cancelada"]
DEMAND_TYPES = ["emissao", "renovacao", "revogacao", "usuario", "instalacao_existente", "outro"]
TASK_LANES = ["backlog", "a_fazer", "em_andamento", "concluido"]
TASK_PRIORITIES = ["alta", "media", "baixa"]
CERT_TYPES = ["servidor", "cliente_mtls", "ambos", "ca"]
CERT_CATEGORIES = [
    "sectigo_dv", "sectigo_ov", "sectigo_ev",
    "ac_interna_apl_prd", "ac_icp_testes",
    "apple", "bandeiras", "parceiro_externo", "sepro", "outro",
]
INSTALL_LOCATIONS = [
    "mainframe", "balanceador", "keyvault_azure", "aws_cert_manager",
    "secrets_manager", "azion", "akamai", "iis", "apache", "nginx",
    "tomcat", "outro",
]

WO_TYPES = ['WO', 'CRQ']
WO_STATUSES = ['aberta', 'em_andamento', 'concluida', 'cancelada']

SCHEMA = """
CREATE TABLE reqs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_number TEXT NOT NULL UNIQUE,
    cn TEXT NOT NULL,
    env TEXT NOT NULL CHECK (env IN ('PRD','TQS','HMP','DES')),
    password TEXT,
    status TEXT NOT NULL DEFAULT 'aberta',
    notes TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE certificates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    cn TEXT,
    sans TEXT DEFAULT '',
    subject TEXT,
    issuer TEXT,
    serial TEXT,
    thumbprint_sha1 TEXT,
    not_before TEXT,
    not_after TEXT,
    key_type TEXT,
    source TEXT NOT NULL DEFAULT 'importado',
    file_path TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE install_locations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER NOT NULL REFERENCES reqs(id) ON DELETE CASCADE,
    cert_id INTEGER REFERENCES certificates(id) ON DELETE SET NULL,
    server TEXT NOT NULL,
    path_or_store TEXT DEFAULT '',
    installed_at TEXT,
    notes TEXT DEFAULT ''
);

CREATE TABLE activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    action TEXT NOT NULL,
    detail TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE docs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'outros',
    content_md TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""

SCHEMA_V2 = """
CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT DEFAULT '',
    category TEXT NOT NULL DEFAULT 'geral',
    priority TEXT NOT NULL DEFAULT 'media' CHECK (priority IN ('alta','media','baixa')),
    lane TEXT NOT NULL DEFAULT 'backlog'
        CHECK (lane IN ('backlog','a_fazer','em_andamento','concluido')),
    position INTEGER NOT NULL DEFAULT 0,
    req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

SCHEMA_V3 = """
CREATE TABLE reply_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

SCHEMA_V4 = """
ALTER TABLE certificates ADD COLUMN cert_type TEXT NOT NULL DEFAULT '';
ALTER TABLE certificates ADD COLUMN issuer_cn TEXT NOT NULL DEFAULT '';
ALTER TABLE certificates ADD COLUMN parent_id INTEGER REFERENCES certificates(id);

CREATE TABLE csrs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cn TEXT,
    sans TEXT DEFAULT '',
    subject TEXT,
    key_type TEXT,
    sig_algo TEXT,
    req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    pem TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

SCHEMA_V5 = """
ALTER TABLE certificates ADD COLUMN cert_category TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN demand_type TEXT NOT NULL DEFAULT 'emissao';
ALTER TABLE reqs ADD COLUMN subject_email TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN subject_l TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN subject_st TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN subject_org TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN subject_ou TEXT NOT NULL DEFAULT '';
ALTER TABLE reqs ADD COLUMN subject_country TEXT NOT NULL DEFAULT '';
ALTER TABLE install_locations ADD COLUMN location_type TEXT NOT NULL DEFAULT 'outro';
ALTER TABLE install_locations ADD COLUMN change_required INTEGER NOT NULL DEFAULT 0;
ALTER TABLE install_locations ADD COLUMN change_ticket TEXT NOT NULL DEFAULT '';

CREATE TABLE IF NOT EXISTS batch_ops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- NOTA: As tabelas batch_ops e batch_op_items estão depreciadas (removidas do sistema).
-- Mantidas aqui para garantir a retrocompatibilidade da migração V5.

CREATE TABLE IF NOT EXISTS batch_op_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id INTEGER NOT NULL REFERENCES batch_ops(id) ON DELETE CASCADE,
    req_id   INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    position INTEGER NOT NULL DEFAULT 0,
    req_number TEXT NOT NULL DEFAULT '',
    cn TEXT NOT NULL DEFAULT '',
    password TEXT,
    status TEXT NOT NULL DEFAULT 'pendente',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

SCHEMA_V6 = """
ALTER TABLE activity_log ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE reqs ADD COLUMN assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    role TEXT NOT NULL DEFAULT 'viewer'
        CHECK (role IN ('admin','operator','viewer')),
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL DEFAULT '',
    active INTEGER NOT NULL DEFAULT 1,
    must_change_password INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    expires_at TEXT NOT NULL,
    ip_addr TEXT DEFAULT ''
);
"""

SCHEMA_V7 = """
ALTER TABLE reqs ADD COLUMN wo_number TEXT NOT NULL DEFAULT '';

CREATE TABLE work_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wo_number TEXT NOT NULL UNIQUE,
    wo_type TEXT NOT NULL DEFAULT 'WO'
        CHECK (wo_type IN ('WO','CRQ')),
    req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    parent_req_id INTEGER REFERENCES reqs(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT '',
    description TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'aberta'
        CHECK (status IN ('aberta','em_andamento','concluida','cancelada')),
    scheduled_at TEXT,
    completed_at TEXT,
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

LIFECYCLE_STATUSES = ['pedido', 'instalado', 'em_inventario', 'reservado', 'excluir', 'fim_de_vida']

SCHEMA_V8 = """
ALTER TABLE certificates ADD COLUMN lifecycle_status TEXT NOT NULL DEFAULT 'em_inventario'
    CHECK (lifecycle_status IN ('pedido','instalado','em_inventario','reservado','excluir','fim_de_vida'));
"""

DEFAULT_SETTINGS = {
    "base_dir": str(DATA_DIR / "files"),
    "folder_template": "{env}/{req}_{cn}",
    "alert_days": "30,60,90",
    "password_policy": json.dumps({
        "length": 16, "upper": True, "lower": True,
        "digits": True, "symbols": True, "exclude_ambiguous": True,
    }),
    "csr_default_engine": "local",
    "hsmutil_templates": json.dumps({
        "gen_key": "",
        "gen_csr": "",
        "export_key": "",
    }),
}


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "files").mkdir(parents=True, exist_ok=True)
    conn = get_db()
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        conn.executescript(SCHEMA)
        _seed(conn)
        conn.execute("PRAGMA user_version = 1")
        conn.commit()
    if version < 2:
        conn.executescript(SCHEMA_V2)
        _seed_tasks(conn)
        conn.execute("PRAGMA user_version = 2")
        conn.commit()
    if version < 3:
        conn.executescript(SCHEMA_V3)
        for name, content in SEED_TEMPLATES:
            conn.execute("INSERT INTO reply_templates (name, content) VALUES (?,?)",
                         (name, content))
        conn.execute("PRAGMA user_version = 3")
        conn.commit()
    if version < 4:
        conn.executescript(SCHEMA_V4)
        conn.execute("PRAGMA user_version = 4")
        conn.commit()
    if version < 5:
        conn.executescript(SCHEMA_V5)
        conn.execute("PRAGMA user_version = 5")
        conn.commit()
    if version < 6:
        conn.executescript(SCHEMA_V6)
        _seed_v6(conn)
        conn.execute("PRAGMA user_version = 6")
        conn.commit()
    if version < 7:
        conn.executescript(SCHEMA_V7)
        conn.execute("PRAGMA user_version = 7")
        conn.commit()
    if version < 8:
        conn.executescript(SCHEMA_V8)
        conn.execute("PRAGMA user_version = 8")
        conn.commit()
    conn.close()


def log_activity(conn, action: str, detail: str = "", req_id=None):
    conn.execute(
        "INSERT INTO activity_log (req_id, action, detail) VALUES (?,?,?)",
        (req_id, action, detail),
    )


def get_setting(conn, key: str) -> str:
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULT_SETTINGS.get(key, "")


def _seed(conn):
    for k, v in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?,?)", (k, v))
    for title, category, content in SEED_DOCS:
        conn.execute(
            "INSERT INTO docs (title, category, content_md) VALUES (?,?,?)",
            (title, category, content),
        )


def _seed_v6(conn):
    from app.services.auth import hash_password
    pwd_hash, pwd_salt = hash_password("certhub@2025")
    conn.execute(
        """
        INSERT OR IGNORE INTO users (username, display_name, email, role, password_hash, salt)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        ("admin", "Administrador", "admin@certhub.local", "admin", pwd_hash, pwd_salt)
    )


def _seed_tasks(conn):
    for pos, (title, description, category, priority, lane) in enumerate(SEED_TASKS, start=1):
        conn.execute(
            "INSERT INTO tasks (title, description, category, priority, lane, position) "
            "VALUES (?,?,?,?,?,?)",
            (title, description, category, priority, lane, pos),
        )


SEED_TASKS = [
    ("Validação de cadeia de certificados",
     "Nova aba/seção: upload do certificado + intermediárias (ou fetch via AIA), montar e "
     "validar a cadeia com cryptography (x509.verification) e mostrar veredito visual — "
     "cadeia OK ou quebrada em qual elo, validade e hostname.",
     "certhub", "alta", "a_fazer"),
    ("Toolbox OpenSSL (PFX ⇄ crt/key)",
     "Interface gráfica para as operações mais comuns: extrair .crt/.key de um .pfx, montar "
     "PFX a partir de crt+key+cadeia, converter PEM⇄DER e conferir se chave/CSR/cert combinam "
     "(modulus). Implementar com cryptography.hazmat (pkcs12) — sem depender do openssl no PATH — "
     "e exibir o comando openssl equivalente ao lado.",
     "certhub", "alta", "a_fazer"),
    ("Wiki da equipe no SharePoint",
     "Criar o site/páginas no SharePoint: como solicitar serviços (gerar, revogar, instalar "
     "certificados), normativos que regem os processos, tutoriais e links úteis. Estruturar o "
     "conteúdo em formato pergunta-resposta para servir de base de conhecimento do assistente.",
     "wiki", "alta", "a_fazer"),
    ("Assistente virtual no Copilot Studio",
     "Criar o agente no Copilot Studio usando a wiki do SharePoint como knowledge source; "
     "publicar no Teams para a equipe e para quem tem dúvidas sobre solicitações e normativos.",
     "wiki", "media", "backlog"),
    ("Criptografar senhas das REQs",
     "Substituir senhas em texto puro por senha mestra + PBKDF2/Fernet.",
     "certhub", "media", "backlog"),
    ("Helper Node.js para HSM Dinamo",
     "Integração via SDK JS da Dinamo (app/services/hsm/dinamo_js.py) em vez de templates hsmutil.",
     "hsm", "baixa", "backlog"),
]


SEED_TEMPLATES = [
    ("Certificado emitido — aviso ao solicitante", """\
Prezado(a),

O certificado referente à demanda {req} foi emitido com sucesso.

  • CN / URL: {cn}
  • Ambiente: {env}
  • Emissor: {emissor}
  • Válido até: {vencimento}

A senha do arquivo PFX será encaminhada por canal seguro.
Qualquer dúvida sobre a instalação, estamos à disposição.

Atenciosamente,
Equipe de Criptografia"""),
    ("Certificado instalado — encerramento da demanda", """\
Prezado(a),

Informamos que a demanda {req} foi concluída.

  • Certificado: {cn}
  • Ambiente: {env}
  • Instalado em: {locais}
  • Válido até: {vencimento}

A cadeia de certificação foi validada após a instalação.
A demanda será encerrada em {data}.

Atenciosamente,
Equipe de Criptografia"""),
    ("Solicitação de informações complementares", """\
Prezado(a),

Para dar andamento à demanda {req}, precisamos das seguintes informações:

  1. CN / URL do certificado (confirmar: {cn})
  2. Ambiente de destino (PRD, TQS, HMP ou DES)
  3. Servidor(es) onde será instalado
  4. Nomes alternativos (SANs), se houver
  5. Responsável técnico pela instalação

A demanda permanecerá aguardando retorno.

Atenciosamente,
Equipe de Criptografia"""),
]


SEED_DOCS = [
    ("Cheatsheet certutil", "certutil", """\
# certutil — comandos úteis

## Consultar certificados
```
certutil -store My                      :: lista o repositório pessoal (máquina)
certutil -user -store My               :: repositório do usuário
certutil -store My "<thumbprint>"      :: detalhes de um certificado
certutil -dump certificado.cer         :: inspeciona um arquivo de certificado
certutil -dump arquivo.pfx             :: inspeciona um PFX (pede a senha)
```

## Importar / exportar
```
certutil -importPFX arquivo.pfx                    :: importa PFX na máquina (LocalMachine\\My)
certutil -f -p "SENHA" -importPFX arquivo.pfx      :: importa com senha, sobrescrevendo
certutil -exportPFX My "<thumbprint>" saida.pfx    :: exporta para PFX
certutil -addstore Root ca-raiz.cer                :: instala CA raiz confiável
certutil -addstore CA intermediaria.cer            :: instala CA intermediária
certutil -delstore My "<thumbprint>"               :: remove certificado
```

## Diagnóstico
```
certutil -verify -urlfetch certificado.cer   :: valida cadeia + revogação (CRL/OCSP)
certutil -repairstore My "<thumbprint>"      :: reassocia chave privada ao certificado
certutil -viewstore My                       :: abre visualização gráfica
```
"""),
    ("certreq — gerar CSR no Windows", "certreq", """\
# certreq — CSR via arquivo .inf

## 1. Criar o arquivo `request.inf`
```ini
[NewRequest]
Subject = "CN=www.exemplo.com.br, O=Empresa, C=BR"
KeyLength = 2048
KeySpec = 1
Exportable = TRUE
MachineKeySet = TRUE
ProviderName = "Microsoft RSA SChannel Cryptographic Provider"
RequestType = PKCS10
HashAlgorithm = sha256

[Extensions]
2.5.29.17 = "{text}"
_continue_ = "dns=www.exemplo.com.br&"
_continue_ = "dns=exemplo.com.br"
```

## 2. Gerar a CSR
```
certreq -new request.inf pedido.csr
```

## 3. Instalar o certificado emitido pela CA
```
certreq -accept certificado.cer
```
> O `-accept` deve rodar na MESMA máquina onde a CSR foi gerada — é lá que está a chave privada.

Dica: a aba **Gerar CSR** deste app monta o `.inf` automaticamente com CN e SANs.
"""),
    ("Cheatsheet OpenSSL", "openssl", """\
# OpenSSL — comandos úteis

## Gerar chave + CSR
```
openssl req -new -newkey rsa:2048 -nodes -keyout dominio.key -out dominio.csr \\
  -subj "/CN=www.exemplo.com.br/O=Empresa/C=BR"

# Conferir a CSR
openssl req -in dominio.csr -noout -text
```

## Inspecionar certificados
```
openssl x509 -in cert.cer -noout -text            :: detalhes
openssl x509 -in cert.cer -noout -dates           :: validade
openssl x509 -in cert.cer -noout -fingerprint -sha1
openssl s_client -connect host:443 -servername host   :: certificado de um servidor
```

## Conversões
```
openssl x509 -inform der -in cert.der -out cert.pem            :: DER -> PEM
openssl pkcs12 -export -out cert.pfx -inkey dominio.key \\
  -in cert.cer -certfile cadeia.cer                            :: montar PFX
openssl pkcs12 -in cert.pfx -out cert.pem -nodes               :: PFX -> PEM (cert+chave)
openssl pkcs12 -in cert.pfx -nocerts -nodes -out chave.key     :: só a chave
openssl pkcs12 -in cert.pfx -clcerts -nokeys -out cert.cer     :: só o certificado
```

## Verificações
```
# Chave, CSR e certificado combinam? (os 3 hashes devem ser iguais)
openssl rsa  -in dominio.key -noout -modulus | openssl md5
openssl req  -in dominio.csr -noout -modulus | openssl md5
openssl x509 -in cert.cer    -noout -modulus | openssl md5
```
"""),
    ("Cheatsheet keytool (Java)", "keytool", """\
# keytool — keystores Java (Tomcat, aplicações Java)

## Gerar keystore + CSR
```
keytool -genkeypair -alias meusite -keyalg RSA -keysize 2048 \\
  -keystore keystore.jks -dname "CN=www.exemplo.com.br, O=Empresa, C=BR" \\
  -ext SAN=dns:www.exemplo.com.br,dns:exemplo.com.br

keytool -certreq -alias meusite -keystore keystore.jks -file pedido.csr \\
  -ext SAN=dns:www.exemplo.com.br,dns:exemplo.com.br
```

## Importar certificados emitidos (ordem: raiz -> intermediária -> final)
```
keytool -importcert -alias raiz -file ca-raiz.cer -keystore keystore.jks -trustcacerts
keytool -importcert -alias intermediaria -file ca-int.cer -keystore keystore.jks
keytool -importcert -alias meusite -file certificado.cer -keystore keystore.jks
```

## Consultas e conversões
```
keytool -list -v -keystore keystore.jks                     :: listar conteúdo
keytool -importkeystore -srckeystore cert.pfx -srcstoretype PKCS12 \\
  -destkeystore keystore.jks -deststoretype JKS             :: PFX -> JKS
keytool -importkeystore -srckeystore keystore.jks \\
  -destkeystore cert.p12 -deststoretype PKCS12              :: JKS -> PFX/P12
```
"""),
    ("Manual: instalar certificado no IIS", "manual", """\
# Instalação de certificado — IIS (Windows Server)

## Via PFX (mais comum)
1. Copie o `.pfx` para o servidor.
2. `certutil -f -p "SENHA" -importPFX certificado.pfx` (ou clique duplo -> LocalMachine -> Pessoal).
3. Abra o **Gerenciador do IIS** -> site -> **Bindings** -> `https` -> selecione o novo certificado.
4. Reinicie o site se necessário (`iisreset` só em último caso).

## Via CSR gerada no próprio servidor (certreq)
1. Gere a CSR com `certreq -new request.inf pedido.csr` (use a aba Gerar CSR).
2. Submeta a CSR à CA e baixe o certificado emitido.
3. `certreq -accept certificado.cer` **na mesma máquina**.
4. Ajuste o binding no IIS como acima.

## Checklist pós-instalação
- [ ] Cadeia completa instalada (raiz e intermediárias em seus repositórios)
- [ ] `certutil -verify -urlfetch certificado.cer` sem erros
- [ ] Site abre com cadeado / sem aviso no navegador
- [ ] Registrar local de instalação na demanda (aba Demandas)
"""),
    ("Manual: instalar certificado no Tomcat/Java", "manual", """\
# Instalação de certificado — Tomcat / aplicações Java

1. Localize (ou crie) o keystore usado pelo Tomcat (`server.xml`, conector HTTPS -> `keystoreFile`).
2. Importe a cadeia e o certificado no keystore (ver *Cheatsheet keytool*).
   - Se o certificado veio como PFX: converta com `keytool -importkeystore -srcstoretype PKCS12`.
3. Confira o alias e a senha no `server.xml`:
```xml
<Connector port="8443" scheme="https" secure="true" SSLEnabled="true"
    keystoreFile="conf/keystore.jks" keystorePass="SENHA" keyAlias="meusite" />
```
4. Reinicie o Tomcat.
5. Valide: `openssl s_client -connect host:8443 -servername host | openssl x509 -noout -dates`
6. Registre o local de instalação na demanda.
"""),
    ("Manual: instalar certificado no Apache/Nginx", "manual", """\
# Instalação de certificado — Apache / Nginx (Linux)

## Arquivos necessários
- `dominio.key` (chave privada), `certificado.crt`, `cadeia.crt` (intermediárias)
- Se recebeu PFX: extraia com openssl (ver *Cheatsheet OpenSSL* -> Conversões).

## Apache
```apache
SSLEngine on
SSLCertificateFile      /etc/ssl/certs/certificado.crt
SSLCertificateKeyFile   /etc/ssl/private/dominio.key
SSLCertificateChainFile /etc/ssl/certs/cadeia.crt
```
`apachectl configtest && systemctl reload apache2`

## Nginx (certificado + cadeia concatenados)
```
cat certificado.crt cadeia.crt > fullchain.crt
```
```nginx
ssl_certificate     /etc/ssl/certs/fullchain.crt;
ssl_certificate_key /etc/ssl/private/dominio.key;
```
`nginx -t && systemctl reload nginx`

## Validação
```
openssl s_client -connect host:443 -servername host -showcerts
```
"""),
]
