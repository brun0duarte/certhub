"""Registro de providers de instalação automatizada, chaveado por location_type
(mesmas chaves de app.db.INSTALL_LOCATIONS / app.js INSTALL_TYPES)."""
from .providers import (
    AkamaiProvider, ApacheSshProvider, AwsAcmProvider, AwsSecretsManagerProvider,
    AzionProvider, AzureKeyVaultProvider, BalanceadorProvider, IisWinrmProvider,
    MainframeRacdcertProvider, NginxSshProvider,
)

PROVIDERS = {
    p.name: p()
    for p in (
        BalanceadorProvider, AzureKeyVaultProvider, AwsAcmProvider, AwsSecretsManagerProvider,
        AzionProvider, AkamaiProvider, ApacheSshProvider, NginxSshProvider,
        IisWinrmProvider, MainframeRacdcertProvider,
    )
}
