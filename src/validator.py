from dataclasses import dataclass
from enum import Enum
from typing import Any


class ValidationErrorKind(str, Enum):
    SCHEMA_FAILURE = "schema_failure"
    COUNT_FAILURE = "count_failure"


@dataclass(frozen=True)
class ValidationError:
    kind: ValidationErrorKind
    message: str


@dataclass(frozen=True)
class ValidationResult:
    players: list[dict[str, Any]] | None = None
    error: ValidationError | None = None

    @property
    def is_valid(self) -> bool:
        return self.error is None


_REQUIRED_PLAYER_FIELDS = ("name", "position", "jersey_number")


def validate_roster_response(
    response: dict[str, Any],
    min_players: int = 24,
    max_players: int = 28,
) -> ValidationResult:
    players = response.get("players")
    if not isinstance(players, list):
        return ValidationResult(
            error=ValidationError(
                kind=ValidationErrorKind.SCHEMA_FAILURE,
                message="players must be a list",
            )
        )

    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return ValidationResult(
                error=ValidationError(
                    kind=ValidationErrorKind.SCHEMA_FAILURE,
                    message=f"players[{index}] must be an object",
                )
            )

        for field in _REQUIRED_PLAYER_FIELDS:
            if field not in player:
                return ValidationResult(
                    error=ValidationError(
                        kind=ValidationErrorKind.SCHEMA_FAILURE,
                        message=f"players[{index}] missing required field: {field}",
                    )
                )

        if not isinstance(player["name"], str) or not player["name"].strip():
            return ValidationResult(
                error=ValidationError(
                    kind=ValidationErrorKind.SCHEMA_FAILURE,
                    message=f"players[{index}].name must be a non-empty string",
                )
            )

        if not isinstance(player["position"], str) or not player["position"].strip():
            return ValidationResult(
                error=ValidationError(
                    kind=ValidationErrorKind.SCHEMA_FAILURE,
                    message=f"players[{index}].position must be a non-empty string",
                )
            )

        jersey_number = player["jersey_number"]
        if not isinstance(jersey_number, int) or isinstance(jersey_number, bool):
            return ValidationResult(
                error=ValidationError(
                    kind=ValidationErrorKind.SCHEMA_FAILURE,
                    message=f"players[{index}].jersey_number must be an integer",
                )
            )

    player_count = len(players)
    if player_count < min_players or player_count > max_players:
        return ValidationResult(
            error=ValidationError(
                kind=ValidationErrorKind.COUNT_FAILURE,
                message=f"player count {player_count} is outside {min_players}-{max_players}",
            )
        )

    return ValidationResult(players=players)
