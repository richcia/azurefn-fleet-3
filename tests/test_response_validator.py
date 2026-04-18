import json
from pathlib import Path

import pytest

from response_validator import validate_response


@pytest.fixture
def valid_response_payload() -> dict:
    fixture_path = Path(__file__).parent / "fixtures" / "valid_response_25.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_validate_response_rejects_missing_players_key() -> None:
    is_valid, data, error = validate_response({"team": "Yankees"})

    assert not is_valid
    assert data == {}
    assert "players" in error


@pytest.mark.parametrize("missing_field", ["name", "position", "jersey_number"])
def test_validate_response_rejects_missing_required_player_fields(
    valid_response_payload: dict, missing_field: str
) -> None:
    del valid_response_payload["players"][0][missing_field]

    is_valid, data, error = validate_response(valid_response_payload)

    assert not is_valid
    assert data == {}
    assert missing_field in error


def test_validate_response_rejects_non_integer_jersey_number(
    valid_response_payload: dict,
) -> None:
    valid_response_payload["players"][0]["jersey_number"] = "23"

    is_valid, data, error = validate_response(valid_response_payload)

    assert not is_valid
    assert data == {}
    assert "non-integer" in error


@pytest.mark.parametrize("player_count", [23, 29])
def test_validate_response_rejects_out_of_range_player_count(player_count: int) -> None:
    payload = {
        "players": [
            {"name": f"Player {index}", "position": "P", "jersey_number": index}
            for index in range(1, player_count + 1)
        ]
    }

    is_valid, data, error = validate_response(payload)

    assert not is_valid
    assert data == {}
    assert "out of range" in error


def test_validate_response_accepts_valid_response_payload(valid_response_payload: dict) -> None:
    is_valid, data, error = validate_response(valid_response_payload)

    assert is_valid
    assert error == ""
    assert len(data["players"]) == 25
