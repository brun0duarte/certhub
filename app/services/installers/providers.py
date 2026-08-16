"""Providers de instalação automatizada — um por tipo de local (`location_type`).

Providers de nuvem (Azure/AWS/Azion/Akamai) tentam a operação real, usando
credencial de conta/API cadastrada em Configurações (`installer_credentials`)
— nunca fabricam sucesso: erro real da API (autenticação, rede, recurso) é
sempre repassado em `error`. Providers de acesso a servidor (Apache/Nginx/
IIS/Mainframe) e Balanceador validam a configuração de verdade mas retornam
um bloqueio específico e honesto (lacuna de integração documentada em
`specs/005-automacao-instaladores/research.md`), sem tentar uma conexão que
não pode ser autenticada.
"""
import base64
import json
from pathlib import Path

import requests
from akamai.edgegrid import EdgeGridAuth
from botocore.exceptions import BotoCoreError, ClientError
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12

from ...db import get_db, get_setting
from ...services import passwordgen
from .base import InstallProvider

import boto3


def _installer_credentials() -> dict:
    conn = get_db()
    try:
        raw = get_setting(conn, "installer_credentials")
    finally:
        conn.close()
    try:
        return json.loads(raw or "{}")
    except (TypeError, ValueError):
        return {}


def _load_cert_pem(location: dict) -> str | None:
    """Lê o PEM do certificado vinculado ao local (`certificates.cert_pem` ou `.file_path`)."""
    cert_id = location.get("cert_id")
    if not cert_id:
        return None
    conn = get_db()
    try:
        row = conn.execute("SELECT cert_pem, file_path FROM certificates WHERE id=?", (cert_id,)).fetchone()
    finally:
        conn.close()
    if not row:
        return None
    if row["cert_pem"]:
        return row["cert_pem"]
    if row["file_path"]:
        try:
            return Path(row["file_path"]).read_text()
        except OSError:
            return None
    return None


def _decompose_pfx(data: bytes, password: str) -> tuple[str, str, str]:
    """Decompõe um PFX/P12 (bytes) em (key_pem, cert_pem, chain_pem)."""
    pwd = password.encode() if password else None
    key, cert, extra_certs = pkcs12.load_key_and_certificates(data, pwd)
    if key is None or cert is None:
        raise ValueError("arquivo PFX não contém chave privada e certificado")
    key_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode()
    chain_pem = "".join(c.public_bytes(serialization.Encoding.PEM).decode() for c in (extra_certs or []))
    return key_pem, cert_pem, chain_pem


def _load_pfx(path: str, password: str) -> tuple[str, str, str]:
    """Decompõe um PFX/P12 (arquivo em disco) em (key_pem, cert_pem, chain_pem)."""
    return _decompose_pfx(Path(path).read_bytes(), password)


def _resolve_key_material(location: dict, req: dict) -> tuple[str, str, str]:
    """Retorna (key_pem, cert_pem, chain_pem) pro provider usar. Prioriza a chave já
    gerada via HSM pra essa REQ (`reqs.hsm_label`) — sem exigir upload manual; cai pro
    PFX enviado manualmente (`uploaded_file_path`) só se a REQ não tiver chave HSM
    (REQs antigas, ou certificado importado fora do fluxo de HSM)."""
    hsm_label = (req.get("hsm_label") or "").strip()
    if hsm_label:
        from ...routers.hsm import _provider as _hsm_provider

        conn = get_db()
        try:
            policy = json.loads(get_setting(conn, "password_policy"))
            password = passwordgen.generate(**policy)
            provider = _hsm_provider(conn)
            result = provider.export_pfx(hsm_label, password)
        except Exception as e:
            raise ValueError(f"Falha ao resolver o HSM ativo: {e}") from e
        finally:
            conn.close()
        if not result.get("ok"):
            raise ValueError(result.get("output") or "Falha ao exportar a chave do HSM.")
        return _decompose_pfx(result["pfx_bytes"], password)
    uploaded = location.get("uploaded_file_path")
    if uploaded:
        return _load_pfx(uploaded, req.get("password") or "")
    raise ValueError("REQ sem chave gerada via HSM e sem arquivo enviado — gere a chave/CSR na "
                      "aba HSM antes de instalar, ou envie o PFX manualmente.")


