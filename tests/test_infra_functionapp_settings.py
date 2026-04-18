import json
from pathlib import Path


def test_functionapp_template_trapi_settings_use_expected_sources():
    template_path = Path(__file__).resolve().parents[1] / "infra" / "modules" / "functionapp.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))

    app_settings = template["resources"][1]["properties"]["siteConfig"]["appSettings"]
    values_by_name = {setting["name"]: setting["value"] for setting in app_settings}

    assert values_by_name["TRAPI_ENDPOINT"].startswith("[format('@Microsoft.KeyVault(")
    assert values_by_name["TRAPI_AUTH_SCOPE"] == "[parameters('trapiAuthScope')]"
