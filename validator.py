from dataclasses import dataclass
from typing import Any

MIN_PLAYER_COUNT = 24
MAX_PLAYER_COUNT = 28
REQUIRED_PLAYER_FIELDS = ("name", "position", "jersey_number")
REQUIRED_PLAYER_NAMES = {"Don Mattingly", "Dave Winfield", "Rickey Henderson"}


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    player_count: int
    error_message: str = ""


def validate_response(response: Any) -> ValidationResult:
    if not isinstance(response, dict):
        return ValidationResult(False, 0, "Response must be a JSON object.")

    players = response.get("players")
    if not isinstance(players, list):
        return ValidationResult(False, 0, "Response missing players array.")

    player_count = len(players)
    if player_count < MIN_PLAYER_COUNT or player_count > MAX_PLAYER_COUNT:
        return ValidationResult(
            False,
            player_count,
            f"Player count must be between {MIN_PLAYER_COUNT} and {MAX_PLAYER_COUNT}.",
        )

    player_names = set()
    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return ValidationResult(False, player_count, f"Player at index {index} must be an object.")

        for field in REQUIRED_PLAYER_FIELDS:
            if field not in player:
                return ValidationResult(False, player_count, f"Player at index {index} missing {field}.")

        if not isinstance(player["name"], str) or not player["name"].strip():
            return ValidationResult(False, player_count, f"Player at index {index} has invalid name.")
        player_names.add(player["name"].strip())
        if not isinstance(player["position"], str) or not player["position"].strip():
            return ValidationResult(False, player_count, f"Player at index {index} has invalid position.")
        if type(player["jersey_number"]) is not int:
            return ValidationResult(False, player_count, f"Player at index {index} has invalid jersey_number.")

    missing_required_players = REQUIRED_PLAYER_NAMES - player_names
    if missing_required_players:
        return ValidationResult(
            False,
            player_count,
            f"Response missing required players: {', '.join(sorted(missing_required_players))}.",
        )

    return ValidationResult(True, player_count, "")


def validate(response: Any) -> ValidationResult:
    return validate_response(response)
