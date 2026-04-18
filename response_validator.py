import json
from typing import Any


def validate_response(raw_json: str) -> tuple[bool, dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        return False, None, "Response is not valid JSON"

    if not isinstance(parsed, dict) or "players" not in parsed:
        return False, None, "Missing 'players' key"

    players = parsed["players"]
    if not isinstance(players, list):
        return False, None, "'players' must be a list"

    count = len(players)
    if count < 24 or count > 28:
        return False, None, "Player count must be between 24 and 28"

    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return False, None, f"Player at index {index} is not an object"
        missing = [key for key in ("name", "position", "jersey_number") if key not in player]
        if missing:
            return False, None, f"Player at index {index} missing fields: {', '.join(missing)}"
        if not isinstance(player["jersey_number"], int):
            return False, None, f"Player at index {index} has non-integer jersey_number"

    return True, parsed, None
