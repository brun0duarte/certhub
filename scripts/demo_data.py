"""Popula o CertHub com dados fictícios (domínio bancofic.com.br) para demonstração.

Uso:
    .venv/bin/python scripts/demo_data.py             # cria os dados (22 exemplos narrativos + 150 aleatórios)
    .venv/bin/python scripts/demo_data.py --bulk 500  # troca a quantidade de certificados aleatórios (0 desativa)
    .venv/bin/python scripts/demo_data.py --remove    # remove tudo que foi criado

Marcadores usados na remoção: reqs.notes contém [demo], certificates.source='demo',
csrs.subject contém O=BancoFic, activity_log.detail contém [demo]. Os usuários de
demonstração (alex, bruno, carlos, davi, leonardo) NÃO são removidos por --remove —
mesma política de scripts/reset_seed.py, que preserva contas de usuário.
"""
import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.db import get_db, get_setting, init_db
from app.services import certparse, folders
from app.services.auth import hash_password

DEMO_USERS = [
    ("alex", "Alex Souza", "admin"),
    ("bruno", "Bruno Duarte", "admin"),
    ("carlos", "Carlos Lima", "operator"),
    ("davi", "Davi Nogueira", "operator"),
    ("leonardo", "Leonardo Alves", "viewer"),
]

