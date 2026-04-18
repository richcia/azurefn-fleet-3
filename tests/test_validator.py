import pytest

import validator


def _build_valid_players(count=24):
    players = [
        {"name": "Don Mattingly", "position": "1B", "jersey_number": 23},
        {"name": "Dave Winfield", "position": "RF", "jersey_number": 31},
        {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
    ]

    for index in range(3, count):
        players.append(
            {
                "name": f"Player {index}",
                "position": "P",
                "jersey_number": index,
            }
        )
    return players


def test_validator_rejects_missing_players_array():
    result = validator.validate_response({"roster": []})

    assert not result.is_valid
    assert result.player_count == 0
    assert "players" in result.error_message


@pytest.mark.parametrize("missing_field", ["name", "position", "jersey_number"])
def test_validator_rejects_players_missing_required_fields(missing_field):
    players = _build_valid_players()
    del players[0][missing_field]

    result = validator.validate_response({"players": players})

    assert not result.is_valid
    assert result.player_count == 24
    assert missing_field in result.error_message


@pytest.mark.parametrize("count", [23, 29])
def test_validator_rejects_player_count_outside_range(count):
    payload = {"players": _build_valid_players(count)}

    result = validator.validate_response(payload)

    assert not result.is_valid
    assert result.player_count == count
    assert "between 24 and 28" in result.error_message


def test_validator_accepts_valid_response_with_known_players():
    payload = {"players": _build_valid_players(24)}

    result = validator.validate_response(payload)

    assert result.is_valid
    assert result.player_count == 24
    assert result.error_message == ""


def test_validator_returns_validation_result_instead_of_raising():
    result = validator.validate_response({"players": []})

    assert isinstance(result, validator.ValidationResult)
    assert not result.is_valid
