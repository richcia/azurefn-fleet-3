import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient

import function_app
from blob_writer import CONTAINER_NAME
from validator import validate


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@pytest.mark.integration
def test_staging_trapi_blob_contains_known_players():
    if os.environ.get("RUN_INTEGRATION_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_INTEGRATION_TESTS=true to run integration tests.")

    _get_required_env("TRAPI_ENDPOINT")
    account_name = _get_required_env("DATA_STORAGE_ACCOUNT_NAME")

    run_date_utc = datetime.now(timezone.utc).date().isoformat()
    function_app.get_and_store_yankees_roster(SimpleNamespace(past_due=False))

    blob_name = f"{run_date_utc}.json"
    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=DefaultAzureCredential(),
    )
    blob_client = blob_service_client.get_blob_client(container=CONTAINER_NAME, blob=blob_name)
    assert blob_client.exists(), f"Missing blob {CONTAINER_NAME}/{blob_name}."
    payload = json.loads(blob_client.download_blob().readall())

    validation_result = validate(payload)
    assert validation_result.is_valid, validation_result.error_message
    names = {player["name"] for player in payload["players"]}
    assert {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}.issubset(names)
