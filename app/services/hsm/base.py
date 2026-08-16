"""Interface comum dos provedores de chave (local, hsmutil CLI, SDK Dinamo)."""
from abc import ABC, abstractmethod

# Vocabulário de erro compartilhado entre providers "estilo HSM" (Dinamo real e
# simulado) — garante os mesmos códigos HTTP e mensagens em PT-BR nos dois.
ERROR_STATUS = {
    "ALREADY_EXISTS": 409,
    "NOT_FOUND": 404,
    "KEY_MISMATCH": 422,
    "NOT_EXPORTABLE": 403,
    "CONN_FAILED": 502,
    "TIMEOUT": 502,
}

ERROR_MESSAGES = {
    "ALREADY_EXISTS": "Já existe uma chave com esse rótulo no HSM.",
    "NOT_FOUND": "Chave não encontrada no HSM.",
    "KEY_MISMATCH": "O certificado não corresponde à chave pública dessa entrada no HSM.",
    "NOT_EXPORTABLE": "Essa chave está marcada como não exportável no HSM.",
    "CONN_FAILED": "Não foi possível conectar ao HSM. Verifique host/usuário/senha em Configurações.",
    "TIMEOUT": "O HSM não respondeu a tempo.",
}


class KeyProvider(ABC):
    name: str = "base"

    @abstractmethod
    def gen_key(self, label: str, key_type: str = "rsa2048", **kwargs) -> dict:
        """Gera uma chave. Retorna {'ok': bool, 'output': str, ...}."""

    @abstractmethod
    def gen_csr(self, label: str, cn: str, sans: list[str] | None = None,
                key_type: str = "rsa2048", **kwargs) -> dict:
        """Gera uma CSR. Retorna {'ok': bool, 'csr_pem': str|None, 'output': str}."""

    @abstractmethod
    def export_key(self, label: str, out_path: str, **kwargs) -> dict:
        """Exporta a chave. Retorna {'ok': bool, 'output': str}."""
