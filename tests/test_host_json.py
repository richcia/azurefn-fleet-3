import json
from pathlib import Path


def test_app_06_host_json_settings():
    host = json.loads(Path("host.json").read_text())

    assert host.get("functionTimeout") == "00:02:00"
    assert (
        host.get("logging", {})
        .get("applicationInsights", {})
        .get("samplingSettings", {})
        .get("isEnabled")
        is True
    )
    assert (
        host.get("logging", {})
        .get("applicationInsights", {})
        .get("samplingSettings", {})
        .get("excludedTypes")
        == "Request;Exception"
    )
    assert host.get("extensions", {}).get("timerTrigger", {}).get("maxConcurrentCalls") == 1
    assert host.get("extensionBundle", {}).get("version") == "[4.*, 5.0.0)"
