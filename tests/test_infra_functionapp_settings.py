import json
from pathlib import Path


def test_functionapp_template_trapi_settings_use_expected_sources():
    template_path = Path(__file__).resolve().parents[1] / "infra" / "modules" / "functionapp.json"
    template = json.loads(template_path.read_text(encoding="utf-8"))

    function_apps = [resource for resource in template["resources"] if resource["type"] == "Microsoft.Web/sites"]
    assert function_apps, "Expected Microsoft.Web/sites resource in functionapp.json template."
    function_app = function_apps[0]
    app_settings = function_app["properties"]["siteConfig"]["appSettings"]
    values_by_name = {setting["name"]: setting["value"] for setting in app_settings}

    assert values_by_name["TRAPI_ENDPOINT"].startswith("[format('@Microsoft.KeyVault(")
    assert values_by_name["TRAPI_AUTH_SCOPE"] == "[parameters('trapiAuthScope')]"