DEMO_DOCS = [
    {
        "title": 'Instalação de certificado — Azure Key Vault',
        "category": 'manual',
        "content_md": '# Instalação de certificado — Azure Key Vault\n\n## Via CLI (`az`)\nPrecisa do PFX (cert + chave privada) e da senha.\n```bash\naz keyvault certificate import \\\n  --vault-name MEUKEYVAULT \\\n  --name meu-certificado \\\n  --file certificado.pfx \\\n  --password "SENHA_DO_PFX"\n```\nSem senha (PEM com chave, sem criptografia) funciona do mesmo jeito, só sem `--password`.\n\n## Via API REST\n```\nPUT https://MEUKEYVAULT.vault.azure.net/certificates/meu-certificado/import?api-version=7.4\nAuthorization: Bearer <token>\nContent-Type: application/json\n\n{\n  "value": "<PFX em base64>",\n  "pwd": "SENHA_DO_PFX"\n}\n```\nToken via `az account get-access-token --resource https://vault.azure.net`.\n\n## Rotação (renovação)\nReimportar com o mesmo `--name` cria uma **nova versão** — versões antigas continuam\ndisponíveis (útil pra rollback) e a versão mais recente vira a "current" automaticamente\npros consumidores que buscam sem pinar versão específica.\n\n## Validação\n```bash\naz keyvault certificate show --vault-name MEUKEYVAULT --name meu-certificado \\\n  --query "{thumbprint: x509ThumbprintHex, expires: attributes.expires}"\n```\n\n## Checklist pós-instalação\n- [ ] Aplicação/serviço aponta pro Key Vault com a permissão correta (RBAC ou Access Policy — `get`/`list` no mínimo)\n- [ ] Se o consumidor pina versão, atualizar a referência pra nova versão\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Automatizável de ponta a ponta (CLI/API/SDK) — não exige acesso manual ao portal.\n',
    },
    {
        "title": 'Instalação de certificado — AWS Certificate Manager e Secrets Manager',
        "category": 'manual',
        "content_md": '# Instalação de certificado — AWS ACM e Secrets Manager\n\n## AWS Certificate Manager (ACM) — importar certificado de terceiros\nACM não emite o certificado pra você aqui (isso é o fluxo de geração normal) — este é o\nfluxo de **importar** um certificado já emitido por uma CA externa, pra usar em\nALB/CloudFront/API Gateway etc.\n```bash\naws acm import-certificate \\\n  --certificate fileb://certificado.pem \\\n  --private-key fileb://chave.pem \\\n  --certificate-chain fileb://cadeia.pem\n```\nGuarde o `CertificateArn` retornado.\n\n### Renovar (reimportar sobre o mesmo ARN)\n```bash\naws acm import-certificate \\\n  --certificate-arn arn:aws:acm:regiao:conta:certificate/xxxx \\\n  --certificate fileb://novo-certificado.pem \\\n  --private-key fileb://nova-chave.pem \\\n  --certificate-chain fileb://cadeia.pem\n```\nServiços que já referenciam o ARN (ALB listener, CloudFront distribution) atualizam\nautomaticamente — não precisa trocar a referência.\n\n## AWS Secrets Manager — guardar PFX/chave pra app buscar em runtime\nÚtil quando a aplicação não roda atrás de um recurso gerenciado pela AWS que aceite ACM\ndireto (ex: app própria em EC2/ECS que lê o cert do código).\n```bash\n# criar\naws secretsmanager create-secret --name meu-certificado \\\n  --secret-binary fileb://certificado.pfx\n\n# atualizar (renovação)\naws secretsmanager put-secret-value --secret-id meu-certificado \\\n  --secret-binary fileb://certificado-novo.pfx\n```\n\n## Validação\n```bash\naws acm describe-certificate --certificate-arn arn:aws:acm:... \\\n  --query "Certificate.{status:Status,expires:NotAfter}"\n```\n\n## Checklist pós-instalação\n- [ ] ARN correto associado ao listener/distribution (ACM) ou secret referenciado pela app (Secrets Manager)\n- [ ] Certificado no ACM está `ISSUED` (não `PENDING_VALIDATION`)\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Automatizável de ponta a ponta (CLI/API/SDK/Terraform). ACM cuida de renovação\n> automática só pros certificados que ele mesmo emite — os importados precisam ser\n> reimportados manualmente ou via automação antes de vencer.\n',
    },
    {
        "title": 'Instalação de certificado — Mainframe RACDCERT (RACF / z/OS)',
        "category": 'manual',
        "content_md": "# Instalação de certificado — RACDCERT (RACF / z/OS)\n\n> Comandos TSO, executados por quem tem autoridade RACF (normalmente time de segurança\n> mainframe). Sintaxe pode variar por versão do RACF/z/OS — confirme com o time\n> responsável antes de rodar em produção.\n\n## 1. Transferir o certificado pro mainframe\nO arquivo (PFX ou PEM) precisa chegar como dataset z/OS — via FTP/SFTP em modo **binário**\n(PFX) ou texto com conversão de code page (PEM), ou colado direto num dataset PDS.\n\n## 2. Importar um PKCS#12 (cert + chave junto) direto num keyring\n```\nRACDCERT ID(userid) ADD('HLQ.CERT.PFXDATA') PASSWORD('senha-do-pfx') +\n    WITHLABEL('meu-certificado') TRUST\n```\n\n## 3. Ou importar cert (sem chave) e conectar a um keyring existente\n```\nRACDCERT ID(userid) ADD('HLQ.CERT.CERDATA') WITHLABEL('meu-certificado') TRUST\n\nRACDCERT ID(userid) CONNECT(LABEL('meu-certificado') RING(meu-keyring) DEFAULT)\n```\n\n## 4. Criar o keyring, se ainda não existir\n```\nRACDCERT ID(userid) ADDRING(meu-keyring)\n```\n\n## Listar / conferir\n```\nRACDCERT ID(userid) LIST\nRACDCERT ID(userid) LISTRING(meu-keyring)\n```\n\n## Checklist pós-instalação\n- [ ] Certificado conectado (`CONNECT`) ao keyring correto, com `DEFAULT` se for o principal\n- [ ] `LISTRING` confere o certificado esperado, sem duplicidade\n- [ ] Certificado antigo removido/desconectado do keyring após validar o novo (`RACDCERT REMOVE`)\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Normalmente **manual** — exige acesso RACF/TSO restrito a poucas pessoas e costuma\n> passar por controle de mudança formal. Tecnicamente dá pra automatizar (JCL batch com\n> IKJEFT01 rodando os comandos RACDCERT, ou REXX), mas a maioria das organizações mantém\n> esse passo manual por política de segurança do mainframe, não por limitação técnica.\n",
    },
    {
        "title": 'Instalação de certificado — Azion Edge Certificates',
        "category": 'manual',
        "content_md": '# Instalação de certificado — Azion (Edge Certificates)\n\n> Azion reestruturou CLI e API algumas vezes (`azioncli` → `azion`, v3 → v4 da API) —\n> confirme os nomes exatos de comando/endpoint na documentação oficial atual antes de\n> automatizar; o fluxo abaixo é o padrão geral.\n\n## Via API\n```\nPOST https://api.azion.com/v4/edge_certificates\nAuthorization: Token <seu-token>\nContent-Type: application/json\n\n{\n  "name": "meu-certificado",\n  "certificate": "<conteúdo do .crt/cadeia em PEM>",\n  "private_key": "<conteúdo da chave privada em PEM>"\n}\n```\nAssocie o certificate (pelo id retornado) ao domain/edge application correspondente.\n\n## Via CLI\n```bash\nazion certificates create \\\n  --name "meu-certificado" \\\n  --certificate certificado.pem \\\n  --private-key chave.pem\n```\n(confira `azion certificates --help` na versão instalada — os flags mudaram entre versões)\n\n## Validação\n```bash\ncurl -s https://api.azion.com/v4/edge_certificates/<id> \\\n  -H "Authorization: Token <token>" | jq \'.results.{name,validity}\'\n```\n\n## Checklist pós-instalação\n- [ ] Certificado associado ao domain/edge application certo\n- [ ] Propagação no edge concluída (pode levar alguns minutos)\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Automatizável via API/CLI — igual aos outros CDNs/edge, é só cuidar da versão da CLI\n> usada no script de automação.\n',
    },
    {
        "title": 'Instalação de certificado — Windows Server (repositório de certificados)',
        "category": 'manual',
        "content_md": '# Instalação de certificado — Windows Server (repositório de certificados)\n\nComplementa o manual de IIS — aqui é o import genérico no repositório do Windows,\nusado por qualquer serviço que leia certificado do *certificate store* (não só IIS):\nRDP, SQL Server, serviços .NET próprios, etc.\n\n## Via PowerShell (recomendado — silencioso, scriptável)\n```powershell\n$pwd = ConvertTo-SecureString -String "SENHA_DO_PFX" -Force -AsPlainText\nImport-PfxCertificate -FilePath certificado.pfx `\n  -CertStoreLocation Cert:\\LocalMachine\\My -Password $pwd\n```\n\n## Via certutil\n```cmd\ncertutil -f -p "SENHA_DO_PFX" -importPFX certificado.pfx\n```\n\n## Conferir o thumbprint instalado\n```powershell\nGet-ChildItem Cert:\\LocalMachine\\My |\n  Where-Object { $_.Subject -like "*dominio.com.br*" } |\n  Select-Object Subject, Thumbprint, NotAfter\n```\n\n## Usar num serviço específico (exemplo: RDP)\n```powershell\n$thumb = "COLE_O_THUMBPRINT_AQUI"\nSet-ItemProperty -Path \'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp\' `\n  -Name SSLCertificateSHA1Hash -Value $thumb\n```\n\n## Remover certificado antigo (depois de validar o novo)\n```powershell\nRemove-Item -Path "Cert:\\LocalMachine\\My\\THUMBPRINT_ANTIGO"\n```\n\n## Checklist pós-instalação\n- [ ] Certificado aparece em `Cert:\\LocalMachine\\My` com o thumbprint esperado\n- [ ] Serviço consumidor reiniciado/reconfigurado pra usar o novo thumbprint, se necessário\n- [ ] Certificado antigo removido após validação\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Automatizável via PowerShell Remoting (`Invoke-Command`) ou Ansible (módulo\n> `win_certificate_store` / `community.windows`) — dá pra rodar em lote em vários\n> servidores sem acesso manual a cada um.\n',
    },
    {
        "title": 'Instalação de certificado — Akamai (CPS)',
        "category": 'manual',
        "content_md": '# Instalação de certificado — Akamai CPS (Certificate Provisioning System)\n\n> Fluxo de mudança em várias etapas (draft → submissão → validação → deploy staging →\n> deploy produção). Nomes de comando/endpoint podem variar por versão do Akamai CLI —\n> confirme com `akamai cps --help` antes de automatizar de verdade.\n\n## Pré-requisito\nCertificado gerenciado dentro de um "enrollment" no CPS — cada domínio/SAN set tem um\n`enrollment-id` próprio.\n\n## Via Akamai CLI\n```bash\n# baixa o enrollment atual como base pro update\nakamai cps retrieve-enrollment <enrollment-id> --json enrollment.json\n\n# edita enrollment.json com o novo certificado/chave (formato "third party CSR"\n# ou "BYOC" — bring your own certificate) e envia\nakamai cps update <enrollment-id> --force --json enrollment.json\n\n# acompanha o status da mudança\nakamai cps status <enrollment-id>\n```\n\n## Via API (Akamai OPEN API — CPS v2)\n```\nPOST /cps/v2/enrollments/{enrollmentId}/change-management\nAuthorization: EG1-HMAC-SHA256 <assinatura>\nContent-Type: application/vnd.akamai.cps.change-management.v1+json\n\n{ "certificatesAndTrustChains": [ { "certificate": "<PEM>", "trustChain": "<PEM>" } ] }\n```\nAssinatura EdgeGrid (HMAC) — normalmente feita pela lib oficial (`.edgerc` + SDK), não à mão.\n\n## Validação\n```bash\nakamai cps status <enrollment-id>\n```\nConfere se o deploy chegou em `active` no ambiente de produção (staging primeiro).\n\n## Checklist pós-instalação\n- [ ] Deploy validado em staging antes de produção\n- [ ] Status do enrollment em `active`/`deployed`\n- [ ] Registrar local de instalação na demanda (aba Demandas)\n\n> Automatizável via API/CLI, mas o processo em si é multi-etapa (staging antes de\n> produção é obrigatório no fluxo padrão da Akamai) — dá pra scriptar o fluxo inteiro,\n> só não pula as etapas de validação.\n',
    },
]

