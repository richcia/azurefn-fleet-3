import json
from pathlib import Path

import pytest

HOST_JSON_PATH = Path(__file__).resolve().parent.parent / "host.json"


@pytest.mark.unit
def test_host_json_exists():
    assert HOST_JSON_PATH.exists(), "host.json must exist at the repo root"


@pytest.mark.unit
def test_host_json_is_valid_json():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    assert isinstance(config, dict)


@pytest.mark.unit
def test_host_json_schema_version():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    assert config.get("version") == "2.0", "host.json must use schema version 2.0"


@pytest.mark.unit
def test_host_json_function_timeout():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    assert config.get("functionTimeout") == "00:02:00", "functionTimeout must be 00:02:00 (120 seconds)"


@pytest.mark.unit
def test_host_json_max_concurrent_requests():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    assert config.get("extensions", {}).get("http", {}).get("maxConcurrentRequests") == 1


@pytest.mark.unit
def test_host_json_logging_level():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    assert config.get("logging", {}).get("logLevel", {}).get("default") == "Information"


@pytest.mark.unit
def test_host_json_aggregator():
    with HOST_JSON_PATH.open(encoding="utf-8") as f:
        config = json.load(f)
    aggregator = config.get("aggregator", {})
    assert aggregator.get("batchSize") == 1000
    assert aggregator.get("flushTimeout") == "00:00:30"
