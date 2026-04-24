"""Unit tests for prompts/get_1985_yankees.txt (APP-01 acceptance criteria)."""

import hashlib
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PROMPT_PATH = REPO_ROOT / "prompts" / "get_1985_yankees.txt"

ANCHOR_PLAYERS = ["Don Mattingly", "Dave Winfield", "Rickey Henderson"]


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


class TestPromptRosterRequirements:
    def test_requests_active_roster_only(self, prompt_text: str) -> None:
        lower = prompt_text.lower()
        assert "active" in lower or "roster" in lower, "Prompt must request active roster members"

    def test_requests_24_to_28_players(self, prompt_text: str) -> None:
        assert "24" in prompt_text and "28" in prompt_text, (
            "Prompt must explicitly specify the 24-28 player count range"
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
        digest = hashlib.sha256(normalized_prompt.encode("utf-8")).hexdigest()
        assert len(digest) == 64, "SHA-256 digest must be 64 hex characters"
        assert all(c in "0123456789abcdef" for c in digest), "SHA-256 digest must be lowercase hex"
