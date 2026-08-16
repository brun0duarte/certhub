import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.revocation.ac_interna import AcInternaRevocationProvider
from app.services.revocation.internacional import InternacionalRevocationProvider
from app.services.revocation.outros import OutrosRevocationProvider
from app.services.revocation.serpro import SerproRevocationProvider


def _assert_not_connected(result, label_substring):
    assert result["ok"] is False
    assert result["code"] == "NOT_CONNECTED"
    assert label_substring in result["output"]


def test_internacional_provider_not_connected():
    result = InternacionalRevocationProvider().revoke("www.exemplo.com.br", serial="AA", thumbprint="BB")
    _assert_not_connected(result, "CA Internacional")


def test_serpro_provider_not_connected():
    result = SerproRevocationProvider().revoke("www.exemplo.com.br")
    _assert_not_connected(result, "Serpro")


def test_ac_interna_nprd_provider_not_connected():
    result = AcInternaRevocationProvider(ambiente="nprd").revoke("www.exemplo.com.br")
    _assert_not_connected(result, "AC Interna NPRD")


def test_ac_interna_prd_provider_not_connected():
    result = AcInternaRevocationProvider(ambiente="prd").revoke("www.exemplo.com.br")
    _assert_not_connected(result, "AC Interna PRD")


def test_ac_interna_provider_defaults_to_nprd_for_unknown_ambiente():
    provider = AcInternaRevocationProvider(ambiente="algo-invalido")
    assert provider.ambiente == "nprd"
    assert provider.label == "AC Interna NPRD"


def test_outros_provider_not_connected():
    result = OutrosRevocationProvider().revoke("www.exemplo.com.br")
    _assert_not_connected(result, "destino informado")


def test_providers_reject_empty_cn():
    for provider in (InternacionalRevocationProvider(), SerproRevocationProvider(),
                      AcInternaRevocationProvider(), OutrosRevocationProvider()):
        result = provider.revoke("   ")
        assert result["ok"] is False
        assert result["code"] == "INVALID_INPUT"