NOW = dt.datetime.now(dt.timezone.utc)
random.seed(42)

# Este script roda no host (fora do container), mas o app real roda dentro do
# container Docker com base_dir configurado como /app/data/files. Os arquivos
# físicos ficam sempre aqui (mesmo volume ./data montado em /app/data) — só o
# caminho gravado no banco precisa refletir a visão do container.
HOST_FILES_ROOT = Path(__file__).resolve().parent.parent / "data" / "files"


def _write(conn, logical_path: Path, content) -> str:
    """Grava no disco real do host (via HOST_FILES_ROOT) e devolve o caminho
    lógico (base_dir configurado) pra guardar em file_path — é o que o
    container vai usar pra reler o arquivo depois."""
    base = Path(get_setting(conn, "base_dir"))
    rel = logical_path.relative_to(base)
    real_path = HOST_FILES_ROOT / rel
    real_path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        real_path.write_text(content)
    else:
        real_path.write_bytes(content)
    return str(logical_path)


def _key(key_type="rsa2048"):
    if key_type == "rsa4096":
        return rsa.generate_private_key(public_exponent=65537, key_size=4096)
    if key_type == "ec256":
        return ec.generate_private_key(ec.SECP256R1())
    if key_type == "ec384":
        return ec.generate_private_key(ec.SECP384R1())
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _name(cn, org="BancoFic S.A."):
    return x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
    ])


def make_cert(cn, *, issuer=None, issuer_key=None, key=None, key_type="rsa2048", ca=False,
              sans=None, days=365, days_ago=30, org="BancoFic S.A.",
              server=True, client=False):
    key = key or _key(key_type)
    subject = _name(cn, org)
    builder = (x509.CertificateBuilder()
               .subject_name(subject)
               .issuer_name(issuer.subject if issuer else subject)
               .public_key(key.public_key())
               .serial_number(x509.random_serial_number())
               .not_valid_before(NOW - dt.timedelta(days=days_ago))
               .not_valid_after(NOW + dt.timedelta(days=days))
               .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True))
    if sans:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(s) for s in sans]), critical=False)
    if not ca:
        ekus = []
        if server:
            ekus.append(ExtendedKeyUsageOID.SERVER_AUTH)
        if client:
            ekus.append(ExtendedKeyUsageOID.CLIENT_AUTH)
        if ekus:
            builder = builder.add_extension(x509.ExtendedKeyUsage(ekus), critical=False)
    cert = builder.sign(issuer_key or key, hashes.SHA256())
    return cert, key


def insert_cert(conn, cert, req_id=None, parent_id=None, lifecycle_status=None,
                 cert_category="", ownership="interno", partner=None):
    pem_bytes = cert.public_bytes(serialization.Encoding.PEM)
    info = certparse.parse_certificate(pem_bytes)
    partner = partner or {}

    # Grava o certificado de verdade em disco, na mesma estrutura que o import real usa —
    # assim "Copiar PEM" e o Decoder funcionam também nos dados de demonstração.
    base = get_setting(conn, "base_dir")
    safe_name = folders.sanitize(info["cn"]) + ".crt"
    if req_id:
        req = conn.execute("SELECT req_number, cn, env FROM reqs WHERE id=?", (req_id,)).fetchone()
        template = get_setting(conn, "folder_template")
        dest_folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"]) / "cert"
    else:
        dest_folder = Path(base) / "certs"
    file_path = _write(conn, dest_folder / safe_name, pem_bytes)

    cur = conn.execute(
        """INSERT INTO certificates
           (req_id, cn, sans, subject, issuer, issuer_cn, cert_type, serial,
            thumbprint_sha1, not_before, not_after, key_type, source, file_path, parent_id,
            cert_category, ownership, external_partner, partner_email, partner_registration
            {lc_col})
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?{lc_val})""".format(
            lc_col=", lifecycle_status" if lifecycle_status else "",
            lc_val=",?" if lifecycle_status else ""),
        (req_id, info["cn"], info["sans"], info["subject"], info["issuer"],
         info["issuer_cn"], info["cert_type"], info["serial"], info["thumbprint_sha1"],
         info["not_before"], info["not_after"], info["key_type"], "demo", file_path, parent_id,
         cert_category, ownership, partner.get("name", ""), partner.get("email", ""),
         partner.get("reg", ""))
        + ((lifecycle_status,) if lifecycle_status else ()))
    return cur.lastrowid


def seed_tasks(conn, req_id):
    """Clona o checklist de tarefas ativo pra uma demanda de instalação em PRD —
    mesma lógica usada pelo backend em reqs.py::_seed_install_tasks."""
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