def _missing_fields(config_fields: list[dict], config: dict) -> list[str]:
    return [f["label"] for f in config_fields
            if f.get("required") and not str(config.get(f["key"]) or "").strip()]


def _beyondtrust_blocked(config_fields: list[dict], config: dict, credential_ref: str) -> dict:
    """Validação real de configuração + bloqueio honesto: `credential_ref` é só uma referência
    ao BeyondTrust (convenção humana) — não existe integração com a API do BeyondTrust hoje pra
    resolvê-la sozinho e buscar a credencial de acesso ao servidor alvo (research.md #2)."""
    missing = _missing_fields(config_fields, config)
    if missing:
        return {"ok": False, "output": "", "error": f"Campos obrigatórios faltando: {', '.join(missing)}."}
    host = config.get("host", "")
    ref = credential_ref.strip() if credential_ref else "(nenhuma referência informada)"
    return {
        "ok": False, "output": "",
        "error": f"Automação requer buscar a credencial '{ref}' no BeyondTrust para acessar {host} — "
                 f"integração com a API do BeyondTrust ainda não implementada; use o registro indicado "
                 f"manualmente.",
    }


class BalanceadorProvider(InstallProvider):
    name = "balanceador"
    label = "Balanceador"
    config_fields = [
        {"key": "tipo", "label": "Tipo", "required": True, "options": ["CTC", "DTD"]},
        {"key": "certificate_name", "label": "Nome sugerido do certificado", "required": True},
        {"key": "host", "label": "Hostname ou IP do balanceador", "required": True},
    ]

    def install(self, *, location, req, config, credential_ref):
        missing = _missing_fields(self.config_fields, config)
        if missing:
            return {"ok": False, "output": "", "error": f"Campos obrigatórios faltando: {', '.join(missing)}."}
        tipo = config.get("tipo", "")
        return {
            "ok": False, "output": "",
            "error": f"Automação para balanceador tipo {tipo} ainda não tem integração definida — "
                     f"nenhuma API conhecida associada a esse tipo. Descreva o mecanismo de gestão desse "
                     f"balanceador pra viabilizar.",
        }


class AzureKeyVaultProvider(InstallProvider):
    name = "keyvault_azure"
    label = "Azure Key Vault"
    config_fields = [
        {"key": "vault_name", "label": "Nome do Vault", "required": True},
        {"key": "certificate_name", "label": "Nome do certificado no Vault", "required": True},
    ]
    key_source = "hsm"  # chave/certificado buscados automaticamente via reqs.hsm_label

    def install(self, *, location, req, config, credential_ref):
        creds = _installer_credentials().get("keyvault_azure") or {}
        tenant_id, client_id, client_secret = creds.get("tenant_id"), creds.get("client_id"), creds.get("client_secret")
        if not (tenant_id and client_id and client_secret):
            return {"ok": False, "output": "", "error": "Credenciais do Azure Key Vault não configuradas em Configurações."}
        try:
            key_pem, cert_pem, chain_pem = _resolve_key_material(location, req)
        except ValueError as e:
            return {"ok": False, "output": "", "error": str(e)}
        pfx_bytes = pkcs12.serialize_key_and_certificates(
            name=None,
            key=serialization.load_pem_private_key(key_pem.encode(), password=None),
            cert=x509.load_pem_x509_certificate(cert_pem.encode()),
            cas=None, encryption_algorithm=serialization.NoEncryption())
        try:
            token_resp = requests.post(
                f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token",
                data={"grant_type": "client_credentials", "client_id": client_id,
                      "client_secret": client_secret, "scope": "https://vault.azure.net/.default"},
                timeout=15)
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]
        except requests.RequestException as e:
            return {"ok": False, "output": "", "error": f"Falha ao autenticar no Azure AD: {e}"}
        except (KeyError, ValueError) as e:
            return {"ok": False, "output": "", "error": f"Resposta inesperada do Azure AD: {e}"}
        vault_name, cert_name = config.get("vault_name", ""), config.get("certificate_name", "")
        try:
            resp = requests.post(
                f"https://{vault_name}.vault.azure.net/certificates/{cert_name}/import",
                params={"api-version": "7.4"},
                headers={"Authorization": f"Bearer {access_token}"},
                json={"value": base64.b64encode(pfx_bytes).decode(), "pwd": ""},
                timeout=30)
        except requests.RequestException as e:
            return {"ok": False, "output": "", "error": f"Falha de rede ao acessar o Key Vault: {e}"}
        if resp.ok:
            return {"ok": True, "output": f"Certificado importado no Key Vault '{vault_name}' como '{cert_name}'.", "error": ""}
        return {"ok": False, "output": "", "error": f"Azure Key Vault retornou erro ({resp.status_code}): {resp.text}"}


