from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationErrorKind(str, Enum):
    MISSING_PLAYERS_KEY = "MISSING_PLAYERS_KEY"
    PLAYERS_NOT_A_LIST = "PLAYERS_NOT_A_LIST"
    INVALID_PLAYER_SCHEMA = "INVALID_PLAYER_SCHEMA"
    PLAYER_COUNT_OUT_OF_RANGE = "PLAYER_COUNT_OUT_OF_RANGE"


_PLAYER_COUNT_MIN = 24
_PLAYER_COUNT_MAX = 28

_REQUIRED_PLAYER_FIELDS: dict[str, type] = {
    "name": str,
    "position": str,
    "jersey_number": int,
}


@dataclass
class ValidationError:
    kind: ValidationErrorKind
    message: str


@dataclass
class ValidationResult:
    is_valid: bool
    players: list[dict[str, Any]] | None = field(default=None)
    error: ValidationError | None = field(default=None)


def validate_roster_response(payload: Any) -> ValidationResult:
    """Validate a roster response payload.

    Returns a ValidationResult with is_valid=True and a populated players list
    when the payload is valid, or is_valid=False with a ValidationError
    describing the first failure found.
    """
    if not isinstance(payload, dict):
        return ValidationResult(
            is_valid=False,
            error=ValidationError(
                kind=ValidationErrorKind.MISSING_PLAYERS_KEY,
                message="Payload is not a dict or is missing the 'players' key.",
            ),
        )

    if "players" not in payload:
        return ValidationResult(
            is_valid=False,
            error=ValidationError(
                kind=ValidationErrorKind.MISSING_PLAYERS_KEY,
                message="Payload is missing the 'players' key.",
            ),
        )

    players = payload["players"]

    if not isinstance(players, list):
        return ValidationResult(
            is_valid=False,
            error=ValidationError(
                kind=ValidationErrorKind.PLAYERS_NOT_A_LIST,
                message="'players' value is not a list.",
            ),
        )

    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return ValidationResult(
                is_valid=False,
                error=ValidationError(
                    kind=ValidationErrorKind.INVALID_PLAYER_SCHEMA,
                    message=f"Player at index {index} is not a dict.",
                ),
            )
        for field_name, expected_type in _REQUIRED_PLAYER_FIELDS.items():
            if field_name not in player:
                return ValidationResult(
                    is_valid=False,
                    error=ValidationError(
                        kind=ValidationErrorKind.INVALID_PLAYER_SCHEMA,
                        message=(
                            f"Player at index {index} is missing required field '{field_name}'."
                        ),
                    ),
                )
            if not isinstance(player[field_name], expected_type):
                return ValidationResult(
                    is_valid=False,
                    error=ValidationError(
                        kind=ValidationErrorKind.INVALID_PLAYER_SCHEMA,
                        message=(
                            f"Player at index {index} field '{field_name}' must be "
                            f"{expected_type.__name__}, got {type(player[field_name]).__name__}."
                        ),
                    ),
                )

    player_count = len(players)
    if player_count < _PLAYER_COUNT_MIN or player_count > _PLAYER_COUNT_MAX:
        return ValidationResult(
            is_valid=False,
            error=ValidationError(
                kind=ValidationErrorKind.PLAYER_COUNT_OUT_OF_RANGE,
                message=(
                    f"Player count {player_count} is out of the expected range "
                    f"[{_PLAYER_COUNT_MIN}, {_PLAYER_COUNT_MAX}]."
                ),
            ),
        )

    return ValidationResult(is_valid=True, players=players)