def set_task(conn, req_id, title, status=None, notes=None, evidence=None):
    """Simula progresso em uma tarefa do checklist (pra demo não nascer 100% vazia)."""
    task = conn.execute("SELECT * FROM install_tasks WHERE req_id=? AND title=?",
                        (req_id, title)).fetchone()
    if not task:
        return
    if status or notes is not None:
        conn.execute(
            "UPDATE install_tasks SET status=COALESCE(?, status), notes=COALESCE(?, notes) WHERE id=?",
            (status, notes, task["id"]))
    if evidence:
        req = conn.execute("SELECT * FROM reqs WHERE id=?", (req_id,)).fetchone()
        base = get_setting(conn, "base_dir")
        template = get_setting(conn, "folder_template")
        folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"])
        dest_folder = folder / "evidencias" / str(task["id"])
        logical_path = dest_folder / evidence["filename"]
        file_path = _write(conn, logical_path, evidence["content"])
        conn.execute(
            "INSERT INTO install_task_evidence (task_id, filename, file_path) VALUES (?,?,?)",
            (task["id"], evidence["filename"], file_path))


def add_csr(conn, req_id, cn, key_type="rsa2048"):
    """Gera uma CSR de verdade pra demanda — grava em reqs.csr_pem (aba 'Certificado Gerado'),
    no repositório de CSRs e no disco (csr/{cn}.key e .csr), igual ao fluxo real de /csr/generate."""
    k = _key(key_type)
    csr = (x509.CertificateSigningRequestBuilder()
           .subject_name(_name(cn))
           .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
           .sign(k, hashes.SHA256()))
    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
    key_pem = k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.TraditionalOpenSSL,
                              serialization.NoEncryption()).decode()
    key_label = {"rsa2048": "RSA 2048", "rsa4096": "RSA 4096",
                "ec256": "EC secp256r1", "ec384": "EC secp384r1"}[key_type]

    conn.execute("UPDATE reqs SET csr_pem=? WHERE id=?", (csr_pem, req_id))
    conn.execute(
        "INSERT INTO csrs (cn, sans, subject, key_type, sig_algo, req_id, pem) VALUES (?,?,?,?,?,?,?)",
        (cn, cn, csr.subject.rfc4514_string(), key_label, "sha256", req_id, csr_pem))

    req = conn.execute("SELECT req_number, cn, env FROM reqs WHERE id=?", (req_id,)).fetchone()
    base = get_setting(conn, "base_dir")
    template = get_setting(conn, "folder_template")
    folder = folders.req_folder(base, template, req["req_number"], req["cn"], req["env"]) / "csr"
    fname = folders.sanitize(cn)
    _write(conn, folder / f"{fname}.key", key_pem)
    _write(conn, folder / f"{fname}.csr", csr_pem)


