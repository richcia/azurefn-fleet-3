from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STORAGE_MODULE = REPO_ROOT / "infra" / "modules" / "storage.bicep"
MAIN_TEMPLATE = REPO_ROOT / "infra" / "main.bicep"


def test_storage_module_sets_required_storage_properties() -> None:
    content = STORAGE_MODULE.read_text(encoding="utf-8")

    assert "name: 'Standard_LRS'" in content
    assert "accessTier: 'Cool'" in content
    assert "allowSharedKeyAccess: false" in content
    assert "deleteRetentionPolicy" in content
    assert "days: 7" in content


def test_storage_module_provisions_private_yankees_roster_container() -> None:
    content = STORAGE_MODULE.read_text(encoding="utf-8")

    assert "name: 'yankees-roster'" in content
    assert "publicAccess: 'None'" in content
    assert "allowBlobPublicAccess: false" in content


def test_main_template_exports_storage_resource_id_and_host_separation_flag() -> None:
    content = MAIN_TEMPLATE.read_text(encoding="utf-8")

    assert "output storageAccountResourceId string" in content
    assert "param functionHostStorageAccountName string = ''" in content
    assert "output storageDistinctFromHost bool" in content
