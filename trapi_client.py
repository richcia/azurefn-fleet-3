"""TRAPI client for fetching the 1985 New York Yankees roster via GPT-4o."""

import json
import logging
import os
from typing import Any

import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_TRAPI_ENDPOINT = os.environ.get(
    "TRAPI_ENDPOINT",
    "https://trapi.research.microsoft.com/gcr/shared/openai/deployments/gpt-4o/chat/completions",
)
_API_VERSION = os.environ.get("TRAPI_API_VERSION", "2024-02-01")
_SCOPE = "https://cognitiveservices.azure.com/.default"

_ROSTER_PROMPT = (
    "List every player on the 1985 New York Yankees roster. "
    "Return ONLY a JSON array where each element is an object with exactly two keys: "
    '"name" (full player name as a string) and "position" (primary position as a string). '
    "Do not include any additional text, markdown, or explanation outside the JSON array."
)


class TRAPIError(Exception):
    """Raised when the TRAPI endpoint returns a non-2xx status code."""


def _get_access_token(credential: DefaultAzureCredential | None = None) -> str:
    """Obtain an Azure AD bearer token for the Cognitive Services scope."""
    cred = credential or DefaultAzureCredential()
    token = cred.get_token(_SCOPE)
    return token.token


def _parse_roster(content: str) -> list[dict[str, Any]]:
    """Parse a JSON array of player dicts from the model response content."""
    content = content.strip()
    # Strip markdown code fences if the model wrapped the JSON
    if content.startswith("```"):
        lines = content.splitlines()
        # Drop first line (``` or ```json) and last line (```)
        inner = [ln for ln in lines[1:] if ln.strip() != "```"]
        content = "\n".join(inner).strip()

    players = json.loads(content)
    if not isinstance(players, list):
        raise ValueError("Expected a JSON array of player objects, got a non-list response.")

    validated: list[dict[str, Any]] = []
    for item in players:
        if not isinstance(item, dict):
            logger.warning("Skipping non-dict player entry: %r", item)
            continue
        if "name" not in item or "position" not in item:
            logger.warning("Skipping player entry missing required fields: %r", item)
            continue
        # Intentionally keep only the required fields; extra model fields are discarded.
        validated.append({"name": str(item["name"]), "position": str(item["position"])})

    return validated


def fetch_1985_yankees_roster(
    credential: DefaultAzureCredential | None = None,
    endpoint: str | None = None,
    api_version: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch the complete 1985 New York Yankees roster from GPT-4o via TRAPI.

    Authentication is performed using :class:`~azure.identity.DefaultAzureCredential`
    (no API key).  The caller may supply an alternative credential for testing.

    Args:
        credential: Optional Azure credential.  Defaults to ``DefaultAzureCredential()``.
        endpoint: Override the TRAPI chat-completions endpoint URL.
        api_version: Override the ``api-version`` query parameter.

    Returns:
        A list of dicts, each containing at least ``name`` and ``position`` keys.

    Raises:
        TRAPIError: When the TRAPI endpoint returns a non-2xx HTTP status.
        ValueError: When the model response cannot be parsed as a roster list.
    """
    url = endpoint or _TRAPI_ENDPOINT
    version = api_version or _API_VERSION

    access_token = _get_access_token(credential)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {"role": "system", "content": "You are a baseball historian assistant."},
            {"role": "user", "content": _ROSTER_PROMPT},
        ],
        "temperature": 0,
        "max_tokens": 2048,
    }

    params = {"api-version": version}

    logger.info("Calling TRAPI endpoint: %s", url)
    response = requests.post(url, headers=headers, json=payload, params=params, timeout=60)

    if not response.ok:
        raise TRAPIError(
            f"TRAPI request failed with status {response.status_code}: {response.text}"
        )

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        logger.warning("TRAPI returned no choices; returning empty roster.")
        return []

    content = choices[0].get("message", {}).get("content", "")
    if not content:
        logger.warning("TRAPI returned empty message content; returning empty roster.")
        return []

    players = _parse_roster(content)
    logger.info("Fetched %d players from TRAPI.", len(players))
    return players
