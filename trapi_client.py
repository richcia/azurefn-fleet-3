"""
TRAPI client module for querying GPT-4o via the TRAPI proxy.

Authentication is performed exclusively via Azure Managed Identity
(DefaultAzureCredential). No API key is used.
"""

import os
import json
import logging
import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# The scope used to acquire a bearer token for the TRAPI endpoint.
# Override via the TRAPI_TOKEN_SCOPE environment variable if needed.
_DEFAULT_TOKEN_SCOPE = "api://trapi/.default"

PROMPT = (
    "List every player on the 1985 New York Yankees roster. "
    "Return ONLY a JSON array where each element is an object with the keys "
    '"name" (full name, string) and "position" (abbreviated position, string). '
    "Do not include any explanation or text outside the JSON array."
)


def _get_access_token(scope: str | None = None) -> str:
    """Acquire a bearer token using DefaultAzureCredential."""
    token_scope = scope or os.environ.get("TRAPI_TOKEN_SCOPE", _DEFAULT_TOKEN_SCOPE)
    credential = DefaultAzureCredential()
    token = credential.get_token(token_scope)
    return token.token


def _call_trapi(endpoint: str, access_token: str, prompt: str) -> str:
    """
    Send a chat-completion request to the TRAPI endpoint.

    Returns the raw content string from the first choice.
    Raises requests.HTTPError on non-2xx responses.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _parse_roster(raw_content: str) -> list[dict]:
    """
    Parse the GPT-4o response into a list of player dicts.

    The model is prompted to return a pure JSON array; this function
    extracts the array even if the model wraps it in a code fence.
    """
    content = raw_content.strip()

    # Strip markdown code fences if present (e.g. ```json ... ```)
    if content.startswith("```"):
        lines = content.splitlines()
        # Remove opening fence (```json or ```)
        lines = lines[1:]
        # Remove closing fence
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    players = json.loads(content)
    if not isinstance(players, list):
        raise ValueError("Expected a JSON array of player objects")
    if not players:
        raise ValueError("Expected a non-empty JSON array of player objects")
    return players


def get_1985_yankees_roster(
    endpoint: str | None = None,
    token_scope: str | None = None,
) -> list[dict]:
    """
    Query GPT-4o via TRAPI for the 1985 New York Yankees roster.

    Args:
        endpoint: TRAPI chat-completion URL. Defaults to the
                  ``TRAPI_ENDPOINT`` environment variable.
        token_scope: OAuth2 scope for token acquisition. Defaults to
                     ``TRAPI_TOKEN_SCOPE`` env var or the built-in default.

    Returns:
        A non-empty list of dicts, each with at least ``name`` and
        ``position`` keys.

    Raises:
        ValueError: If TRAPI_ENDPOINT is not configured or the response
                    cannot be parsed into a roster.
        requests.HTTPError: On non-2xx HTTP responses.
    """
    trapi_endpoint = endpoint or os.environ.get("TRAPI_ENDPOINT")
    if not trapi_endpoint:
        raise ValueError(
            "TRAPI endpoint not configured. "
            "Set the TRAPI_ENDPOINT environment variable."
        )

    logger.info("Acquiring access token for TRAPI endpoint: %s", trapi_endpoint)
    access_token = _get_access_token(token_scope)

    logger.info("Querying TRAPI for 1985 Yankees roster")
    raw_content = _call_trapi(trapi_endpoint, access_token, PROMPT)

    logger.info("Parsing roster response")
    roster = _parse_roster(raw_content)
    logger.info("Received %d player records", len(roster))
    return roster
