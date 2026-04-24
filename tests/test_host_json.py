import json
from pathlib import Path

import pytest

HOST_JSON_PATH = Path(__file__).resolve().parent.parent / "host.json"


@pytest.fixture(scope="module")
def host_config():
    if not HOST_JSON_PATH.exists():
        pytest.skip("host.json not found — skipping content tests")
    content = HOST_JSON_PATH.read_text(encoding="utf-8")
    try:
        config = json.loads(content)
    except json.JSONDecodeError as exc:
        pytest.fail(f"host.json is not valid JSON: {exc}")
    assert isinstance(config, dict), "host.json root must be a JSON object"
    return config


@pytest.mark.unit
def test_host_json_exists():
    assert HOST_JSON_PATH.exists(), "host.json must exist at the repo root"


@pytest.mark.unit
def test_host_json_is_valid_json(host_config):
    assert isinstance(host_config, dict)


@pytest.mark.unit
def test_host_json_schema_version(host_config):
    assert host_config.get("version") == "2.0", "host.json must use schema version 2.0"


@pytest.mark.unit
def test_host_json_function_timeout(host_config):
    assert host_config.get("functionTimeout") == "00:02:00", "functionTimeout must be 00:02:00 (120 seconds)"


@pytest.mark.unit
def test_host_json_max_concurrent_requests(host_config):
    assert host_config.get("extensions", {}).get("http", {}).get("maxConcurrentRequests") == 1


@pytest.mark.unit
def test_host_json_logging_level(host_config):
    assert host_config.get("logging", {}).get("logLevel", {}).get("default") == "Information"


@pytest.mark.unit
def test_host_json_aggregator(host_config):
    aggregator = host_config.get("aggregator", {})
    assert aggregator.get("batchSize") == 1000
    assert aggregator.get("flushTimeout") == "00:00:30"
