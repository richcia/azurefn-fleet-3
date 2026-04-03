"""
trapi_client.py

Authenticates to the TRAPI/GPT-4o endpoint using DefaultAzureCredential
(no API keys), requests the 1985 NY Yankees roster, and returns a structured
list of player dicts. Includes retry logic with exponential backoff.
"""
import json
import logging
import os
import time
from typing import Optional

import httpx
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration – supplied via environment variables; safe defaults for local
# dev (actual values must be set in the Function App's application settings).
# ---------------------------------------------------------------------------
TRAPI_ENDPOINT: str = os.environ.get(
    "TRAPI_ENDPOINT",
    "https://trapi.research.microsoft.com",
)
TRAPI_SCOPE: str = os.environ.get(
    "TRAPI_SCOPE",
    "api://trapi/.default",
)
TRAPI_MODEL: str = os.environ.get("TRAPI_MODEL", "gpt-4o")
TRAPI_API_VERSION: str = os.environ.get("TRAPI_API_VERSION", "2024-08-01-preview")

MAX_RETRIES: int = 3
BACKOFF_BASE: float = 2.0  # seconds

_ROSTER_PROMPT = (
    "List the complete roster of the 1985 New York Yankees baseball team. "
    "For each player, provide their full name and primary position. "
    "Return the result as a JSON array of objects. "
    "Each object must have exactly two string fields: "
    '"name" (the player\'s full name) and '
    '"position" (their position abbreviation, e.g. SP, RP, C, 1B, 2B, 3B, '
    "SS, LF, CF, RF, DH, or MGR). "
    "Return only the JSON array with no additional text or markdown."
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_bearer_token(credential: DefaultAzureCredential, scope: str) -> str:
    """Obtain a bearer token from the Azure credential for *scope*."""
    token = credential.get_token(scope)
    return token.token


def _parse_roster(content: str) -> list[dict[str, str]]:
    """Parse the model's text response into a validated list of player dicts.

    Handles optional Markdown code fences that the model may emit.

    Args:
        content: Raw text returned by the model.

    Returns:
        A list of dicts each containing 'name' and 'position' string keys.

    Raises:
        ValueError: If the content cannot be parsed or is structurally invalid.
    """
    text = content.strip()
    # Strip Markdown code fences (```json … ``` or ``` … ```)
    if text.startswith("```"):
        lines = text.splitlines()
        lines = [line for line in lines if not line.startswith("```")]
        text = "\n".join(lines).strip()

    try:
        players = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response is not valid JSON: {exc}") from exc

    if not isinstance(players, list):
        raise ValueError(
            f"Expected a JSON array of players; got {type(players).__name__}"
        )

    validated: list[dict[str, str]] = []
    for idx, player in enumerate(players):
        if not isinstance(player, dict):
            raise ValueError(
                f"Player at index {idx} is not an object; got {type(player).__name__}"
            )
        missing = [f for f in ("name", "position") if f not in player]
        if missing:
            raise ValueError(
                f"Player at index {idx} is missing required fields: {missing}"
            )
        validated.append(
            {"name": str(player["name"]), "position": str(player["position"])}
        )

    return validated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_roster(
    *,
    credential: Optional[DefaultAzureCredential] = None,
    endpoint: Optional[str] = None,
    scope: Optional[str] = None,
    model: Optional[str] = None,
) -> list[dict[str, str]]:
    """Fetch the 1985 New York Yankees roster from GPT-4o via TRAPI.

    Authentication is performed exclusively via *credential* (DefaultAzureCredential
    by default). No API keys are used.

    Transient HTTP 429 (Too Many Requests) and HTTP 503 (Service Unavailable)
    responses trigger an exponential-backoff retry (up to MAX_RETRIES = 3 retries).
    The wait before each retry is ``BACKOFF_BASE ** attempt`` seconds, where
    *attempt* is 0-indexed: delays of 1 s (2^0), 2 s (2^1), 4 s (2^2).

    Args:
        credential: An ``azure.identity.DefaultAzureCredential`` instance. If
            omitted a fresh one is created.
        endpoint: TRAPI base URL. Defaults to the ``TRAPI_ENDPOINT`` env var.
        scope: OAuth2 scope for the TRAPI resource. Defaults to the
            ``TRAPI_SCOPE`` env var.
        model: GPT-4o deployment name. Defaults to the ``TRAPI_MODEL`` env var.

    Returns:
        A list of player dicts, each with 'name' and 'position' string keys.

    Raises:
        httpx.HTTPStatusError: If a non-retryable HTTP error is returned or all
            retries are exhausted.
        ValueError: If the model response cannot be parsed into a valid roster.
    """
    if credential is None:
        credential = DefaultAzureCredential()

    base_url = (endpoint or TRAPI_ENDPOINT).rstrip("/")
    oauth_scope = scope or TRAPI_SCOPE
    deployment = model or TRAPI_MODEL

    url = (
        f"{base_url}/openai/deployments/{deployment}/chat/completions"
        f"?api-version={TRAPI_API_VERSION}"
    )
    payload: dict = {
        "messages": [{"role": "user", "content": _ROSTER_PROMPT}],
        "max_tokens": 2000,
        "temperature": 0,
    }

    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        token = _get_bearer_token(credential, oauth_scope)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            logger.info(
                "TRAPI request attempt %d/%d – url=%s",
                attempt + 1,
                MAX_RETRIES + 1,
                url,
            )
            with httpx.Client(timeout=60.0) as client:
                response = client.post(url, headers=headers, json=payload)

            if response.status_code in (429, 503):
                wait = BACKOFF_BASE**attempt
                logger.warning(
                    "TRAPI returned HTTP %d on attempt %d/%d; "
                    "retrying in %.1f s (backoff base=%.1f, attempt=%d)",
                    response.status_code,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    wait,
                    BACKOFF_BASE,
                    attempt,
                )
                last_error = httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )
                if attempt < MAX_RETRIES:
                    time.sleep(wait)
                    continue
                # Final attempt still got a retriable error → raise
                response.raise_for_status()

            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code not in (429, 503):
                # Non-retryable error – re-raise immediately
                logger.error(
                    "Non-retryable HTTP error on attempt %d: %s", attempt + 1, exc
                )
                raise
            # Retriable 429/503 reached raise_for_status() on the final attempt
            raise

        # Successful response – parse and return
        try:
            data = response.json()
            content: str = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(
                f"Unexpected TRAPI response structure: {exc}"
            ) from exc

        logger.info("TRAPI request succeeded on attempt %d", attempt + 1)
        return _parse_roster(content)

    # Should be unreachable, but satisfy type checkers
    raise last_error or RuntimeError(
        "Failed to retrieve roster after all retries"
    )
