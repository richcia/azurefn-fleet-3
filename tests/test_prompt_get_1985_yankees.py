"""Unit tests for prompts/get_1985_yankees.txt (APP-01 acceptance criteria)."""

import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "get_1985_yankees.txt"

ANCHOR_PLAYERS = ["Don Mattingly", "Dave Winfield", "Rickey Henderson"]

# Pin normalized SHA-256 so any unintentional prompt change is caught.
# Update this constant ONLY after a deliberate prompt revision.
EXPECTED_PROMPT_SHA256 = "bb0943a131f76dc80f3acf74f9a915902145f8a711eabbb07a21d6f900eb74b0"


@pytest.fixture(scope="module")
def prompt_text() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def normalized_prompt(prompt_text: str) -> str:
    """Mirrors trapi_client._normalize_prompt logic for stable SHA-256."""
    return "\n".join(line.rstrip() for line in prompt_text.strip().splitlines())


class TestPromptFileExistence:
    def test_file_exists(self) -> None:
        assert PROMPT_PATH.exists(), f"Prompt file not found at {PROMPT_PATH}"

    def test_file_is_readable(self, prompt_text: str) -> None:
        assert len(prompt_text) > 0, "Prompt file is empty"


class TestPromptModelVersionHeader:
    def test_model_version_comment_present(self, prompt_text: str) -> None:
        first_line = prompt_text.splitlines()[0].strip()
        assert re.match(
            r"^# model: gpt-4o-\d{4}-\d{2}-\d{2}$", first_line
        ), f"First line must match '# model: gpt-4o-YYYY-MM-DD', got: {first_line!r}"


class TestPromptJsonSchema:
    def test_schema_players_key_mentioned(self, prompt_text: str) -> None:
        assert '"players"' in prompt_text, "Prompt must reference the 'players' key in schema"

    def test_schema_name_field_mentioned(self, prompt_text: str) -> None:
        assert '"name"' in prompt_text, "Prompt must reference the 'name' field in schema"

    def test_schema_position_field_mentioned(self, prompt_text: str) -> None:
        assert '"position"' in prompt_text, "Prompt must reference the 'position' field in schema"

    def test_schema_jersey_number_field_mentioned(self, prompt_text: str) -> None:
        assert '"jersey_number"' in prompt_text, "Prompt must reference the 'jersey_number' field in schema"

    def test_schema_example_is_valid_json(self, prompt_text: str) -> None:
        import json

        # Find all JSON-like substrings and verify at least the schema example is valid JSON.
        for line in prompt_text.splitlines():
            stripped = line.strip()
            if stripped.startswith('{"players"'):
                try:
                    json.loads(stripped)
                except json.JSONDecodeError as exc:
                    pytest.fail(f"Schema example line is not valid JSON: {stripped!r} — {exc}")
                return
        pytest.fail("No schema example line starting with '{\"players\"' found in prompt")


class TestPromptRosterRequirements:
    def test_requests_active_roster_only(self, prompt_text: str) -> None:
        lower = prompt_text.lower()
        assert "active" in lower and "roster" in lower, (
            "Prompt must explicitly request the active roster (both 'active' and 'roster' required)"
        )

    def test_requests_24_to_28_players(self, prompt_text: str) -> None:
        assert re.search(r"24[–\-]28|24 to 28|between 24 and 28", prompt_text), (
            "Prompt must explicitly state the 24-28 player count range"
        )

    @pytest.mark.parametrize("player", ANCHOR_PLAYERS)
    def test_anchor_player_mentioned(self, prompt_text: str, player: str) -> None:
        assert player in prompt_text, f"Prompt must mention anchor player: {player}"


class TestPromptOutputFormat:
    def test_no_markdown_fencing_instruction(self, prompt_text: str) -> None:
        lower = prompt_text.lower()
        assert "markdown" in lower or "code fence" in lower or "backtick" in lower or "code block" in lower, (
            "Prompt must explicitly prohibit markdown fencing/code blocks"
        )

    def test_json_only_instruction(self, prompt_text: str) -> None:
        lower = prompt_text.lower()
        assert "json" in lower, "Prompt must instruct to return JSON"


class TestPromptFileStability:
    def test_no_trailing_whitespace(self, prompt_text: str) -> None:
        for i, line in enumerate(prompt_text.splitlines(), start=1):
            assert line == line.rstrip(), f"Line {i} has trailing whitespace: {line!r}"

    def test_no_crlf_line_endings(self, prompt_text: str) -> None:
        assert "\r\n" not in prompt_text, "File must use LF line endings, not CRLF"

    def test_sha256_is_stable(self, normalized_prompt: str) -> None:
        """Pin the normalized SHA-256 so unintentional prompt changes are caught."""
        digest = hashlib.sha256(normalized_prompt.encode("utf-8")).hexdigest()
        assert digest == EXPECTED_PROMPT_SHA256, (
            f"Prompt file has changed unexpectedly. "
            f"Expected {EXPECTED_PROMPT_SHA256!r}, got {digest!r}. "
            "Update EXPECTED_PROMPT_SHA256 only after an intentional prompt revision."
        )
