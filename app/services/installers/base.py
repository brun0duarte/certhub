"""Interface comum dos providers de instalação automatizada por local (Azure,
AWS, Azion, Apache/Nginx/IIS, mainframe, Akamai...)."""
from abc import ABC, abstractmethod


class InstallProvider(ABC):
    name: str = "base"
    label: str = "Base"
    # Campos não-sensíveis capturados no formulário do local (vault name, ARN,
    # host, etc). Credenciais de acesso ao alvo NUNCA passam por aqui — ficam
    # no BeyondTrust, o local só guarda uma referência (`credential_ref`).
    config_fields: list[dict] = []
    # Se True, a UI mostra upload de arquivo (PFX) — só quando `key_source`
    # não resolve a chave sozinho (ver abaixo).
    requires_file: bool = False
    # De onde vem a chave privada/certificado usados por `install()`:
    # "none" (provider não precisa de material de certificado — configuração
    # pura, ex. Apache/Balanceador), "hsm" (busca automática via
    # `reqs.hsm_label` — sem upload, ver `_resolve_key_material` em
    # `providers.py`), "upload" (só via arquivo enviado manualmente, `requires_file`).
    key_source: str = "none"

    @abstractmethod
    def install(self, *, location: dict, req: dict, config: dict, credential_ref: str) -> dict:
        """Executa a instalação. Retorna sempre {'ok': bool, 'output': str, 'error': str}."""
