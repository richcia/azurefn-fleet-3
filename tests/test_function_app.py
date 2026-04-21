from __future__ import annotations

import importlib
import logging
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest


def _reload_function_app():
    sys.modules.pop("function_app", None)
    return importlib.import_module("function_app")


def test_function_emits_required_events_and_metric(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o-2025-04-01")
    module = _reload_function_app()

    mock_counter = Mock()
    monkeypatch.setattr(module, "_PLAYER_COUNT_RETURNED", mock_counter)

    class _Writer:
        def write(self, payload: dict[str, object], run_date_utc: str) -> str:
            assert payload
            assert run_date_utc
            logging.getLogger("function_app").info("blob_write_succeeded", extra={"blob_uri": "https://example/blob"})
            return "https://example/blob"

        def write_failed(self, payload: object, run_date_utc: str) -> None:
            raise AssertionError("write_failed should not be called in success path")

    monkeypatch.setattr(module, "BlobWriter", _Writer)
    monkeypatch.setattr(
        module,
        "fetch_1985_yankees_roster",
        lambda: {
            "players": [{"name": f"Player {i}", "position": "P", "jersey_number": i} for i in range(1, 25)],
            "usage": {"total_tokens": 123},
        },
    )

    caplog.set_level(logging.INFO)
    module.get_and_store_yankees_roster(timer=object())

    function_started_logs = [record for record in caplog.records if record.message == "function_started"]
    trapi_request_logs = [record for record in caplog.records if record.message == "trapi_request_sent"]
    trapi_response_logs = [record for record in caplog.records if record.message == "trapi_response_received"]
    blob_write_logs = [record for record in caplog.records if record.message == "blob_write_succeeded"]
    function_completed_logs = [record for record in caplog.records if record.message == "function_completed"]

    assert len(function_started_logs) == 1
    assert len(trapi_request_logs) == 1
    assert len(trapi_response_logs) == 1
    assert len(blob_write_logs) == 1
    assert len(function_completed_logs) == 1

    assert function_started_logs[0].run_date_utc
    assert trapi_request_logs[0].model_version == "gpt-4o-2025-04-01"
    assert trapi_request_logs[0].prompt_hash
    assert trapi_response_logs[0].token_count == 123
    assert trapi_response_logs[0].latency_ms >= 0
    assert trapi_response_logs[0].player_count == 24
    assert blob_write_logs[0].blob_uri == "https://example/blob"
    assert function_completed_logs[0].player_count == 24
    assert function_completed_logs[0].blob_uri == "https://example/blob"
    assert function_completed_logs[0].write_conflict is False

    add_args = mock_counter.add.call_args.args
    add_kwargs = mock_counter.add.call_args.kwargs
    assert add_args[0] == 24
    assert "run_date_utc" in add_args[1]
    assert add_kwargs == {}


def test_configure_telemetry_exporter_uses_app_insights_connection_string(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_function_app()
    spy = Mock()
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key")
    monkeypatch.setattr(module, "_configure_azure_monitor", spy)

    module._configure_telemetry_exporter()

    spy.assert_called_once_with(connection_string="InstrumentationKey=test-key")


def test_configure_telemetry_exporter_skips_when_connection_string_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = _reload_function_app()
    spy = Mock()
    monkeypatch.delenv("APPLICATIONINSIGHTS_CONNECTION_STRING", raising=False)
    monkeypatch.setattr(module, "_configure_azure_monitor", spy)

    module._configure_telemetry_exporter()

    spy.assert_not_called()


def test_configure_telemetry_exporter_logs_warning_on_configure_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    module = _reload_function_app()
    monkeypatch.setenv("APPLICATIONINSIGHTS_CONNECTION_STRING", "InstrumentationKey=test-key")

    def _raise(**kwargs: object) -> None:
        del kwargs
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_configure_azure_monitor", _raise)
    caplog.set_level(logging.WARNING)

    module._configure_telemetry_exporter()

    assert any(record.message == "telemetry_exporter_configuration_failed" for record in caplog.records)


def test_function_logs_write_conflict_when_blob_exists(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    module = _reload_function_app()
    monkeypatch.setattr(module, "_PLAYER_COUNT_RETURNED", Mock())

    class _Writer:
        def write(self, payload: dict[str, object], run_date_utc: str) -> None:
            assert payload
            assert run_date_utc
            return None

        def write_failed(self, payload: object, run_date_utc: str) -> None:
            raise AssertionError("write_failed should not be called in success path")

    monkeypatch.setattr(module, "BlobWriter", _Writer)
    monkeypatch.setattr(
        module,
        "fetch_1985_yankees_roster",
        lambda: {"players": [{"name": f"Player {i}", "position": "P", "jersey_number": i} for i in range(1, 25)]},
    )

    caplog.set_level(logging.INFO)
    module.get_and_store_yankees_roster(timer=object())

    completed_logs = [record for record in caplog.records if record.message == "function_completed"]
    assert completed_logs
    assert completed_logs[-1].write_conflict is True


def test_timer_trigger_configuration_matches_spec() -> None:
    source = (Path(__file__).resolve().parents[1] / "function_app.py").read_text(encoding="utf-8")
    assert 'schedule="0 0 2 * * *"' in source
    assert "use_monitor=True" in source


def test_function_app_import_succeeds_with_mocked_env_vars() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "TRAPI_ENDPOINT": "https://example.invalid",
            "TRAPI_DEPLOYMENT_NAME": "deployment",
            "TRAPI_AUTH_SCOPE": "api://trapi/.default",
            "TRAPI_API_VERSION": "2025-04-01-preview",
            "ROSTER_STORAGE_ACCOUNT_NAME": "acct",
            "ROSTER_CONTAINER_NAME": "yankees-roster",
        }
    )

    completed = subprocess.run(
        [sys.executable, "-c", "import function_app"],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
