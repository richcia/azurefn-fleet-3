from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationErrorKind(str, Enum):
    SCHEMA_INVALID = "SCHEMA_INVALID"
    PLAYER_COUNT_LOW = "PLAYER_COUNT_LOW"
    PLAYER_COUNT_HIGH = "PLAYER_COUNT_HIGH"


@dataclass(frozen=True)
class ValidationError:
    kind: ValidationErrorKind
    message: str


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    players: list[dict[str, Any]] | None = None
    error: ValidationError | None = None


def _schema_invalid(message: str) -> ValidationResult:
    return ValidationResult(
        is_valid=False,
        players=None,
        error=ValidationError(kind=ValidationErrorKind.SCHEMA_INVALID, message=message),
    )


def validate_roster_response(payload: dict[str, Any]) -> ValidationResult:
    if not isinstance(payload, dict):
        return _schema_invalid("Payload must be an object")

    players = payload.get("players")
    if not isinstance(players, list):
        return _schema_invalid("Field 'players' must be a list")

    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return _schema_invalid(f"players[{index}] must be an object")

        if "name" not in player or "position" not in player or "jersey_number" not in player:
            return _schema_invalid(f"players[{index}] is missing required fields")

        if not isinstance(player["name"], str):
            return _schema_invalid(f"players[{index}].name must be a string")

        if not isinstance(player["position"], str):
            return _schema_invalid(f"players[{index}].position must be a string")

        jersey_number = player["jersey_number"]
        if isinstance(jersey_number, bool) or not isinstance(jersey_number, int):
            return _schema_invalid(f"players[{index}].jersey_number must be an integer")

    player_count = len(players)
    if player_count < 24:
        return ValidationResult(
            is_valid=False,
            players=players,
            error=ValidationError(
                kind=ValidationErrorKind.PLAYER_COUNT_LOW,
                message=f"Expected at least 24 players, got {player_count}",
            ),
        )

    if player_count > 28:
        return ValidationResult(
            is_valid=False,
            players=players,
            error=ValidationError(
                kind=ValidationErrorKind.PLAYER_COUNT_HIGH,
                message=f"Expected at most 28 players, got {player_count}",
            ),
        )

    return ValidationResult(is_valid=True, players=players, error=None)
