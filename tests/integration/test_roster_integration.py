from __future__ import annotations

import json
import os
import subprocess
import time
from datetime import datetime, timezone

import pytest
import requests
from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


_RUN_INTEGRATION_TESTS = os.getenv("RUN_INTEGRATION_TESTS", "").strip().lower() in {"1", "true", "yes", "on"}
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        not _RUN_INTEGRATION_TESTS,
        reason="Set RUN_INTEGRATION_TESTS=true to run integration tests",
    ),
]


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _az_cli(*args: str) -> str:
    completed = subprocess.run(["az", *args], check=True, text=True, capture_output=True)
    return completed.stdout.strip()


def _invoke_roster_function() -> None:
    function_name = os.getenv("AZURE_FUNCTION_NAME", "GetAndStoreYankeesRoster")
    function_app_name = os.getenv("AZURE_FUNCTIONAPP_NAME", "").strip()

    if function_app_name:
        resource_group = os.getenv("AZURE_RESOURCE_GROUP", "").strip() or _az_cli(
            "functionapp",
            "show",
            "--name",
            function_app_name,
            "--query",
            "resourceGroup",
            "-o",
            "tsv",
        )
        host_key = os.getenv("AZURE_FUNCTIONAPP_MASTER_KEY", "").strip() or _az_cli(
            "functionapp",
            "keys",
            "list",
            "--name",
            function_app_name,
            "--resource-group",
            resource_group,
            "--query",
            "masterKey",
            "-o",
            "tsv",
        )
        invoke_url = f"https://{function_app_name}.azurewebsites.net/admin/functions/{function_name}"
        response = requests.post(invoke_url, headers={"x-functions-key": host_key}, json={}, timeout=30)
        response.raise_for_status()
        return

    function_host_url = os.getenv("INTEGRATION_FUNCTION_HOST_URL", "http://127.0.0.1:7071").rstrip("/")
    host_key = os.getenv("FUNCTIONS_MASTER_KEY", "").strip() or os.getenv("AZURE_FUNCTIONAPP_MASTER_KEY", "").strip()
    headers = {"x-functions-key": host_key} if host_key else {}
    invoke_url = f"{function_host_url}/admin/functions/{function_name}"
    response = requests.post(invoke_url, headers=headers, json={}, timeout=30)
    response.raise_for_status()


def test_roster_blob_contains_known_players() -> None:
    storage_account_name = (
        os.getenv("DATA_STORAGE_ACCOUNT_NAME", "").strip() or os.getenv("ROSTER_STORAGE_ACCOUNT_NAME", "").strip()
    )
    assert storage_account_name, "DATA_STORAGE_ACCOUNT_NAME or ROSTER_STORAGE_ACCOUNT_NAME must be set"

    container_name = os.getenv("ROSTER_CONTAINER_NAME", "yankees-roster").strip()
    assert container_name == "yankees-roster", "QA-02 requires blob path in container 'yankees-roster'"

    blob_service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    run_date_before_invoke_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    blob_client_before_invoke = blob_service_client.get_blob_client(
        container=container_name,
        blob=f"{run_date_before_invoke_utc}.json",
    )

    allow_cleanup = _bool_env("INTEGRATION_ALLOW_DESTRUCTIVE_BLOB_CLEANUP")
    if allow_cleanup and _bool_env("INTEGRATION_DELETE_EXISTING_BLOBS_BEFORE_INVOKE"):
        try:
            blob_client_before_invoke.delete_blob()
        except ResourceNotFoundError:
            pass

    invoke_started_at = datetime.now(timezone.utc)
    _invoke_roster_function()
    run_date_after_invoke_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    candidate_blob_clients = [
        blob_service_client.get_blob_client(container=container_name, blob=f"{run_date_utc}.json")
        for run_date_utc in dict.fromkeys([run_date_before_invoke_utc, run_date_after_invoke_utc])
    ]

    timeout_seconds = int(os.getenv("INTEGRATION_BLOB_TIMEOUT_SECONDS", "300"))
    poll_interval_seconds = int(os.getenv("INTEGRATION_BLOB_POLL_INTERVAL_SECONDS", "10"))
    deadline = time.time() + timeout_seconds

    payload: dict[str, object] | None = None
    selected_blob_client = None
    while time.time() < deadline:
        for blob_client in candidate_blob_clients:
            if not blob_client.exists():
                continue
            blob_properties = blob_client.get_blob_properties()
            if blob_properties.last_modified < invoke_started_at:
                continue
            payload = json.loads(blob_client.download_blob().readall())
            selected_blob_client = blob_client
            break
        if payload is not None:
            break
        time.sleep(poll_interval_seconds)

    assert payload is not None, (
        f"Expected blob to exist at {container_name}/{{today_utc}}.json within {timeout_seconds}s after function trigger"
    )

    players = payload.get("players") if isinstance(payload, dict) else None
    assert isinstance(players, list), "Expected blob JSON to contain a 'players' list"

    lower_names = [
        str(player.get("name", "")).lower() for player in players if isinstance(player, dict)
    ]
    for known_player in ("mattingly", "winfield", "henderson"):
        assert any(known_player in name for name in lower_names), (
            f"Expected players list to include a name containing '{known_player}'"
        )

    if allow_cleanup and _bool_env("INTEGRATION_DELETE_CREATED_BLOB"):
        try:
            assert selected_blob_client is not None
            selected_blob_client.delete_blob()
        except ResourceNotFoundError:
            pass
