"""Validation helpers for TRAPI roster responses."""

from __future__ import annotations

import json
from typing import Any

REQUIRED_PLAYER_FIELDS = ("name", "position", "jersey_number")
MIN_PLAYER_COUNT = 24
MAX_PLAYER_COUNT = 28


def validate_response(raw_json: Any) -> tuple[bool, dict, str]:
    """Validate expected response schema and player count constraints."""
    if isinstance(raw_json, str):
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            return False, {}, f"Response is not valid JSON: {exc.msg}"
    else:
        payload = raw_json

    if not isinstance(payload, dict):
        return False, {}, "Response body must be a JSON object"

    if "players" not in payload:
        return False, {}, "Response missing required 'players' key"

    players = payload["players"]
    if not isinstance(players, list):
        return False, {}, "'players' must be a list"

    player_count = len(players)
    if player_count < MIN_PLAYER_COUNT or player_count > MAX_PLAYER_COUNT:
        return (
            False,
            {},
            f"Player count {player_count} is out of range; expected {MIN_PLAYER_COUNT}-{MAX_PLAYER_COUNT}",
        )

    for index, player in enumerate(players):
        if not isinstance(player, dict):
            return False, {}, f"Player at index {index} must be an object"

        for field_name in REQUIRED_PLAYER_FIELDS:
            if field_name not in player:
                return (
                    False,
                    {},
                    f"Player at index {index} missing required '{field_name}' field",
                )

        if not isinstance(player["name"], str):
            return False, {}, f"Player at index {index} has non-string 'name'"

        if not isinstance(player["position"], str):
            return False, {}, f"Player at index {index} has non-string 'position'"

        jersey_number = player["jersey_number"]
        if not isinstance(jersey_number, int) or isinstance(jersey_number, bool):
            return False, {}, f"Player at index {index} has non-integer 'jersey_number'"

    return True, {"players": players}, ""
