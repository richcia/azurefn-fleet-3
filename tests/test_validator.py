from src.validator import ValidationErrorKind, validate_roster_response


def _build_players(count: int) -> list[dict[str, object]]:
    return [
        {
            "name": f"Player {i}",
            "position": "P",
            "jersey_number": i,
        }
        for i in range(1, count + 1)
    ]


def test_validate_roster_response_valid_payload_in_range() -> None:
    payload = {"players": _build_players(24)}

    result = validate_roster_response(payload)

    assert result.is_valid is True
    assert result.players == payload["players"]
    assert result.error is None


def test_validate_roster_response_schema_invalid_when_players_missing() -> None:
    result = validate_roster_response({})

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.SCHEMA_INVALID


def test_validate_roster_response_schema_invalid_when_player_shape_wrong() -> None:
    payload = {"players": [{"name": "Don Mattingly", "position": "1B", "jersey_number": "23"}]}

    result = validate_roster_response(payload)

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.SCHEMA_INVALID


def test_validate_roster_response_player_count_low() -> None:
    payload = {"players": _build_players(23)}

    result = validate_roster_response(payload)

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.PLAYER_COUNT_LOW


def test_validate_roster_response_player_count_high() -> None:
    payload = {"players": _build_players(29)}

    result = validate_roster_response(payload)

    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.PLAYER_COUNT_HIGH
