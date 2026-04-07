"""TRAPI client for fetching the 1985 New York Yankees roster via GPT-4o."""

import json
import os

import requests
from azure.identity import DefaultAzureCredential

_ROSTER_PROMPT = (
    "List every player on the 1985 New York Yankees roster. "
    "Return the result as a JSON array where each element is an object with "
    'the fields "name" (full player name) and "position" (player position). '
    "Include all players on the 40-man roster. Output only the JSON array, no other text."
)

_COGSERVICES_SCOPE = "https://cognitiveservices.azure.com/.default"


def _get_bearer_token() -> str:
    """Obtain an Azure AD bearer token using DefaultAzureCredential."""
    credential = DefaultAzureCredential()
    token = credential.get_token(_COGSERVICES_SCOPE)
    return token.token


def _parse_roster_content(content: str) -> list[dict]:
    """Parse a JSON string (possibly wrapped in markdown fences) into a player list."""
    content = content.strip()

    # Strip markdown fences if present (e.g. ```json ... ```)
    if content.startswith("```"):
        lines = content.splitlines()
        # Remove opening fence line and closing fence line
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        content = "\n".join(inner).strip()

    try:
        players = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Could not parse TRAPI response as JSON: {content!r}"
        ) from exc

    if not isinstance(players, list):
        raise ValueError(
            f"Expected a JSON array of players, got {type(players).__name__}"
        )

    validated = [
        player
        for player in players
        if isinstance(player, dict) and "name" in player and "position" in player
    ]
    return validated


def fetch_1985_yankees_roster() -> list[dict]:
    """Fetch the 1985 New York Yankees roster from GPT-4o via TRAPI.

    Authentication is performed with ``DefaultAzureCredential`` — no API key is used.

    Environment variables:
        TRAPI_ENDPOINT: Base URL of the TRAPI / Azure OpenAI endpoint (required).
        TRAPI_DEPLOYMENT_NAME: GPT-4o model deployment name (default: ``gpt-4o``).
        TRAPI_API_VERSION: Azure OpenAI API version (default: ``2024-02-01``).

    Returns:
        A list of dicts, each containing at least ``name`` and ``position`` keys.

    Raises:
        ValueError: If ``TRAPI_ENDPOINT`` is not set or the response cannot be parsed.
        RuntimeError: If the TRAPI endpoint returns a non-2xx HTTP status code.
    """
    endpoint = os.environ.get("TRAPI_ENDPOINT", "").rstrip("/")
    deployment_name = os.environ.get("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.environ.get("TRAPI_API_VERSION", "2024-02-01")

    if not endpoint:
        raise ValueError(
            "TRAPI_ENDPOINT environment variable is not set. "
            "Set it to the base URL of your Azure OpenAI / TRAPI endpoint."
        )

    token = _get_bearer_token()

    url = (
        f"{endpoint}/openai/deployments/{deployment_name}"
        f"/chat/completions?api-version={api_version}"
    )
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [{"role": "user", "content": _ROSTER_PROMPT}],
        "temperature": 0,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)

    if not response.ok:
        raise RuntimeError(
            f"TRAPI request failed with HTTP {response.status_code}: {response.text}"
        )

    data = response.json()

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise ValueError(
            f"Unexpected TRAPI response structure: {data!r}"
        ) from exc

    return _parse_roster_content(content)
