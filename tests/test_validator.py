import importlib
import sys
import types

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


def test_validate_roster_response_valid_payload_upper_boundary() -> None:
    payload = {"players": _build_players(28)}

    result = validate_roster_response(payload)

    assert result.is_valid is True
    assert result.players == payload["players"]
    assert result.error is None


def test_validate_roster_response_accepts_known_1985_yankees_players() -> None:
    payload = {
        "players": [
            {"name": "Don Mattingly", "position": "1B", "jersey_number": 23},
            {"name": "Dave Winfield", "position": "RF", "jersey_number": 31},
            {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
            *_build_players(21),
        ]
    }

    result = validate_roster_response(payload)

    assert result.is_valid is True
    assert result.players is not None
    player_names = {player["name"] for player in result.players}
    assert {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}.issubset(player_names)
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


def test_trapi_client_import_contract_uses_validator_module() -> None:
    module = importlib.import_module("trapi_client")

    assert module.validate_roster_response is validate_roster_response


def test_function_app_import_contract_uses_validator_module() -> None:
    stub_blob_writer = types.ModuleType("src.blob_writer")

    class BlobWriter:  # noqa: D401
        def __init__(self) -> None:
            pass

    stub_blob_writer.BlobWriter = BlobWriter
    sys.modules["src.blob_writer"] = stub_blob_writer

    try:
        module = importlib.import_module("function_app")
        assert module.validate_roster_response is validate_roster_response
    finally:
        sys.modules.pop("src.blob_writer", None)
        sys.modules.pop("function_app", None)
