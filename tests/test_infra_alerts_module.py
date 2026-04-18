from pathlib import Path


def test_alerts_module_defines_action_group_and_three_alerts():
    bicep_path = Path(__file__).resolve().parents[1] / "infra" / "modules" / "alerts.bicep"
    bicep = bicep_path.read_text(encoding="utf-8")

    assert "resource actionGroup 'Microsoft.Insights/actionGroups" in bicep
    assert "name: 'rciapala'" in bicep

    assert "resource executionFailureAlert 'Microsoft.Insights/scheduledQueryRules" in bicep
    assert "resource functionDurationAlert 'Microsoft.Insights/scheduledQueryRules" in bicep
    assert "resource playerCountLowOrHighAlert 'Microsoft.Insights/scheduledQueryRules" in bicep


def test_all_alerts_use_shared_action_group_and_five_minute_evaluation():
    bicep_path = Path(__file__).resolve().parents[1] / "infra" / "modules" / "alerts.bicep"
    bicep = bicep_path.read_text(encoding="utf-8")

    assert bicep.count("evaluationFrequency: 'PT5M'") == 3
    assert bicep.count("actionGroups: [") == 3


def test_alert_queries_cover_failures_duration_and_player_count_range():
    bicep_path = Path(__file__).resolve().parents[1] / "infra" / "modules" / "alerts.bicep"
    bicep = bicep_path.read_text(encoding="utf-8")

    assert "success == false" in bicep
    assert "Success == false" in bicep

    assert "duration > time(00:01:30)" in bicep
    assert "DurationMs > 90000" in bicep

    assert "name == \"player_count_returned\" and (value < 24 or value > 40)" in bicep
    assert "Name == \"player_count_returned\" and (Val < 24 or Val > 40)" in bicep


def test_main_bicep_wires_alerts_module():
    main_bicep_path = Path(__file__).resolve().parents[1] / "infra" / "main.bicep"
    main_bicep = main_bicep_path.read_text(encoding="utf-8")

    assert "module alerts './modules/alerts.bicep'" in main_bicep
    assert "applicationInsightsResourceId: applicationInsightsResourceId" in main_bicep
    assert "rciapalaEmailAddress: rciapalaEmailAddress" in main_bicep