class AwsAcmProvider(InstallProvider):
    name = "aws_cert_manager"
    label = "AWS Certificate Manager"
    config_fields = [
        {"key": "account", "label": "Conta AWS", "required": True},
        {"key": "region", "label": "Região", "required": True, "default": "sa-east-1"},
        {"key": "certificate_name", "label": "Nome do certificado", "required": True},
    ]
    key_source = "hsm"  # chave/certificado buscados automaticamente via reqs.hsm_label

    def install(self, *, location, req, config, credential_ref):
        creds = _installer_credentials().get("aws") or {}
        access_key, secret_key = creds.get("access_key_id"), creds.get("secret_access_key")
        if not (access_key and secret_key):
            return {"ok": False, "output": "", "error": "Credenciais AWS não configuradas em Configurações."}
        try:
            key_pem, cert_pem, chain_pem = _resolve_key_material(location, req)
        except ValueError as e:
            return {"ok": False, "output": "", "error": str(e)}
        region = config.get("region") or creds.get("region") or "sa-east-1"
        client = boto3.client("acm", aws_access_key_id=access_key, aws_secret_access_key=secret_key, region_name=region)
        kwargs = {"Certificate": cert_pem.encode(), "PrivateKey": key_pem.encode()}
        if chain_pem:
            kwargs["CertificateChain"] = chain_pem.encode()
        try:
            resp = client.import_certificate(**kwargs)
        except (ClientError, BotoCoreError) as e:
            return {"ok": False, "output": "", "error": f"AWS Certificate Manager retornou erro: {e}"}
        return {"ok": True, "output": f"Certificado importado no ACM: {resp.get('CertificateArn', '')}", "error": ""}


class AwsSecretsManagerProvider(InstallProvider):
    name = "secrets_manager"
    label = "AWS Secrets Manager"
    config_fields = [
        {"key": "account", "label": "Conta AWS", "required": True},
        {"key": "region", "label": "Região", "required": True, "default": "sa-east-1"},
        {"key": "secret_name", "label": "Nome do secret", "required": True},
    ]
    # Segredo grava 3 chaves fixas (tls.crt/tls.key/ca.crt).
    key_source = "hsm"  # chave/certificado buscados automaticamente via reqs.hsm_label

    def install(self, *, location, req, config, credential_ref):
        creds = _installer_credentials().get("aws") or {}
        access_key, secret_key = creds.get("access_key_id"), creds.get("secret_access_key")
        if not (access_key and secret_key):
            return {"ok": False, "output": "", "error": "Credenciais AWS não configuradas em Configurações."}
        try:
            key_pem, cert_pem, chain_pem = _resolve_key_material(location, req)
        except ValueError as e:
            return {"ok": False, "output": "", "error": str(e)}
        region = config.get("region") or creds.get("region") or "sa-east-1"
        client = boto3.client("secretsmanager", aws_access_key_id=access_key, aws_secret_access_key=secret_key,
                               region_name=region)
        secret_value = json.dumps({"tls.crt": cert_pem, "tls.key": key_pem, "ca.crt": chain_pem})
        secret_name = config.get("secret_name", "")
        try:
            client.put_secret_value(SecretId=secret_name, SecretString=secret_value)
        except (ClientError, BotoCoreError) as e:
            return {"ok": False, "output": "", "error": f"AWS Secrets Manager retornou erro: {e}"}
        return {"ok": True, "output": f"Secret '{secret_name}' atualizado no Secrets Manager.", "error": ""}


