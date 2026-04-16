import json
from pathlib import Path


def test_host_json_timeout_and_concurrency():
    host_config = json.loads(Path("host.json").read_text(encoding="utf-8"))

    assert host_config["functionTimeout"] == "00:02:00"
    assert host_config["extensions"]["serviceBus"]["messageHandlerOptions"]["maxConcurrentCalls"] == 1
