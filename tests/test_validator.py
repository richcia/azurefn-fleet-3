"""Unit tests for src/validator.py — covers all acceptance criteria for APP-02."""
import pytest

from src.validator import (
    ValidationErrorKind,
    ValidationResult,
    validate_roster_response,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_player(
    name: str = "Don Mattingly",
    position: str = "1B",
    jersey_number: int = 23,
) -> dict:
    return {"name": name, "position": position, "jersey_number": jersey_number}


def _make_roster(count: int) -> dict:
    return {
        "players": [
            _make_player(name=f"Player {i}", jersey_number=i)
            for i in range(count)
        ]
    }


# ---------------------------------------------------------------------------
# Happy-path: valid 24-player payload
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_valid_24_player_payload():
    payload = _make_roster(24)
    result = validate_roster_response(payload)
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.players == payload["players"]
    assert result.error is None


@pytest.mark.unit
def test_valid_28_player_payload():
    payload = _make_roster(28)
    result = validate_roster_response(payload)
    assert result.is_valid is True
    assert len(result.players) == 28


# ---------------------------------------------------------------------------
# Missing 'players' key
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_missing_players_key_empty_dict():
    result = validate_roster_response({})
    assert result.is_valid is False
    assert result.error is not None
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


@pytest.mark.unit
def test_missing_players_key_wrong_key():
    result = validate_roster_response({"roster": []})
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


# ---------------------------------------------------------------------------
# Invalid player schema — missing jersey_number
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_player_missing_jersey_number():
    payload = {"players": [{"name": "x", "position": "y"}]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


@pytest.mark.unit
def test_player_missing_name():
    payload = {"players": [{"position": "1B", "jersey_number": 23}]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


@pytest.mark.unit
def test_player_missing_position():
    payload = {"players": [{"name": "Bob", "jersey_number": 5}]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


@pytest.mark.unit
def test_player_wrong_type_jersey_number():
    payload = {"players": [{"name": "Bob", "position": "RF", "jersey_number": "23"}]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


@pytest.mark.unit
def test_player_wrong_type_name():
    payload = {"players": [{"name": 99, "position": "RF", "jersey_number": 23}]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


# ---------------------------------------------------------------------------
# Player count out of range
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_too_few_players_23():
    result = validate_roster_response(_make_roster(23))
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.PLAYER_COUNT_OUT_OF_RANGE


@pytest.mark.unit
def test_too_many_players_29():
    result = validate_roster_response(_make_roster(29))
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.PLAYER_COUNT_OUT_OF_RANGE


@pytest.mark.unit
def test_zero_players():
    result = validate_roster_response({"players": []})
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.PLAYER_COUNT_OUT_OF_RANGE


# ---------------------------------------------------------------------------
# players value is not a list
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_players_not_a_list():
    result = validate_roster_response({"players": "not-a-list"})
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.PLAYERS_NOT_A_LIST


@pytest.mark.unit
def test_players_is_dict():
    result = validate_roster_response({"players": {}})
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.PLAYERS_NOT_A_LIST


# ---------------------------------------------------------------------------
# ValidationResult.players is populated only for valid payloads
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_players_populated_on_valid():
    payload = _make_roster(24)
    result = validate_roster_response(payload)
    assert result.players is not None
    assert len(result.players) == 24


@pytest.mark.unit
def test_players_none_on_invalid():
    result = validate_roster_response({})
    assert not result.players


# ---------------------------------------------------------------------------
# Graceful handling of None, empty dict, and malformed inputs
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_none_payload():
    result = validate_roster_response(None)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


@pytest.mark.unit
def test_list_payload():
    result = validate_roster_response([])
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


@pytest.mark.unit
def test_string_payload():
    result = validate_roster_response("not-a-dict")
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


@pytest.mark.unit
def test_integer_payload():
    result = validate_roster_response(42)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.MISSING_PLAYERS_KEY


@pytest.mark.unit
def test_player_entry_not_a_dict():
    payload = {"players": ["not-a-dict-player"]}
    result = validate_roster_response(payload)
    assert result.is_valid is False
    assert result.error.kind == ValidationErrorKind.INVALID_PLAYER_SCHEMA


# ---------------------------------------------------------------------------
# Import check (validates the public API surface)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_import_public_api():
    from src.validator import validate_roster_response as vr, ValidationErrorKind as vek
    assert callable(vr)
    assert issubclass(vek, str)
