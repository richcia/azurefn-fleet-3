"""Tests for tests/fixtures/roster_1985_yankees.json (DATA-01 acceptance criteria)."""

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "roster_1985_yankees.json"

KNOWN_PLAYERS = [
    {"name": "Don Mattingly",    "position": "1B", "jersey_number": 23},
    {"name": "Dave Winfield",    "position": "RF", "jersey_number": 31},
    {"name": "Rickey Henderson", "position": "LF", "jersey_number": 24},
]

VALID_POSITIONS = {"1B", "2B", "3B", "SS", "C", "LF", "CF", "RF", "DH", "SP", "RP"}


@pytest.fixture(scope="module")
def roster() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def players(roster: dict) -> list:
    return roster["players"]


class TestFixtureExistence:
    def test_file_exists(self) -> None:
        assert FIXTURE_PATH.exists(), f"Fixture not found at {FIXTURE_PATH}"

    def test_file_is_valid_json(self) -> None:
        try:
            json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            pytest.fail(f"Fixture is not valid JSON: {exc}")


class TestRosterStructure:
    def test_has_players_key(self, roster: dict) -> None:
        assert "players" in roster, "Fixture must have a top-level 'players' key"

    def test_player_count_in_range(self, players: list) -> None:
        count = len(players)
        assert 24 <= count <= 28, f"Expected 24–28 players, got {count}"

    def test_each_player_has_required_fields(self, players: list) -> None:
        for i, player in enumerate(players):
            assert "name" in player,         f"Player[{i}] missing 'name'"
            assert "position" in player,     f"Player[{i}] missing 'position'"
            assert "jersey_number" in player, f"Player[{i}] missing 'jersey_number'"

    def test_name_is_non_empty_string(self, players: list) -> None:
        for i, player in enumerate(players):
            assert isinstance(player["name"], str) and player["name"].strip(), (
                f"Player[{i}] 'name' must be a non-empty string"
            )

    def test_position_is_non_empty_string(self, players: list) -> None:
        for i, player in enumerate(players):
            assert isinstance(player["position"], str) and player["position"].strip(), (
                f"Player[{i}] 'position' must be a non-empty string"
            )

    def test_jersey_number_is_integer(self, players: list) -> None:
        for i, player in enumerate(players):
            assert isinstance(player["jersey_number"], int), (
                f"Player[{i}] 'jersey_number' must be an integer, got {type(player['jersey_number'])}"
            )

    def test_jersey_number_is_positive(self, players: list) -> None:
        for i, player in enumerate(players):
            assert player["jersey_number"] > 0, (
                f"Player[{i}] 'jersey_number' must be positive, got {player['jersey_number']}"
            )

    def test_no_duplicate_jersey_numbers(self, players: list) -> None:
        numbers = [p["jersey_number"] for p in players]
        assert len(numbers) == len(set(numbers)), (
            f"Duplicate jersey numbers found: {[n for n in numbers if numbers.count(n) > 1]}"
        )

    def test_no_duplicate_names(self, players: list) -> None:
        names = [p["name"] for p in players]
        assert len(names) == len(set(names)), (
            f"Duplicate player names found: {[n for n in names if names.count(n) > 1]}"
        )

    def test_outfield_positions_are_specific(self, players: list) -> None:
        for player in players:
            assert player["position"] != "OF", (
                f"Player '{player['name']}' uses generic 'OF' position; "
                "use 'LF', 'CF', or 'RF' instead"
            )


@pytest.mark.parametrize("known", KNOWN_PLAYERS, ids=lambda p: p["name"])
class TestKnownPlayers:
    def test_known_player_present(self, known: dict, players: list) -> None:
        names = [p["name"] for p in players]
        assert known["name"] in names, f"Known player '{known['name']}' not found in fixture"

    def test_known_player_position(self, known: dict, players: list) -> None:
        player = next((p for p in players if p["name"] == known["name"]), None)
        assert player is not None
        assert player["position"] == known["position"], (
            f"{known['name']}: expected position {known['position']!r}, "
            f"got {player['position']!r}"
        )

    def test_known_player_jersey_number(self, known: dict, players: list) -> None:
        player = next((p for p in players if p["name"] == known["name"]), None)
        assert player is not None
        assert player["jersey_number"] == known["jersey_number"], (
            f"{known['name']}: expected jersey #{known['jersey_number']}, "
            f"got #{player['jersey_number']}"
        )
