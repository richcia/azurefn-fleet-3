import json
import os
from pathlib import Path

import pytest
import requests


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "get_1985_yankees.txt"


def _load_prompt_sections():
    content = PROMPT_PATH.read_text(encoding="utf-8")
    system_marker = "\nsystem:\n"
    user_marker = "\n\nuser:\n"
    assert system_marker in content, "Prompt must include a system section."
    assert user_marker in content, "Prompt must include a user section."

    before_system, system_and_after = content.split(system_marker, 1)
    system_content, user_content = system_and_after.split(user_marker, 1)
    return before_system, system_content.strip(), user_content.strip()


def test_prompt_file_exists():
    assert PROMPT_PATH.exists()


def test_prompt_contains_pinned_model_and_schema_requirements():
    before_system, system_content, user_content = _load_prompt_sections()
    content = f"{before_system}\n{system_content}\n{user_content}"

    assert "model: gpt-4o-2024-05-13" in before_system
    assert "valid JSON" in system_content
    assert "no markdown" in system_content
    assert "no extra keys" in system_content
    for token in ['"players"', '"name"', '"position"', '"jersey_number"', "jersey_number must be an integer."]:
        assert token in user_content
    for player in ["Don Mattingly", "Dave Winfield", "Rickey Henderson"]:
        assert player in user_content


def test_manual_trapi_validation_contains_known_players():
    if os.environ.get("RUN_MANUAL_TRAPI_TESTS", "").lower() != "true":
        pytest.skip("Set RUN_MANUAL_TRAPI_TESTS=true to run manual TRAPI validation.")

    endpoint = os.environ.get("TRAPI_ENDPOINT")
    bearer_token = os.environ.get("TRAPI_BEARER_TOKEN")
    if not endpoint or not bearer_token:
        pytest.skip("Set TRAPI_ENDPOINT and TRAPI_BEARER_TOKEN to run manual TRAPI validation.")

    _, system_content, user_content = _load_prompt_sections()
    response = requests.post(
        endpoint,
        headers={"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"},
        json={
            "model": "gpt-4o-2024-05-13",
            "messages": [
                {
                    "role": "system",
                    "content": system_content,
                },
                {
                    "role": "user",
                    "content": user_content,
                },
            ],
            "temperature": 0,
        },
        timeout=45,
    )
    response.raise_for_status()
    body = response.json()
    assert "choices" in body and isinstance(body["choices"], list) and body["choices"], "TRAPI response missing choices."
    first_choice = body["choices"][0]
    assert "message" in first_choice and isinstance(first_choice["message"], dict), "TRAPI response missing message."
    assert "content" in first_choice["message"] and isinstance(first_choice["message"]["content"], str), "TRAPI response missing message content."

    content = first_choice["message"]["content"]
    payload = json.loads(content)
    assert isinstance(payload, dict) and "players" in payload, "TRAPI content must be a JSON object with players."
    players = payload["players"]
    assert isinstance(players, list)
    assert players
    for player in players:
        assert set(player.keys()) == {"name", "position", "jersey_number"}
        assert isinstance(player["name"], str)
        assert isinstance(player["position"], str)
        assert isinstance(player["jersey_number"], int)
    names = {player["name"] for player in players}
    assert {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}.issubset(names)