def insert_req(conn, req_no, cn, env, status, notes, created, *, demand_type="geracao",
                ownership="interno", partner=None, external_wo="", external_crq=""):
    partner = partner or {}
    cur = conn.execute(
        """INSERT INTO reqs (req_number, cn, env, password, status, notes, created_at, updated_at,
               demand_type, ownership, external_partner, partner_email, partner_registration,
               external_wo, external_crq)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (req_no, cn, env, f"Demo!{random.randint(10000, 99999)}Xy", status,
         f"[demo] {notes}", created, created, demand_type, ownership,
         partner.get("name", ""), partner.get("email", ""), partner.get("reg", ""),
         external_wo, external_crq))
    return cur.lastrowid


def insert_doc(conn, title, category, content_md):
    exists = conn.execute("SELECT id FROM docs WHERE title=?", (title,)).fetchone()
    if exists:
        return False
    conn.execute("INSERT INTO docs (title, category, content_md) VALUES (?,?,?)",
                 (title, category, content_md))
    return True


def insert_user(conn, username, display_name, role, password):
    pwd_hash, salt = hash_password(password)
    conn.execute(
        """INSERT OR IGNORE INTO users (username, display_name, email, role, password_hash, salt)
           VALUES (?,?,?,?,?,?)""",
        (username, display_name, f"{username}@certhub.local", role, pwd_hash, salt))


BULK_SUBDOMAINS = [
    "app", "srv", "web", "auth", "pay", "checkout", "admin", "intra", "gw", "edge",
    "cache", "queue", "report", "batch", "crm", "erp", "hr", "billing", "notif",
    "search", "upload", "media", "cdn", "mobile", "partner", "sandbox", "stage",
    "backup", "sync", "log", "metrics", "chat", "voip", "sftp", "vpn2", "ldap",
    "core", "risco", "fraude", "onboarding", "kyc",
]
BULK_DOMAINS = (["bancofic.com.br"] * 7 + ["fintechx.com.br"] * 1
                + ["acmegateway.com.br"] * 1 + ["logisticay.com.br"] * 1)
BULK_ENVS = ["PRD"] * 5 + ["HMP"] * 2 + ["TQS"] * 2 + ["DES"] * 1
BULK_DEMAND_TYPES = (["geracao"] * 4 + ["instalacao"] * 3 + ["recebimento"] * 1
                      + ["renovacao"] * 2 + ["revogacao"] * 1)
BULK_KEY_TYPES = ["rsa2048"] * 6 + ["rsa4096"] * 2 + ["ec256"] * 2 + ["ec384"] * 1
BULK_CERT_CATS_INT = ["ac_interna_apl_prd", "ac_icp_testes", "outro"]
BULK_CERT_CATS_PUB = ["sectigo_dv", "sectigo_ov", "sectigo_ev", "apple", "bandeiras", "sepro"]
BULK_INSTALL_TARGETS = [
    ("SRVWEB{:02d}", "IIS binding 443 · LocalMachine\\My"),
    ("SRVAPP{:02d}", "nginx /etc/ssl/certs"),
    ("SRVTOM{:02d}", "Tomcat conf/keystore.jks"),
    ("F5-LTM-{:02d}", "clientssl"),
    ("KEYVAULT-{:02d}", "Azure Key Vault"),
    ("ACM-{:02d}", "AWS Certificate Manager"),
    ("MAINFRAME-{:02d}", "RACDCERT keyring"),
    ("AZION-{:02d}", "Edge Certificates"),
    ("AKAMAI-{:02d}", "CPS enrollment"),
]


def generate_bulk(conn, add_req, add_leaf_cert, n=150, start_at=13000):
    """Gera N demandas/certificados aleatórios reaproveitando add_req/add_leaf_cert —
    pra popular o banco em volume sem escrever exemplo por exemplo à mão."""
    for i in range(n):
        env = random.choice(BULK_ENVS)
        demand_type = random.choice(BULK_DEMAND_TYPES)
        domain = random.choice(BULK_DOMAINS)
        sub = random.choice(BULK_SUBDOMAINS)
        cn = f"{sub}-{i:04d}.{domain}"
        ownership = random.choices(["interno", "externo"], weights=[8, 2])[0]
        partner = None
        if ownership == "externo":
            partner = {"name": f"Parceiro {sub.capitalize()} {i:04d}",
                       "email": f"ti-{i:04d}@{domain}", "reg": f"MAT-{random.randint(10000, 99999)}"}

        if demand_type == "instalacao":
            status = random.choices(["aberta", "instalado", "concluida"], weights=[1, 5, 3])[0]
        else:
            status = random.choices(
                ["aberta", "csr_gerada", "cert_emitido", "concluida", "cancelada"],
                weights=[2, 2, 2, 3, 1])[0]

        external_wo = external_crq = ""
        if demand_type == "instalacao" and status != "aberta":
            if env == "PRD":
                external_crq = f"CRQ00{random.randint(60000, 99999)}"
            else:
                external_wo = f"WO00{random.randint(50000, 99999)}"

        rid, created = add_req(
            req_no=f"REQ00{start_at + i}", cn=cn, env=env, status=status,
            notes=f"[bulk] {demand_type} · {sub}", demand_type=demand_type,
            ownership=ownership, partner=partner,
            external_wo=external_wo, external_crq=external_crq)

        has_cert = status not in ("aberta", "csr_gerada", "cancelada")
        if not has_cert:
            continue

        issuer_kind = "pub" if (ownership == "externo" or random.random() < 0.3) else "int"
        cert_category = (
            "parceiro_externo" if ownership == "externo"
            else random.choice(BULK_CERT_CATS_PUB if issuer_kind == "pub" else BULK_CERT_CATS_INT))
        if status == "instalado":
            lifecycle_status = "instalado"
        elif demand_type == "revogacao":
            lifecycle_status = random.choice(["excluir", "fim_de_vida"])
        else:
            lifecycle_status = random.choice(["em_inventario", "reservado"])

        locs = []
        if demand_type == "instalacao" and status in ("instalado", "concluida"):
            for _ in range(random.randint(1, 2)):
                name_fmt, path = random.choice(BULK_INSTALL_TARGETS)
                locs.append((name_fmt.format(random.randint(1, 20)), path))

        cert_id = add_leaf_cert(
            rid, cn, created,
            issuer_kind=issuer_kind,
            key_type=random.choice(BULK_KEY_TYPES),
            days=random.choice([-60, -20, -5, 10, 25, 45, 80, 150, 300, 500]),
            days_ago=random.randint(20, 400),
            sans=[cn],
            client=random.random() < 0.15,
            lifecycle_status=lifecycle_status,
            cert_category=cert_category,
            ownership=ownership,
            partner=partner,
            locs=locs,
        )
        if demand_type == "instalacao" and status in ("instalado", "concluida") and env == "PRD":
            seed_tasks(conn, rid)
            if random.random() < 0.6:
                for title in ("Preparo", "Ativação", "Teste", "Plano de retorno"):
                    if random.random() < 0.7:
                        set_task(conn, rid, title,
                                 status=random.choices(
                                     ["sucesso", "em_andamento", "falha"], weights=[6, 2, 1])[0])


def create(conn, bulk_n=150):
    # --- cadeias: raiz + emissora internas e uma CA "pública" ---
    root, root_key = make_cert("BancoFic Root CA G1", ca=True, days=3650, days_ago=1500)
    issuing, issuing_key = make_cert("BancoFic Issuing CA TLS 01", issuer=root,
                                     issuer_key=root_key, ca=True, days=1825, days_ago=900)
    pub_ca, pub_ca_key = make_cert("ACME Public TLS CA", ca=True, days=3650,
                                   days_ago=1200, org="ACME Trust Services")
    root_id = insert_cert(conn, root, cert_category="ac_interna_apl_prd")
    issuing_id = insert_cert(conn, issuing, parent_id=root_id, cert_category="ac_interna_apl_prd")
    pub_ca_id = insert_cert(conn, pub_ca, cert_category="sectigo_ov")

    n_users = 0
    for username, display_name, role in DEMO_USERS:
        insert_user(conn, username, display_name, role, f"{username}@2026")
        n_users += 1

    n_docs = 0
    for doc in DEMO_DOCS:
        if insert_doc(conn, doc["title"], doc["category"], doc["content_md"]):
            n_docs += 1

    n_reqs = n_certs = 0
    partner_acme = {"name": "ACME Gateway Ltda", "email": "ti@acmegateway.com.br", "reg": "MAT-88213"}
    partner_fintech = {"name": "Fintech Parceira X", "email": "seguranca@fintechx.com.br", "reg": "MAT-40921"}

    def add_req(**kw):
        nonlocal n_reqs
        created = (NOW - dt.timedelta(days=random.randint(5, 400))).strftime("%Y-%m-%d %H:%M:%S")
        rid = insert_req(conn, kw.pop("req_no"), kw.pop("cn"), kw.pop("env"), kw.pop("status"),
                          kw.pop("notes"), created, **kw)
        n_reqs += 1
        return rid, created

    def add_leaf_cert(req_id, cn, created, *, issuer_kind="int", key_type="rsa2048",
                       days=365, days_ago=None, sans=None, server=True, client=False,
                       parent_kind=None, lifecycle_status=None, cert_category="",
                       ownership="interno", partner=None, locs=None):
        nonlocal n_certs
        issuer, ikey, pid = {
            "int": (issuing, issuing_key, issuing_id),
            "pub": (pub_ca, pub_ca_key, pub_ca_id),
        }[issuer_kind]
        cert, _ = make_cert(cn, issuer=issuer, issuer_key=ikey, days=days,
                            days_ago=days_ago if days_ago is not None else random.randint(20, 300),
                            sans=sans, server=server, client=client, key_type=key_type)
        cert_id = insert_cert(conn, cert, req_id=req_id, parent_id=pid,
                              lifecycle_status=lifecycle_status, cert_category=cert_category,
                              ownership=ownership, partner=partner)
        n_certs += 1
        for server_name, path in (locs or []):
            conn.execute(
                """INSERT INTO install_locations (req_id, cert_id, server, path_or_store,
                   installed_at, notes) VALUES (?,?,?,?,?,?)""",
                (req_id, cert_id, server_name, path, created[:10], "[demo]"))
        return cert_id

    # 1) Geração comum, servidor TLS, instalada em 2 lugares — checklist CRQ com progresso parcial
    rid, created = add_req(req_no="REQ0012001", cn="portal.bancofic.com.br", env="PRD",
                            status="instalado", notes="Geração padrão — portal público",
                            demand_type="instalacao", external_crq="CRQ0055120")
    add_leaf_cert(rid, "portal.bancofic.com.br", created, days=25,
                  sans=["portal.bancofic.com.br", "portal-01.bancofic.com.br"],
                  lifecycle_status="instalado", cert_category="sectigo_ov",
                  locs=[("SRVWEB01", "IIS binding 443 · LocalMachine\\My"),
                        ("F5-LTM-01", "clientssl-portal")])
    seed_tasks(conn, rid)
    set_task(conn, rid, "Preparo", status="sucesso", notes="Arquivo .pfx enviado via SharePoint em 2026-08-05.",
              evidence={"filename": "preparo-pfx-enviado.txt",
                        "content": "Evidência (demo): arquivo portal.bancofic.com.br.pfx disponibilizado "
                                   "para a equipe de infraestrutura em 05/08/2026 09:14.\n"})
    set_task(conn, rid, "Ativação", status="sucesso", notes="Ativado no IIS (SRVWEB01) e no F5 (clientssl-portal).")
    set_task(conn, rid, "Teste", status="em_andamento", notes="Handshake TLS ok; validando cadeia completa no F5.")

    # 2) mTLS servidor+cliente, chave EC, múltiplos servidores
    rid, created = add_req(req_no="REQ0012002", cn="api.bancofic.com.br", env="PRD",
                            status="instalado", notes="API interna com mTLS",
                            demand_type="instalacao", external_crq="CRQ0055121")
    add_leaf_cert(rid, "api.bancofic.com.br", created, days=80, key_type="ec256",
                  sans=["api.bancofic.com.br", "api-01.bancofic.com.br"], server=True, client=True,
                  lifecycle_status="instalado", cert_category="ac_interna_apl_prd",
                  locs=[("SRVAPI01", "nginx /etc/ssl/certs"), ("SRVAPI02", "nginx /etc/ssl/certs")])
    seed_tasks(conn, rid)

    # 3) Público (CA pública), concluída há tempo
    rid, created = add_req(req_no="REQ0012003", cn="www.bancofic.com.br", env="PRD",
                            status="instalado", notes="Site institucional",
                            demand_type="instalacao", external_crq="CRQ0041207")
    add_leaf_cert(rid, "www.bancofic.com.br", created, days=300, issuer_kind="pub",
                  sans=["www.bancofic.com.br"], lifecycle_status="instalado",
                  cert_category="sectigo_ov", locs=[("CDN-EDGE", "painel do provedor")])

    # 4) Wildcard homologação, chave RSA 4096
    rid, created = add_req(req_no="REQ0012004", cn="*.hml.bancofic.com.br", env="HMP",
                            status="instalado", notes="Wildcard ambiente de homologação",
                            demand_type="instalacao", external_wo="WO0031177")
    add_leaf_cert(rid, "*.hml.bancofic.com.br", created, days=150, key_type="rsa4096",
                  sans=["wildcard.hml.bancofic.com.br"], lifecycle_status="instalado",
                  cert_category="ac_icp_testes", locs=[("SRVHML03", "Tomcat conf/keystore.jks")])

    # 5) Já vencido (fim de vida) — para o painel de vencidos
    rid, created = add_req(req_no="REQ0012005", cn="sso.bancofic.com.br", env="PRD",
                            status="instalado", notes="SSO corporativo — venceu, aguardando renovação",
                            demand_type="instalacao", external_crq="CRQ0022881")
    add_leaf_cert(rid, "sso.bancofic.com.br", created, days=-12, days_ago=353,
                  sans=["sso.bancofic.com.br"], lifecycle_status="fim_de_vida",
                  cert_category="sectigo_ov", locs=[("SRVSSO01", "IIS binding 443")])
    seed_tasks(conn, rid)

    # 6) Cliente mTLS puro (sem SERVER_AUTH), emitido, sem instalar ainda — CSR real gerada antes
    rid, created = add_req(req_no="REQ0012006", cn="client-integracao.bancofic.com.br", env="PRD",
                            status="cert_emitido", notes="Certificado cliente para integração B2B",
                            demand_type="geracao")
    add_csr(conn, rid, "client-integracao.bancofic.com.br")
    add_leaf_cert(rid, "client-integracao.bancofic.com.br", created, days=200, server=False,
                  client=True, lifecycle_status="em_inventario", cert_category="ac_interna_apl_prd")

    # 7) EC 384, mainframe/MQ, mTLS
    rid, created = add_req(req_no="REQ0012007", cn="mq.bancofic.com.br", env="TQS",
                            status="instalado", notes="Fila MQ com TLS mútuo",
                            demand_type="instalacao", external_wo="WO0019943")
    add_leaf_cert(rid, "mq.bancofic.com.br", created, days=45, key_type="ec384", server=True,
                  client=True, sans=["mq.bancofic.com.br"], lifecycle_status="instalado",
                  cert_category="ac_interna_apl_prd", locs=[("SRVMQ01", "IBM MQ keystore .kdb")])

    # 8) Ainda em CSR gerada, aguardando emissão da CA pública — CSR real anexada
    rid, created = add_req(req_no="REQ0012008", cn="dev.bancofic.com.br", env="DES", status="csr_gerada",
                           notes="Ambiente de desenvolvimento — aguardando CA pública", demand_type="geracao")
    add_csr(conn, rid, "dev.bancofic.com.br", key_type="ec256")

    # 9) Aberta, recém criada
    add_req(req_no="REQ0012009", cn="extranet.bancofic.com.br", env="PRD", status="aberta",
            notes="Extranet parceiros — aguardando início", demand_type="geracao")

    # 10) Cancelada
    add_req(req_no="REQ0012010", cn="relatorios.bancofic.com.br", env="HMP", status="cancelada",
            notes="Cancelada — projeto adiado", demand_type="geracao")

    # 11) Recebimento — certificado público de parceiro externo (ownership externo)
    rid, created = add_req(req_no="REQ0012011", cn="gateway.acmegateway.com.br", env="PRD",
                            status="cert_emitido", notes="Certificado recebido do parceiro ACME Gateway",
                            demand_type="recebimento", ownership="externo", partner=partner_acme)
    add_leaf_cert(rid, "gateway.acmegateway.com.br", created, days=180, issuer_kind="pub",
                  sans=["gateway.acmegateway.com.br"], lifecycle_status="em_inventario",
                  cert_category="parceiro_externo", ownership="externo", partner=partner_acme)

    # 12) Renovação de um certificado que já existia (parent_req_id aponta pra REQ0012001)
    rid, created = add_req(req_no="REQ0012012", cn="portal.bancofic.com.br", env="PRD",
                            status="csr_gerada", notes="Renovação anual do portal — parent REQ0012001",
                            demand_type="renovacao")
    add_csr(conn, rid, "portal.bancofic.com.br", key_type="rsa4096")
    conn.execute("UPDATE reqs SET parent_req_id=(SELECT id FROM reqs WHERE req_number='REQ0012001') "
                 "WHERE id=?", (rid,))

    # 13) Revogação — certificado marcado para exclusão
    rid, created = add_req(req_no="REQ0012013", cn="legado.bancofic.com.br", env="PRD",
                            status="concluida", notes="Sistema legado desativado — cert revogado",
                            demand_type="revogacao")
    add_leaf_cert(rid, "legado.bancofic.com.br", created, days=40, days_ago=310,
                  sans=["legado.bancofic.com.br"], lifecycle_status="excluir",
                  cert_category="outro")

    # 14) Instalação em PRD — a mudança (CRQ) é da instalação, não da geração
    rid, created = add_req(req_no="REQ0012014", cn="client-integracao.bancofic.com.br", env="PRD",
                            status="instalado", notes="Instalação do certificado cliente em produção",
                            demand_type="instalacao", external_crq="CRQ0071144")
    conn.execute(
        """INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes)
           SELECT ?, c.id, 'SRVINT01', 'Java keystore /opt/app/client.jks', ?, '[demo]'
           FROM certificates c WHERE c.cn='client-integracao.bancofic.com.br' LIMIT 1""",
        (rid, created[:10]))
    conn.execute("UPDATE reqs SET parent_req_id=(SELECT id FROM reqs WHERE req_number='REQ0012006') "
                 "WHERE id=?", (rid,))
    seed_tasks(conn, rid)

    # 15) Parceiro externo Fintech — recebimento em ambiente de homologação
    rid, created = add_req(req_no="REQ0012015", cn="open-finance.fintechx.com.br", env="HMP",
                            status="concluida", notes="Certificado Open Finance recebido da Fintech X",
                            demand_type="recebimento", ownership="externo", partner=partner_fintech)
    add_leaf_cert(rid, "open-finance.fintechx.com.br", created, days=95, issuer_kind="pub",
                  key_type="ec256", sans=["open-finance.fintechx.com.br"],
                  lifecycle_status="em_inventario", cert_category="parceiro_externo",
                  ownership="externo", partner=partner_fintech)

    # 15b) Instalação em ambiente não-PRD — a mudança aqui é WO, não CRQ
    rid2, created2 = add_req(req_no="REQ0012018", cn="open-finance.fintechx.com.br", env="HMP",
                             status="instalado", notes="Instalação do certificado Open Finance em HMP",
                             demand_type="instalacao", external_wo="WO0045213")
    conn.execute(
        """INSERT INTO install_locations (req_id, cert_id, server, path_or_store, installed_at, notes)
           SELECT ?, c.id, 'SRVOF01', 'nginx /etc/ssl/certs', ?, '[demo]'
           FROM certificates c WHERE c.cn='open-finance.fintechx.com.br' LIMIT 1""",
        (rid2, created2[:10]))
    conn.execute("UPDATE reqs SET parent_req_id=? WHERE id=?", (rid, rid2))

    # 16) PRD, certificado emitido aguardando a demanda de instalação (ainda sem CRQ)
    rid, created = add_req(req_no="REQ0012016", cn="pagamentos.bancofic.com.br", env="PRD",
                            status="cert_emitido", notes="Aguardando abertura da demanda de instalação",
                            demand_type="geracao")
    add_csr(conn, rid, "pagamentos.bancofic.com.br")
    add_leaf_cert(rid, "pagamentos.bancofic.com.br", created, days=170,
                  sans=["pagamentos.bancofic.com.br"], lifecycle_status="em_inventario",
                  cert_category="sectigo_ev")

    # 17) Reservado — em inventário, sem demanda associada ainda (cert avulso)
    reserved_cert, _ = make_cert("reserva.bancofic.com.br", issuer=issuing, issuer_key=issuing_key,
                                 days=365, days_ago=10, sans=["reserva.bancofic.com.br"])
    insert_cert(conn, reserved_cert, req_id=None, parent_id=issuing_id,
                lifecycle_status="reservado", cert_category="ac_interna_apl_prd")
    n_certs += 1

    partner_logistica = {"name": "Logística Parceira Y", "email": "ti@logisticay.com.br", "reg": "MAT-51120"}

    # 18) Renovação já concluída e avançada pra instalação (ciclo completo geração→instalação)
    rid, created = add_req(req_no="REQ0012019", cn="vpn.bancofic.com.br", env="PRD",
                            status="instalado", notes="Renovação anual da VPN corporativa — ciclo completo",
                            demand_type="instalacao", external_crq="CRQ0088302")
    add_leaf_cert(rid, "vpn.bancofic.com.br", created, days=340,
                  sans=["vpn.bancofic.com.br"], lifecycle_status="instalado",
                  cert_category="ac_interna_apl_prd", locs=[("FW-VPN-01", "Certificado do concentrador VPN")])
    seed_tasks(conn, rid)
    set_task(conn, rid, "Preparo", status="sucesso")
    set_task(conn, rid, "Ativação", status="sucesso")
    set_task(conn, rid, "Teste", status="sucesso")
    set_task(conn, rid, "Plano de retorno", status="sucesso",
             notes="Certificado anterior mantido em backup por 30 dias.")

    # 19) Importação — certificado de parceiro trazido pronto, sem geração local
    rid, created = add_req(req_no="REQ0012020", cn="parceiro-importado.bancofic.com.br", env="DES",
                            status="concluida", notes="Certificado wildcard do parceiro importado direto",
                            demand_type="importacao", ownership="externo",
                            partner={"name": "Parceiro Cloud Z", "email": "certs@cloudz.com",
                                     "reg": "MAT-77009"})
    add_leaf_cert(rid, "parceiro-importado.bancofic.com.br", created, days=250, issuer_kind="pub",
                  sans=["parceiro-importado.bancofic.com.br"], lifecycle_status="em_inventario",
                  cert_category="parceiro_externo", ownership="externo",
                  partner={"name": "Parceiro Cloud Z", "email": "certs@cloudz.com", "reg": "MAT-77009"})

    # 20) Geração pendente em TQS — CSR ainda não gerada
    add_req(req_no="REQ0012021", cn="batch.bancofic.com.br", env="TQS", status="aberta",
            notes="Job noturno de conciliação — geração ainda não iniciada", demand_type="geracao")

    # 21) Revogação concluída em HMP
    rid, created = add_req(req_no="REQ0012022", cn="antigo-hml.bancofic.com.br", env="HMP",
                            status="concluida", notes="Ambiente de homologação descontinuado",
                            demand_type="revogacao")
    add_leaf_cert(rid, "antigo-hml.bancofic.com.br", created, days=60, days_ago=280,
                  sans=["antigo-hml.bancofic.com.br"], lifecycle_status="excluir",
                  cert_category="ac_icp_testes")

    # 22) Recebimento em TQS — parceiro de logística, ainda aguardando instalação
    rid, created = add_req(req_no="REQ0012023", cn="edi.logisticay.com.br", env="TQS",
                            status="cert_emitido", notes="Certificado EDI recebido da Logística Parceira Y",
                            demand_type="recebimento", ownership="externo", partner=partner_logistica)
    add_leaf_cert(rid, "edi.logisticay.com.br", created, days=200, issuer_kind="pub",
                  sans=["edi.logisticay.com.br"], lifecycle_status="em_inventario",
                  cert_category="parceiro_externo", ownership="externo", partner=partner_logistica)

    # --- volume: N demandas/certificados aleatórios além dos 22 exemplos narrativos acima ---
    if bulk_n:
        generate_bulk(conn, add_req, add_leaf_cert, n=bulk_n)

    # --- CSRs no repositório (variedade de tipos de chave) ---
    from cryptography.hazmat.primitives.serialization import Encoding
    csr_examples = [
        ("novo-servico.bancofic.com.br", "rsa2048", "BancoFic S.A."),
        ("pagamentos-v2.bancofic.com.br", "ec256", "BancoFic S.A."),
        ("parceiro.fintechx.com.br", "rsa4096", "Fintech Parceira X"),
    ]
    for cn, key_type, org in csr_examples:
        k = _key(key_type)
        csr = (x509.CertificateSigningRequestBuilder()
               .subject_name(_name(cn, org))
               .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
               .sign(k, hashes.SHA256()))
        key_label = {"rsa2048": "RSA 2048", "rsa4096": "RSA 4096", "ec256": "EC secp256r1"}[key_type]
        conn.execute(
            "INSERT INTO csrs (cn, sans, subject, key_type, sig_algo, pem) VALUES (?,?,?,?,?,?)",
            (cn, cn, csr.subject.rfc4514_string(), key_label, "sha256",
             csr.public_bytes(Encoding.PEM).decode()))

    # --- atividade espalhada nos últimos 30 dias (para o gráfico) ---
    actions = ["req_criada", "csr_gerada", "cert_importado", "status_alterado", "senha_gerada",
               "lifecycle_em_renovacao", "csr_removida", "locais_importados", "doc_criado"]
    for _ in range(30):
        when = (NOW - dt.timedelta(days=random.randint(0, 29),
                                   hours=random.randint(0, 12))).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO activity_log (action, detail, created_at) VALUES (?,?,?)",
            (random.choice(actions), "[demo] atividade fictícia", when))

    n_tasks = conn.execute(
        "SELECT COUNT(*) FROM install_tasks WHERE req_id IN "
        "(SELECT id FROM reqs WHERE notes LIKE '%[demo]%')").fetchone()[0]
    n_evidence = conn.execute(
        "SELECT COUNT(*) FROM install_task_evidence WHERE task_id IN "
        "(SELECT id FROM install_tasks WHERE req_id IN "
        "(SELECT id FROM reqs WHERE notes LIKE '%[demo]%'))").fetchone()[0]
    conn.commit()
    print(f"OK — {n_users} usuários, {n_docs} manuais, {n_reqs} demandas, {n_certs + 3} certificados (3 CAs, arquivos reais em disco), "
          f"{len(csr_examples) + 4} CSRs no repositório, {n_tasks} tarefas de checklist "
          f"({n_evidence} com evidência anexada) e 30 eventos de atividade criados.")


def remove(conn):
    conn.execute("""DELETE FROM install_locations WHERE req_id IN
                    (SELECT id FROM reqs WHERE notes LIKE '%[demo]%')""")
    n_certs = conn.execute("DELETE FROM certificates WHERE source='demo'").rowcount
    n_reqs = conn.execute("DELETE FROM reqs WHERE notes LIKE '%[demo]%'").rowcount
    n_csrs = conn.execute("DELETE FROM csrs WHERE subject LIKE '%O=BancoFic%' "
                          "OR subject LIKE '%O=Fintech Parceira X%'").rowcount
    n_act = conn.execute("DELETE FROM activity_log WHERE detail LIKE '%[demo]%'").rowcount
    conn.commit()
    print(f"Removidos: {n_reqs} demandas, {n_certs} certificados, {n_csrs} CSRs, "
          f"{n_act} eventos de atividade.")


if __name__ == "__main__":
    init_db()
    conn = get_db()
    if "--remove" in sys.argv:
        remove(conn)
    else:
        if conn.execute("SELECT 1 FROM certificates WHERE source='demo' LIMIT 1").fetchone():
            print("Dados demo já existem — rode com --remove antes de recriar.")
            sys.exit(1)
        bulk_n = 150
        if "--bulk" in sys.argv:
            bulk_n = int(sys.argv[sys.argv.index("--bulk") + 1])
        create(conn, bulk_n=bulk_n)
    conn.close()
