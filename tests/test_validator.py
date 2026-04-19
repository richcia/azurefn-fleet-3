from src.validator import ValidationErrorKind, validate_roster_response


def _player(i: int) -> dict[str, object]:
    return {
        "name": f"Player {i}",
        "position": "P",
        "jersey_number": i,
    }


def _players(count: int) -> list[dict[str, object]]:
    return [_player(i) for i in range(1, count + 1)]


def test_validator_accepts_valid_response():
    response = {"players": _players(24)}

    result = validate_roster_response(response)

    assert result.is_valid is True
    assert result.error is None
    assert result.players == response["players"]


def test_validator_rejects_schema_violation_missing_required_field():
    players = _players(24)
    players[0].pop("jersey_number")

    result = validate_roster_response({"players": players})

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.SCHEMA_FAILURE


def test_validator_rejects_non_object_response():
    result = validate_roster_response(None)

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.SCHEMA_FAILURE


def test_validator_rejects_count_too_low():
    result = validate_roster_response({"players": _players(23)})

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.COUNT_FAILURE


def test_validator_rejects_count_too_high():
    result = validate_roster_response({"players": _players(29)})

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.COUNT_FAILURE


def test_validator_passes_with_known_players_present():
    players = [
        {"name": "Don Mattingly", "position": "1B", "jersey_number": 23},
        {"name": "Dave Winfield", "position": "RF", "jersey_number": 31},
        {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
        *_players(21),
    ]

    result = validate_roster_response({"players": players})

    assert result.is_valid is True
    assert result.error is None
