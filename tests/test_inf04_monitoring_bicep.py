import json
from pathlib import Path


def test_host_sampling_settings_enabled_and_exclusions_match_issue_requirement() -> None:
    host = json.loads(Path('host.json').read_text(encoding='utf-8'))
    sampling = host['logging']['applicationInsights']['samplingSettings']

    assert sampling['isEnabled'] is True
    assert sampling['excludedTypes'] == 'Request;Exception'


def test_monitoring_bicep_sets_workspace_based_app_insights_with_30_day_retention_and_loganalytics_mode() -> None:
    content = Path('infra/modules/monitoring.bicep').read_text(encoding='utf-8')

    assert "resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces" in content
    assert "retentionInDays: 30" in content
    assert "resource appInsights 'Microsoft.Insights/components" in content
    assert "WorkspaceResourceId: logAnalyticsWorkspace.id" in content
    assert "RetentionInDays: 30" in content
    assert "IngestionMode: 'LogAnalytics'" in content


def test_connection_string_output_and_function_app_sampling_wiring_exist() -> None:
    monitoring_content = Path('infra/modules/monitoring.bicep').read_text(encoding='utf-8')
    main_content = Path('infra/main.bicep').read_text(encoding='utf-8')
    functionapp_content = Path('infra/modules/functionapp.bicep').read_text(encoding='utf-8')

    assert 'output applicationInsightsConnectionString string' in monitoring_content
    assert "applicationInsightsConnectionString: monitoring.outputs.applicationInsightsConnectionString" in main_content

    assert 'APPLICATIONINSIGHTS_CONNECTION_STRING' in functionapp_content
    assert 'AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__isEnabled' in functionapp_content
    assert 'AzureFunctionsJobHost__logging__applicationInsights__samplingSettings__excludedTypes' in functionapp_content
    assert "excludedTypes: 'Request;Exception'" in functionapp_content
