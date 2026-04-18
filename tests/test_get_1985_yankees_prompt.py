from pathlib import Path


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "get_1985_yankees.txt"


def test_prompt_file_exists():
    assert PROMPT_PATH.exists()


def test_prompt_contains_pinned_model_and_schema_requirements():
    content = PROMPT_PATH.read_text(encoding="utf-8")

    assert "model: gpt-4o-2024-05-13" in content
    assert '{"players":[{"name":"string","position":"string","jersey_number":"integer"}]}' in content
    assert "Don Mattingly" in content
    assert "Dave Winfield" in content
    assert "Rickey Henderson" in content
