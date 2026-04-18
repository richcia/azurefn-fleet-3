import json
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

import pytest


@lru_cache(maxsize=1)
def _load_compiled_main_template() -> dict:
    if shutil.which('az') is None:
        pytest.skip('Azure CLI is required for INF-04 Bicep semantic tests (az bicep build).')

    result = subprocess.run(
        ['az', 'bicep', 'build', '--file', 'infra/main.bicep', '--stdout'],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@lru_cache(maxsize=1)
def _load_host_sampling_settings() -> dict:
    host = json.loads(Path('host.json').read_text(encoding='utf-8'))
    return host['logging']['applicationInsights']['samplingSettings']


def _find_module_deployment(main_template: dict, module_name: str) -> dict:
    return next(
        resource
        for resource in main_template['resources']
        if resource['type'] == 'Microsoft.Resources/deployments' and resource['name'] == module_name
    )


def test_host_sampling_settings_enabled() -> None:
    sampling = _load_host_sampling_settings()

    assert sampling['isEnabled'] is True
    assert sampling['excludedTypes'] == 'Request;Exception'


def test_monitoring_module_compiles_to_workspace_based_app_insights_with_30_day_retention() -> None:
    main_template = _load_compiled_main_template()
    monitoring_module = _find_module_deployment(main_template, 'monitoring')
    monitoring_template = monitoring_module['properties']['template']

    workspace_resource = next(
        resource
        for resource in monitoring_template['resources']
        if resource['type'] == 'Microsoft.OperationalInsights/workspaces'
    )
    app_insights_resource = next(
        resource
        for resource in monitoring_template['resources']
        if resource['type'] == 'Microsoft.Insights/components'
    )

    assert workspace_resource['properties']['retentionInDays'] == 30
    assert app_insights_resource['properties']['RetentionInDays'] == 30
    assert app_insights_resource['properties']['IngestionMode'] == 'LogAnalytics'
    assert 'Microsoft.OperationalInsights/workspaces' in app_insights_resource['properties']['WorkspaceResourceId']


def test_connection_string_and_sampling_settings_are_wired_to_functionapp_module() -> None:
    main_template = _load_compiled_main_template()
    monitoring_module = _find_module_deployment(main_template, 'monitoring')
    functionapp_module = _find_module_deployment(main_template, 'functionappSettings')
    host_sampling = _load_host_sampling_settings()

    assert 'applicationInsightsConnectionString' in monitoring_module['properties']['template']['outputs']

    functionapp_parameters = functionapp_module['properties']['parameters']
    app_insights_connection_ref = functionapp_parameters['applicationInsightsConnectionString']['value']
    sampling_settings_ref = functionapp_parameters['samplingSettings']['value']

    assert '.outputs.applicationInsightsConnectionString.value' in app_insights_connection_ref
    assert '.outputs.samplingSettings.value' in sampling_settings_ref

    monitoring_sampling = monitoring_module['properties']['template']['variables']['samplingSettings']
    assert monitoring_sampling['isEnabled'] == host_sampling['isEnabled']
    assert monitoring_sampling['excludedTypes'] == host_sampling['excludedTypes']

    functionapp_settings = functionapp_module['properties']['template']['variables']['monitoringAppSettings']
    assert 'APPLICATIONINSIGHTS_CONNECTION_STRING' in functionapp_settings
    assert (
        functionapp_settings['AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__isEnabled']
        == "[string(parameters('samplingSettings').isEnabled)]"
    )
    assert (
        functionapp_settings['AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__excludedTypes']
        == "[string(parameters('samplingSettings').excludedTypes)]"
    )
