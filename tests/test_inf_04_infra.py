import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_host_timeout_set_to_120_seconds():
    host = json.loads((REPO_ROOT / "host.json").read_text(encoding="utf-8"))
    assert host["functionTimeout"] == "00:02:00"


def test_functionapp_bicep_contains_required_inf04_settings():
    bicep = (REPO_ROOT / "infra" / "modules" / "functionapp.bicep").read_text(encoding="utf-8")

    assert "Python|3.11" in bicep
    assert "type: 'SystemAssigned'" in bicep
    assert "APPLICATIONINSIGHTS_CONNECTION_STRING" in bicep
    assert "AzureWebJobsStorage__accountName" in bicep
    assert "TRAPI_ENDPOINT" in bicep
    assert "TRAPI_AUTH_SCOPE" in bicep
    assert "Microsoft.Web/sites/slots@2022-09-01" in bicep
    assert "slotConfigNames" in bicep


def test_trapi_settings_are_required_and_slot_overrides_have_fallback():
    bicep = (REPO_ROOT / "infra" / "modules" / "functionapp.bicep").read_text(encoding="utf-8")

    assert "@minLength(1)\nparam trapiEndpointSetting string" in bicep
    assert "@minLength(1)\nparam trapiAuthScopeSetting string" in bicep
    assert "var stagingTrapiEndpointValue = empty(stagingTrapiEndpointSetting) ? trapiEndpointSetting : stagingTrapiEndpointSetting" in bicep
    assert "var stagingTrapiAuthScopeValue = empty(stagingTrapiAuthScopeSetting) ? trapiAuthScopeSetting : stagingTrapiAuthScopeSetting" in bicep
