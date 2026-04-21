from pathlib import Path
import re


def test_monitoring_workspace_retention_is_30_days() -> None:
    source = (Path(__file__).resolve().parents[1] / "infra" / "modules" / "monitoring.bicep").read_text(encoding="utf-8")
    assert "retentionInDays: 30" in source


def test_three_ops_alert_rules_are_enabled() -> None:
    source = (Path(__file__).resolve().parents[1] / "infra" / "modules" / "alerts.bicep").read_text(encoding="utf-8")
    patterns = [
        r"resource executionFailureAlert .*?properties: \{.*?enabled: true",
        r"resource executionDurationAlert .*?properties: \{.*?enabled: true",
        r"resource playerCountOutOfRangeAlert .*?properties: \{.*?enabled: true",
    ]
    for pattern in patterns:
        assert re.search(pattern, source, flags=re.DOTALL)
