import json
from pathlib import Path

def test_prompt_path_points_to_required_file() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    trapi_client_source = (repo_root / "trapi_client.py").read_text(encoding="utf-8")
    assert '"prompts" / "get_1985_yankees.txt"' in trapi_client_source
    assert (repo_root / "prompts" / "get_1985_yankees.txt").exists()


def test_prompt_requires_schema_and_active_roster_size_constraints() -> None:
    prompt_text = (Path(__file__).resolve().parents[1] / "prompts" / "get_1985_yankees.txt").read_text(
        encoding="utf-8"
    )
    assert '{"players":[{"name":"string","position":"string","jersey_number":0}]}' in prompt_text
    assert "active 1985 New York Yankees roster members only" in prompt_text
    assert "between 24 and 28 inclusive" in prompt_text


def test_host_json_sets_timeout_and_single_concurrency() -> None:
    host_path = Path(__file__).resolve().parents[1] / "host.json"
    host_config = json.loads(host_path.read_text(encoding="utf-8"))
    assert host_config["functionTimeout"] == "00:02:00"
    assert host_config["extensions"]["queues"]["maxConcurrentCalls"] == 1


def test_local_settings_example_has_required_app03_values() -> None:
    settings_path = Path(__file__).resolve().parents[1] / "local.settings.json.example"
    settings = json.loads(settings_path.read_text(encoding="utf-8"))
    values = settings["Values"]
    required_keys = {
        "TRAPI_ENDPOINT",
        "TRAPI_DEPLOYMENT_NAME",
        "TRAPI_AUTH_SCOPE",
        "TRAPI_API_VERSION",
        "ROSTER_STORAGE_ACCOUNT_NAME",
        "ROSTER_CONTAINER_NAME",
        "WEBSITE_TIME_ZONE",
    }
    assert required_keys.issubset(values.keys())
    assert values["WEBSITE_TIME_ZONE"] == "UTC"
    placeholder_keys = {
        "TRAPI_ENDPOINT",
        "TRAPI_DEPLOYMENT_NAME",
        "TRAPI_AUTH_SCOPE",
        "TRAPI_API_VERSION",
        "ROSTER_STORAGE_ACCOUNT_NAME",
        "ROSTER_CONTAINER_NAME",
    }
    for key in placeholder_keys:
        assert values[key].startswith("<") and values[key].endswith(">")
