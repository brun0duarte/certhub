"""Interface comum dos provedores de chave (local, hsmutil CLI, SDK Dinamo)."""
from abc import ABC, abstractmethod


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
