import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STORAGE_MODULE = REPO_ROOT / "infra" / "modules" / "storage.bicep"
MAIN_TEMPLATE = REPO_ROOT / "infra" / "main.bicep"


def _build_template(path: Path) -> dict:
    result = subprocess.run(
        ["bicep", "build", str(path), "--stdout"],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def test_storage_module_sets_required_storage_properties() -> None:
    template = _build_template(STORAGE_MODULE)
    resources = template["resources"]
    storage_account = next(resource for resource in resources if resource["type"] == "Microsoft.Storage/storageAccounts")

    assert storage_account["sku"]["name"] == "Standard_LRS"
    assert storage_account["properties"]["accessTier"] == "Cool"
    assert storage_account["properties"]["allowSharedKeyAccess"] is False
    assert storage_account["properties"]["allowBlobPublicAccess"] is False

    blob_service = next(
        resource for resource in resources if resource["type"] == "Microsoft.Storage/storageAccounts/blobServices"
    )
    assert blob_service["properties"]["deleteRetentionPolicy"] == {"enabled": True, "days": 7}


def test_storage_module_provisions_private_yankees_roster_container() -> None:
    template = _build_template(STORAGE_MODULE)
    container = next(
        resource
        for resource in template["resources"]
        if resource["type"] == "Microsoft.Storage/storageAccounts/blobServices/containers"
    )

    assert "yankees-roster" in container["name"]
    assert "default" in container["name"]
    assert container["properties"]["publicAccess"] == "None"


def test_main_template_requires_host_storage_name_and_exports_outputs() -> None:
    template = _build_template(MAIN_TEMPLATE)
    outputs = template["outputs"]
    parameters = template["parameters"]
    separation_output = outputs["storageDistinctFromHost"]["value"]
    separation_variable = template["variables"]["storageDistinctFromHost"]
    guard = next(
        resource
        for resource in template["resources"]
        if resource["name"] == "[format('{0}-', take(parameters('storageAccountName'), 23))]"
    )

    assert "functionHostStorageAccountName" in parameters
    assert "defaultValue" not in parameters["functionHostStorageAccountName"]
    assert "storageAccountResourceId" in outputs
    assert separation_output == "[variables('storageDistinctFromHost')]"
    assert "not(equals(" in separation_variable
    assert "condition" in guard
    assert "take(parameters('storageAccountName'), 23)" in guard["name"]
