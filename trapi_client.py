"""
trapi_client.py – Fetches the 1985 New York Yankees roster from GPT-4o via
the Microsoft TRAPI (Teams Real-time AI Platform) endpoint.

Required environment variables:
    TRAPI_ENDPOINT  – Full HTTPS URL of the TRAPI chat-completions endpoint.
    TRAPI_SCOPE     – Azure AD OAuth scope for the TRAPI resource
                      (e.g. "api://<resource-id>/.default").

No API keys or hardcoded credentials are used; authentication is handled by
azure-identity DefaultAzureCredential (Managed Identity in production,
developer credentials locally).
"""

import json
import os
import time
import logging
from typing import List, Optional

import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_PROMPT = (
    "List every player on the 1985 New York Yankees baseball roster. "
    "Return ONLY a JSON array of strings, where each element is a player's "
    "full name. Do not include any explanation or extra text. Example: "
    '["Player One", "Player Two"]'
)

_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BACKOFF_BASE = 1.0  # seconds


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_roster(
    *,
    max_retries: int = _DEFAULT_MAX_RETRIES,
    backoff_base: float = _DEFAULT_BACKOFF_BASE,
) -> List[str]:
    """Return the 1985 New York Yankees roster as a list of player name strings.

    Raises:
        EnvironmentError: If TRAPI_ENDPOINT or TRAPI_SCOPE are not set.
        RuntimeError:     If the HTTP call fails after all retries or the
                          response cannot be parsed.
    """
    endpoint = os.environ.get("TRAPI_ENDPOINT")
    scope = os.environ.get("TRAPI_SCOPE")

    if not endpoint:
        raise EnvironmentError("TRAPI_ENDPOINT environment variable is not set.")
    if not scope:
        raise EnvironmentError("TRAPI_SCOPE environment variable is not set.")

    token = _acquire_token(scope)
    players = _call_trapi(endpoint, token, max_retries=max_retries, backoff_base=backoff_base)
    return players


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _acquire_token(scope: str) -> str:
    """Obtain a Bearer token for *scope* via DefaultAzureCredential."""
    credential = DefaultAzureCredential()
    token = credential.get_token(scope)
    return token.token


def _call_trapi(
    endpoint: str,
    token: str,
    *,
    max_retries: int,
    backoff_base: float,
) -> List[str]:
    """POST to the TRAPI chat-completions endpoint and parse the roster."""
    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "user", "content": _PROMPT},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        except requests.RequestException as exc:
            logger.warning("Request error on attempt %d: %s", attempt + 1, exc)
            last_exc = exc
            _maybe_sleep(attempt, backoff_base, max_retries)
            continue

        if response.status_code == 200:
            return _parse_response(response.json())

        if response.status_code == 429:
            logger.warning(
                "Rate-limited (429) on attempt %d/%d; backing off.",
                attempt + 1,
                max_retries + 1,
            )
            _maybe_sleep(attempt, backoff_base, max_retries)
            last_exc = requests.HTTPError(response=response)
            continue

        # Non-retryable HTTP error – raise immediately.
        response.raise_for_status()

    raise RuntimeError(
        f"TRAPI call failed after {max_retries + 1} attempts."
    ) from last_exc


def _maybe_sleep(attempt: int, backoff_base: float, max_retries: int) -> None:
    """Sleep with exponential backoff unless this is the last attempt."""
    if attempt < max_retries:
        sleep_time = backoff_base * (2 ** attempt)
        logger.debug("Sleeping %.1fs before retry.", sleep_time)
        time.sleep(sleep_time)


def _parse_response(data: dict) -> List[str]:
    """Extract the roster list from the TRAPI/OpenAI chat-completions response."""
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as exc:
        raise RuntimeError(f"Unexpected TRAPI response structure: {data}") from exc

    content = content.strip()
    if not content:
        return []

    try:
        players = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Could not parse JSON roster from TRAPI response: {content!r}"
        ) from exc

    if not isinstance(players, list):
        raise RuntimeError(
            f"Expected a JSON array from TRAPI, got {type(players).__name__}: {content!r}"
        )

    return [str(p) for p in players]
