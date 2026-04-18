import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STORAGE_BICEP = REPO_ROOT / 'infra/modules/storage.bicep'
MAIN_BICEP = REPO_ROOT / 'infra/main.bicep'


def _build_bicep_to_json(bicep_path: Path, tmp_path: Path) -> dict:
    output_path = tmp_path / f'{bicep_path.stem}.json'
    subprocess.run(
        ['az', 'bicep', 'build', '--file', str(bicep_path), '--outfile', str(output_path)],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return json.loads(output_path.read_text())


def _find_resource(template: dict, resource_type: str) -> dict:
    return next(resource for resource in template['resources'] if resource['type'] == resource_type)


def test_storage_account_tier_and_shared_key_settings(tmp_path):
    template = _build_bicep_to_json(STORAGE_BICEP, tmp_path)
    storage_account = _find_resource(template, 'Microsoft.Storage/storageAccounts')

    assert storage_account['sku']['name'] == 'Standard_LRS'
    assert storage_account['properties']['accessTier'] == 'Cool'
    assert storage_account['properties']['allowSharedKeyAccess'] is False


def test_yankees_roster_container_private(tmp_path):
    template = _build_bicep_to_json(STORAGE_BICEP, tmp_path)
    container = _find_resource(template, 'Microsoft.Storage/storageAccounts/blobServices/containers')

    assert 'yankees-roster' in container['name']
    assert container['properties']['publicAccess'] == 'None'


def test_blob_soft_delete_enabled_for_7_days(tmp_path):
    template = _build_bicep_to_json(STORAGE_BICEP, tmp_path)
    blob_service = _find_resource(template, 'Microsoft.Storage/storageAccounts/blobServices')

    retention = blob_service['properties']['deleteRetentionPolicy']
    assert retention['enabled'] is True
    assert retention['days'] == 7


def test_dedicated_storage_is_separate_from_host_storage(tmp_path):
    template = _build_bicep_to_json(MAIN_BICEP, tmp_path)

    deployment_resource = _find_resource(template, 'Microsoft.Resources/deployments')
    assert deployment_resource['name'] == 'data-storage'

    parameters = template['parameters']
    assert 'dataStorageAccountName' in parameters
    assert 'hostStorageAccountName' in parameters
    assert 'data' in parameters['dataStorageAccountName']['defaultValue']
    assert 'host' in parameters['hostStorageAccountName']['defaultValue']
