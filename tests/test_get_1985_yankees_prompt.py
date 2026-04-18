import json
import os
from pathlib import Path

import pytest
import requests


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "get_1985_yankees.txt"


def test_prompt_file_exists():
    assert PROMPT_PATH.exists()


def test_prompt_contains_pinned_model_and_schema_requirements():
    content = PROMPT_PATH.read_text(encoding="utf-8")

    assert "model: gpt-4o-2024-05-13" in content
    assert '"players"' in content
    assert '"name"' in content
    assert '"position"' in content
    assert '"jersey_number"' in content
    assert "jersey_number must be an integer." in content
    assert "Don Mattingly" in content
    assert "Dave Winfield" in content
    assert "Rickey Henderson" in content


def test_manual_trapi_validation_contains_known_players():
    if os.environ.get("RUN_MANUAL_TRAPI_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_MANUAL_TRAPI_TESTS=true to run manual TRAPI validation.")

    endpoint = os.environ.get("TRAPI_ENDPOINT")
    bearer_token = os.environ.get("TRAPI_BEARER_TOKEN")
    if not endpoint or not bearer_token:
        pytest.skip("Set TRAPI_ENDPOINT and TRAPI_BEARER_TOKEN to run manual TRAPI validation.")

    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o-2024-05-13",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a baseball data assistant. Return only valid JSON with no markdown and no extra keys.",
                },
                {
                    "role": "user",
                    "content": "Return the 1985 New York Yankees active roster as JSON with players having name, position, jersey_number.",
                },
            ],
            "temperature": 0,
        },
        timeout=45,
    )
    response.raise_for_status()
    body = response.json()
    content = body["choices"][0]["message"]["content"]
    players = json.loads(content)["players"]
    assert isinstance(players, list)
    assert players
    for player in players:
        assert set(player.keys()) == {"name", "position", "jersey_number"}
        assert isinstance(player["name"], str)
        assert isinstance(player["position"], str)
        assert isinstance(player["jersey_number"], int)
    names = {player["name"] for player in players}
    assert {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}.issubset(names)
