import json
from pathlib import Path


def _load_main_template() -> dict:
    return json.loads(Path('infra/main.json').read_text(encoding='utf-8'))


def _find_nested_resource(main_template: dict, deployment_name: str) -> dict:
    deployment = next(
        resource
        for resource in main_template['resources']
        if resource['type'] == 'Microsoft.Resources/deployments' and resource['name'] == deployment_name
    )
    return deployment['properties']['template']


def test_host_sampling_settings_enabled_and_exclusions_match_issue_requirement() -> None:
    host = json.loads(Path('host.json').read_text(encoding='utf-8'))
    sampling = host['logging']['applicationInsights']['samplingSettings']

    assert sampling['isEnabled'] is True
    assert sampling['excludedTypes'] == 'Request;Exception'


def test_monitoring_module_compilation_has_workspace_linkage_and_30_day_retention() -> None:
    monitoring_template = _find_nested_resource(_load_main_template(), 'monitoring')
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


def test_connection_string_output_and_function_app_sampling_wiring_exist() -> None:
    main_template = _load_main_template()
    monitoring_template = _find_nested_resource(main_template, 'monitoring')
    functionapp_template = _find_nested_resource(main_template, 'functionappSettings')

    assert 'applicationInsightsConnectionString' in monitoring_template['outputs']

    functionapp_params = next(
        resource
        for resource in main_template['resources']
        if resource['type'] == 'Microsoft.Resources/deployments' and resource['name'] == 'functionappSettings'
    )['properties']['parameters']

    assert functionapp_params['applicationInsightsConnectionString']['value'] == (
        "[reference(resourceId('Microsoft.Resources/deployments', 'monitoring'), "
        "'2025-04-01').outputs.applicationInsightsConnectionString.value]"
    )

    monitoring_settings = functionapp_template['variables']['monitoringAppSettings']
    assert 'APPLICATIONINSIGHTS_CONNECTION_STRING' in monitoring_settings
    assert (
        monitoring_settings[
            'AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__isEnabled'
        ]
        == "[string(parameters('samplingSettings').isEnabled)]"
    )
    assert (
        monitoring_settings[
            'AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__excludedTypes'
        ]
        == "[string(parameters('samplingSettings').excludedTypes)]"
    )
