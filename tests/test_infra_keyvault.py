from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_ROOT = REPO_ROOT / 'infra'


def test_keyvault_module_enables_required_protections() -> None:
    keyvault_file = INFRA_ROOT / 'modules' / 'keyvault.bicep'
    content = keyvault_file.read_text(encoding='utf-8')

    assert "name: 'standard'" in content
    assert 'softDeleteRetentionInDays: 90' in content
    assert 'enablePurgeProtection: true' in content


def test_main_outputs_keyvault_uri_and_wires_reference() -> None:
    main_file = INFRA_ROOT / 'main.bicep'
    functionapp_file = INFRA_ROOT / 'modules' / 'functionapp.bicep'

    main_content = main_file.read_text(encoding='utf-8')
    functionapp_content = functionapp_file.read_text(encoding='utf-8')

    assert 'output keyVaultUri string' in main_content
    assert "@Microsoft.KeyVault(SecretUri=${trapiCredentialSecretUri})" in functionapp_content


def test_infra_bicep_compiles() -> None:
    result = subprocess.run(
        ['az', 'bicep', 'build', '--file', str(INFRA_ROOT / 'main.bicep')],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr or result.stdout
