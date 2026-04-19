import json
import os
import subprocess
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.getenv("RUN_INTEGRATION_TESTS", "false").lower() != "true",
        reason="Set RUN_INTEGRATION_TESTS=true to run integration tests.",
    ),
]


def _env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise AssertionError(f"Missing required environment variable: {name}")
    return value


def _az(*args: str) -> str:
    completed = subprocess.run(
        ["az", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _get_resource_group(app_name: str) -> str:
    return _az(
        "resource",
        "list",
        "--name",
        app_name,
        "--resource-type",
        "Microsoft.Web/sites",
        "--query",
        "[0].resourceGroup",
        "-o",
        "tsv",
    )


def _slot_args(slot_name: str) -> list[str]:
    return ["--slot", slot_name] if slot_name and slot_name != "production" else []


def _invoke_function_admin_api(
    *,
    app_name: str,
    resource_group: str,
    slot_name: str,
    function_name: str,
) -> None:
    slot_args = _slot_args(slot_name)
    host_name = _az(
        "functionapp",
        "show",
        "--name",
        app_name,
        "--resource-group",
        resource_group,
        *slot_args,
        "--query",
        "defaultHostName",
        "-o",
        "tsv",
    )
    master_key = _az(
        "functionapp",
        "keys",
        "list",
        "--name",
        app_name,
        "--resource-group",
        resource_group,
        *slot_args,
        "--query",
        "masterKey",
        "-o",
        "tsv",
    )
    response = requests.post(
        f"https://{host_name}/admin/functions/{function_name}",
        headers={
            "Content-Type": "application/json",
            "x-functions-key": master_key,
        },
        data="{}",
        timeout=30,
    )
    assert response.status_code in {200, 202, 204}, (
        f"Function invocation failed with HTTP {response.status_code}: {response.text}"
    )


def _candidate_blob_names() -> list[str]:
    now = datetime.now(timezone.utc)
    return [
        f"{now.strftime('%Y-%m-%d')}.json",
        f"{(now + timedelta(days=1)).strftime('%Y-%m-%d')}.json",
    ]


def test_staging_output_blob_contains_known_players():
    app_name = _env("AZURE_FUNCTIONAPP_NAME")
    slot_name = os.getenv("AZURE_FUNCTIONAPP_SLOT", "staging").strip() or "staging"
    function_name = os.getenv("SMOKE_TEST_FUNCTION_NAME", "GetAndStoreYankeesRoster").strip()
    storage_account_name = _env("DATA_STORAGE_ACCOUNT_NAME")
    resource_group = _get_resource_group(app_name)
    assert resource_group, f"Unable to resolve resource group for function app '{app_name}'"

    service_client = BlobServiceClient(
        account_url=f"https://{storage_account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    container_client = service_client.get_container_client("yankees-roster")

    candidate_blob_names = _candidate_blob_names()
    existing_before = {
        blob_name
        for blob_name in candidate_blob_names
        if container_client.get_blob_client(blob_name).exists()
    }

    found_blob_name = None
    created_by_test = False
    try:
        _invoke_function_admin_api(
            app_name=app_name,
            resource_group=resource_group,
            slot_name=slot_name,
            function_name=function_name,
        )

        timeout_seconds = int(os.getenv("INTEGRATION_BLOB_TIMEOUT_SECONDS", "240"))
        poll_interval_seconds = int(os.getenv("INTEGRATION_BLOB_POLL_INTERVAL_SECONDS", "10"))
        deadline = time.time() + timeout_seconds

        payload = None
        while time.time() < deadline:
            for blob_name in _candidate_blob_names():
                blob_client = container_client.get_blob_client(blob_name)
                if not blob_client.exists():
                    continue
                found_blob_name = blob_name
                created_by_test = blob_name not in existing_before
                payload = json.loads(blob_client.download_blob().readall().decode("utf-8"))
                break
            if payload is not None:
                break
            time.sleep(poll_interval_seconds)

        assert payload is not None, (
            f"Timed out after {timeout_seconds}s waiting for output blob in yankees-roster/"
        )

        players = payload.get("players")
        assert isinstance(players, list), "Output blob payload must contain a players list"
        names = {player.get("name") for player in players if isinstance(player, dict)}
        assert "Don Mattingly" in names
        assert "Dave Winfield" in names
        assert "Rickey Henderson" in names
        assert 24 <= len(players) <= 28, f"Unexpected player count: {len(players)}"
    finally:
        if found_blob_name and created_by_test and container_client.get_blob_client(found_blob_name).exists():
            container_client.get_blob_client(found_blob_name).delete_blob()
