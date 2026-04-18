import json

from response_validator import validate_response


def test_validate_response_success():
    raw = json.dumps(
        {
            "players": [
                {"name": f"Player {i}", "position": "P", "jersey_number": i}
                for i in range(1, 25)
            ]
        }
    )

    valid, data, error = validate_response(raw)

    assert valid is True
    assert data is not None
    assert error is None


def test_validate_response_invalid_count():
    raw = json.dumps({"players": [{"name": "A", "position": "P", "jersey_number": 1}]})

    valid, _, error = validate_response(raw)

    assert valid is False
    assert "between 24 and 28" in error