class AzionProvider(InstallProvider):
    name = "azion"
    label = "Azion Edge Certificates"
    config_fields = [
        {"key": "certificate_name", "label": "Nome do certificado", "required": True},
    ]
    # POST /v4/workspace/tls/certificates — cert e chave viajam no mesmo payload (texto).
    key_source = "hsm"  # chave/certificado buscados automaticamente via reqs.hsm_label

    def install(self, *, location, req, config, credential_ref):
        creds = _installer_credentials().get("azion") or {}
        api_token = creds.get("api_token")
        if not api_token:
            return {"ok": False, "output": "", "error": "Token da Azion não configurado em Configurações."}
        try:
            key_pem, cert_pem, _chain_pem = _resolve_key_material(location, req)
        except ValueError as e:
            return {"ok": False, "output": "", "error": str(e)}
        try:
            resp = requests.post(
                "https://api.azion.com/v4/workspace/tls/certificates",
                headers={"Authorization": f"Bearer {api_token}", "Accept": "application/json"},
                json={"name": config.get("certificate_name", ""), "certificate": cert_pem, "private_key": key_pem,
                      "type": "edge_certificate", "active": True},
                timeout=30)
        except requests.RequestException as e:
            return {"ok": False, "output": "", "error": f"Falha de rede ao acessar a Azion: {e}"}
        if resp.ok:
            output = f"Certificado importado na Azion ({resp.status_code})."
            try:
                data = resp.json().get("data", {})
                status_detail = f" ({data['status_detail']})" if data.get("status_detail") else ""
                output = (f"Certificado importado na Azion (ID {data['id']}) — status: {data['status']}"
                          f"{status_detail} · válido até {data.get('validity', '—')} · "
                          f"chave: {data.get('key_algorithm', '—')}.")
            except (ValueError, KeyError):
                pass
            return {"ok": True, "output": output, "error": ""}
        return {"ok": False, "output": "", "error": f"Azion retornou erro ({resp.status_code}): {resp.text}"}


