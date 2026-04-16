from pathlib import Path
import json
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[1]
INFRA_ROOT = REPO_ROOT / 'infra'


def _build_main_template() -> dict:
    result = subprocess.run(
        ['az', 'bicep', 'build', '--file', str(INFRA_ROOT / 'main.bicep'), '--stdout'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return json.loads(result.stdout)


def _iter_resources(template: dict):
    for resource in template.get('resources', []):
        yield resource
        nested = resource.get('properties', {}).get('template')
        if isinstance(nested, dict):
            yield from _iter_resources(nested)


def test_keyvault_module_enables_required_protections() -> None:
    template = _build_main_template()
    keyvault_resource = next(
        resource for resource in _iter_resources(template) if resource.get('type') == 'Microsoft.KeyVault/vaults'
    )
    properties = keyvault_resource['properties']
    sku = properties['sku']

    assert sku['name'] == 'standard', 'INF-03 requires the zone-redundant-capable Standard Key Vault SKU.'
    assert properties['softDeleteRetentionInDays'] == 90
    assert properties['enablePurgeProtection'] is True


def test_main_outputs_keyvault_uri_and_wires_reference() -> None:
    template = _build_main_template()
    outputs = template.get('outputs', {})
    function_app_deployment = next(
        resource
        for resource in _iter_resources(template)
        if resource.get('type') == 'Microsoft.Resources/deployments' and resource.get('name', '').startswith('functionApp')
    )
    function_app_variables = function_app_deployment['properties']['template']['variables']
    role_assignment = next(
        resource
        for resource in _iter_resources(template)
        if resource.get('type') == 'Microsoft.Authorization/roleAssignments'
    )

    assert 'keyVaultUri' in outputs
    assert "@Microsoft.KeyVault(SecretUri={0})" in function_app_variables['keyVaultReferenceSettings']
    assert role_assignment['properties']['principalType'] == 'ServicePrincipal'
    assert "4633458b-17de-408a-b874-0445c86b69e6" in json.dumps(template)


def test_infra_bicep_compiles() -> None:
    _build_main_template()
