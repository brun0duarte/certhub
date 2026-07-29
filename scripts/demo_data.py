"""Popula o CertHub com dados fictícios (domínio bancofic.com.br) para demonstração.

Uso:
    .venv/bin/python scripts/demo_data.py           # cria os dados
    .venv/bin/python scripts/demo_data.py --remove  # remove tudo que foi criado

Marcadores usados na remoção: reqs.notes contém [demo], certificates.source='demo',
csrs.subject contém O=BancoFic, activity_log.detail contém [demo].
"""
import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app.db import get_db, init_db
from app.services import certparse

NOW = dt.datetime.now(dt.timezone.utc)
random.seed(42)


def _key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _name(cn, org="BancoFic S.A."):
    return x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, cn),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COUNTRY_NAME, "BR"),
    ])


def make_cert(cn, *, issuer=None, issuer_key=None, key=None, ca=False,
              sans=None, days=365, days_ago=30, org="BancoFic S.A.",
              server=True, client=False):
    key = key or _key()
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


def insert_cert(conn, cert, req_id=None, parent_id=None):
    info = certparse.parse_certificate(cert.public_bytes(serialization.Encoding.PEM))
    cur = conn.execute(
        """INSERT INTO certificates
           (req_id, cn, sans, subject, issuer, issuer_cn, cert_type, serial,
            thumbprint_sha1, not_before, not_after, key_type, source, file_path, parent_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (req_id, info["cn"], info["sans"], info["subject"], info["issuer"],
         info["issuer_cn"], info["cert_type"], info["serial"], info["thumbprint_sha1"],
         info["not_before"], info["not_after"], info["key_type"], "demo", "", parent_id))
    return cur.lastrowid


def create(conn):
    # --- cadeias: raiz + emissora internas e uma CA "pública" ---
    root, root_key = make_cert("BancoFic Root CA G1", ca=True, days=3650, days_ago=1500)
    issuing, issuing_key = make_cert("BancoFic Issuing CA TLS 01", issuer=root,
                                     issuer_key=root_key, ca=True, days=1825, days_ago=900)
    pub_ca, pub_ca_key = make_cert("ACME Public TLS CA", ca=True, days=3650,
                                   days_ago=1200, org="ACME Trust Services")
    root_id = insert_cert(conn, root)
    issuing_id = insert_cert(conn, issuing, parent_id=root_id)
    pub_ca_id = insert_cert(conn, pub_ca)

    # --- demandas + certificados folha ---
    #  (req, cn, env, status, dias p/ vencer, emissora, mtls, locais)
    leaves = [
        ("REQ0012001", "portal.bancofic.com.br", "PRD", "instalado", 25, "int", (True, False),
         [("SRVWEB01", "IIS binding 443 · LocalMachine\\My"), ("F5-LTM-01", "clientssl-portal")]),
        ("REQ0012002", "api.bancofic.com.br", "PRD", "instalado", 80, "int", (True, True),
         [("SRVAPI01", "nginx /etc/ssl/certs"), ("SRVAPI02", "nginx /etc/ssl/certs")]),
        ("REQ0012003", "www.bancofic.com.br", "PRD", "concluida", 300, "pub", (True, False),
         [("CDN-EDGE", "painel do provedor")]),
        ("REQ0012004", "*.hml.bancofic.com.br", "HMP", "instalado", 150, "int", (True, False),
         [("SRVHML03", "Tomcat conf/keystore.jks")]),
        ("REQ0012005", "sso.bancofic.com.br", "PRD", "instalado", -12, "int", (True, False),
         [("SRVSSO01", "IIS binding 443")]),
        ("REQ0012006", "client-integracao.bancofic.com.br", "PRD", "cert_emitido", 200, "int",
         (False, True), []),
        ("REQ0012007", "mq.bancofic.com.br", "TQS", "instalado", 45, "int", (True, True),
         [("SRVMQ01", "IBM MQ keystore .kdb")]),
        ("REQ0012008", "dev.bancofic.com.br", "DES", "csr_gerada", 90, "pub", (True, False), []),
        ("REQ0012009", "extranet.bancofic.com.br", "PRD", "aberta", 0, None, (True, False), []),
        ("REQ0012010", "relatorios.bancofic.com.br", "HMP", "cancelada", 0, None, (True, False), []),
    ]
    n_reqs = n_certs = 0
    for i, (req_no, cn, env, status, days, ca_kind, (srv, cli), locs) in enumerate(leaves):
        created = (NOW - dt.timedelta(days=random.randint(5, 170) + i * 9)
                   ).strftime("%Y-%m-%d %H:%M:%S")
        cur = conn.execute(
            """INSERT INTO reqs (req_number, cn, env, password, status, notes, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (req_no, cn, env, f"Demo!{random.randint(10000, 99999)}Xy",
             status, f"[demo] Demanda fictícia de exemplo — {cn}", created, created))
        req_id = cur.lastrowid
        n_reqs += 1
        if ca_kind:
            issuer, ikey, pid = ((issuing, issuing_key, issuing_id) if ca_kind == "int"
                                 else (pub_ca, pub_ca_key, pub_ca_id))
            sans = [cn.replace("*.", "wildcard.")] if cn.startswith("*.") else [cn]
            if not cn.startswith(("*.", "client-")):
                sans.append(cn.replace(cn.split(".")[0], cn.split(".")[0] + "-01", 1))
            cert, _ = make_cert(cn, issuer=issuer, issuer_key=ikey, days=days,
                                days_ago=random.randint(20, 300), sans=sans,
                                server=srv, client=cli)
            cert_id = insert_cert(conn, cert, req_id=req_id, parent_id=pid)
            n_certs += 1
            for server_name, path in locs:
                conn.execute(
                    """INSERT INTO install_locations (req_id, cert_id, server, path_or_store,
                       installed_at, notes) VALUES (?,?,?,?,?,?)""",
                    (req_id, cert_id, server_name, path,
                     created[:10], "[demo]"))

    # --- CSRs no repositório ---
    from cryptography.hazmat.primitives.serialization import Encoding
    for cn in ("novo-servico.bancofic.com.br", "pagamentos.bancofic.com.br"):
        k = _key()
        csr = (x509.CertificateSigningRequestBuilder()
               .subject_name(_name(cn))
               .add_extension(x509.SubjectAlternativeName([x509.DNSName(cn)]), critical=False)
               .sign(k, hashes.SHA256()))
        conn.execute(
            "INSERT INTO csrs (cn, sans, subject, key_type, sig_algo, pem) VALUES (?,?,?,?,?,?)",
            (cn, cn, csr.subject.rfc4514_string(), "RSA 2048", "sha256",
             csr.public_bytes(Encoding.PEM).decode()))

    # --- atividade espalhada nos últimos 30 dias (para o gráfico) ---
    actions = ["req_criada", "csr_gerada", "cert_importado", "status_alterado", "senha_gerada"]
    for _ in range(25):
        when = (NOW - dt.timedelta(days=random.randint(0, 29),
                                   hours=random.randint(0, 12))).strftime("%Y-%m-%d %H:%M:%S")
        conn.execute(
            "INSERT INTO activity_log (action, detail, created_at) VALUES (?,?,?)",
            (random.choice(actions), "[demo] atividade fictícia", when))

    conn.commit()
    print(f"OK — {n_reqs} demandas, {n_certs + 3} certificados (3 CAs), "
          f"2 CSRs e 25 eventos de atividade criados.")


def remove(conn):
    conn.execute("""DELETE FROM install_locations WHERE req_id IN
                    (SELECT id FROM reqs WHERE notes LIKE '%[demo]%')""")
    n_certs = conn.execute("DELETE FROM certificates WHERE source='demo'").rowcount
    n_reqs = conn.execute("DELETE FROM reqs WHERE notes LIKE '%[demo]%'").rowcount
    n_csrs = conn.execute("DELETE FROM csrs WHERE subject LIKE '%O=BancoFic%'").rowcount
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
        create(conn)
    conn.close()