class AkamaiProvider(InstallProvider):
    name = "akamai"
    label = "Akamai (CPS)"
    config_fields = [
        {"key": "enrollment_id", "label": "Enrollment ID", "required": True},
    ]
    # Enrollments de terceiro geram o CSR no próprio Akamai — a chave privada
    # fica lá, só cert+cadeia (assinados externamente) precisam ser enviados.

    def install(self, *, location, req, config, credential_ref):
        creds = _installer_credentials().get("akamai") or {}
        client_token, client_secret = creds.get("client_token"), creds.get("client_secret")
        access_token, host = creds.get("access_token"), creds.get("host")
        if not (client_token and client_secret and access_token and host):
            return {"ok": False, "output": "", "error": "Credenciais Akamai (EdgeGrid) não configuradas em Configurações."}
        enrollment_id = config.get("enrollment_id", "")
        cert_pem = _load_cert_pem(location)
        if not cert_pem:
            return {"ok": False, "output": "", "error": "Nenhum certificado vinculado a este local para enviar ao Akamai CPS."}
        base_url = host if host.startswith("http") else f"https://{host}"
        auth = EdgeGridAuth(client_token=client_token, client_secret=client_secret, access_token=access_token)
        try:
            enrollment_resp = requests.get(
                f"{base_url}/cps/v2/enrollments/{enrollment_id}", auth=auth,
                headers={"Accept": "application/vnd.akamai.cps.enrollment.v11+json"}, timeout=20)
            enrollment_resp.raise_for_status()
            pending = enrollment_resp.json().get("pendingChanges") or []
        except requests.RequestException as e:
            return {"ok": False, "output": "", "error": f"Falha ao consultar o enrollment {enrollment_id} no Akamai CPS: {e}"}
        if not pending:
            return {"ok": False, "output": "",
                     "error": f"Enrollment {enrollment_id} não tem mudança pendente no Akamai CPS — inicie a "
                              f"mudança de certificado no CPS antes de automatizar o envio."}
        first = pending[0]
        change_path = first if isinstance(first, str) else first.get("location", "")
        try:
            resp = requests.put(
                f"{base_url}{change_path}/input/update/third-party-csr", auth=auth,
                headers={"Content-Type": "application/vnd.akamai.cps.certificate-and-trust-chain.v2+json",
                         "Accept": "application/vnd.akamai.cps.change-id.v1+json"},
                json={"certificatesAndTrustChains": [{"certificate": cert_pem, "trustChain": ""}]},
                timeout=30)
        except requests.RequestException as e:
            return {"ok": False, "output": "", "error": f"Falha de rede ao enviar certificado ao Akamai CPS: {e}"}
        if resp.ok:
            return {"ok": True, "output": f"Certificado enviado ao Akamai CPS (enrollment {enrollment_id}).", "error": ""}
        return {"ok": False, "output": "", "error": f"Akamai CPS retornou erro ({resp.status_code}): {resp.text}"}


class ApacheSshProvider(InstallProvider):
    name = "apache"
    label = "Apache (SSH)"
    config_fields = [
        {"key": "host", "label": "Host", "required": True},
        {"key": "port", "label": "Porta SSH", "required": False, "default": "22"},
        {"key": "remote_cert_path", "label": "Caminho remoto do certificado", "required": True},
        {"key": "remote_key_path", "label": "Caminho remoto da chave", "required": True},
        {"key": "reload_command", "label": "Comando de reload", "required": False},
    ]

    def install(self, *, location, req, config, credential_ref):
        return _beyondtrust_blocked(self.config_fields, config, credential_ref)


class NginxSshProvider(InstallProvider):
    name = "nginx"
    label = "Nginx (SSH)"
    config_fields = ApacheSshProvider.config_fields

    def install(self, *, location, req, config, credential_ref):
        return _beyondtrust_blocked(self.config_fields, config, credential_ref)


class IisWinrmProvider(InstallProvider):
    name = "iis"
    label = "IIS (PowerShell Remoting)"
    config_fields = [
        {"key": "host", "label": "Host", "required": True},
        {"key": "winrm_port", "label": "Porta WinRM", "required": False, "default": "5986"},
        {"key": "cert_store", "label": "Store", "required": False, "default": "LocalMachine\\My"},
    ]
    requires_file = True  # upload do .pfx — senha é a mesma da demanda (aba Informações)
    key_source = "upload"

    def install(self, *, location, req, config, credential_ref):
        return _beyondtrust_blocked(self.config_fields, config, credential_ref)


class MainframeRacdcertProvider(InstallProvider):
    name = "mainframe"
    label = "Mainframe RACDCERT (REXX/SSH)"
    config_fields = [
        {"key": "host", "label": "Host USS (z/OS Unix System Services)", "required": True},
        {"key": "keyring", "label": "Keyring RACF", "required": True},
        {"key": "userid_label", "label": "Label do certificado", "required": True},
    ]

    def install(self, *, location, req, config, credential_ref):
        return _beyondtrust_blocked(self.config_fields, config, credential_ref)
