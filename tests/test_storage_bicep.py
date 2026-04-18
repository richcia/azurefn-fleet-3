from pathlib import Path


STORAGE_BICEP = Path('infra/modules/storage.bicep')


def test_storage_module_exists():
    assert STORAGE_BICEP.exists()


def test_storage_account_tier_and_shared_key_settings():
    content = STORAGE_BICEP.read_text()

    assert "name: 'Standard_LRS'" in content
    assert "accessTier: 'Cool'" in content
    assert "allowSharedKeyAccess: false" in content


def test_yankees_roster_container_private():
    content = STORAGE_BICEP.read_text()

    assert "default/yankees-roster" in content
    assert "publicAccess: 'None'" in content


def test_blob_soft_delete_enabled_for_7_days():
    content = STORAGE_BICEP.read_text()

    assert 'deleteRetentionPolicy' in content
    assert 'enabled: true' in content
    assert 'days: 7' in content


def test_dedicated_data_storage_module_contract():
    content = STORAGE_BICEP.read_text()

    # This module should only define app data storage resources.
    assert 'param storageAccountName string' in content
    assert 'AzureWebJobsStorage' not in content
