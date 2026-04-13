"""TRAPI client for querying GPT-4o via Azure OpenAI endpoint."""

import json
import logging
import os
import re
import time

import requests
from azure.identity import DefaultAzureCredential

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

logger = logging.getLogger("trapi_client")

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()

_TRAPI_SCOPE = "https://cognitiveservices.azure.com/.default"

# ---------------------------------------------------------------------------
# Retry configuration
# ---------------------------------------------------------------------------

_MAX_RETRIES = 3  # maximum number of retry attempts after the initial request


def _get_bearer_token() -> str:
    """Acquire a bearer token using DefaultAzureCredential."""
    token = _DEFAULT_AZURE_CREDENTIAL.get_token(_TRAPI_SCOPE)
    return token.token


# ---------------------------------------------------------------------------
# Prompt configuration
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a baseball historian. Return ONLY a JSON array of objects with "
    "no additional text. Each object must have exactly two keys: "
    "\"name\" (string) and \"position\" (string)."
)

_USER_PROMPT = (
    "List every player on the 1985 New York Yankees roster. "
    "Return ONLY a JSON array where each element has the keys "
    "\"name\" and \"position\". Do not include any markdown, explanation, "
    "or additional text—only the raw JSON array."
)

_DEFAULT_DEPLOYMENT = "gpt-4o"
_DEFAULT_API_VERSION = "2024-02-01"


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _parse_roster_content(content: str) -> list:
    """Parse GPT-4o response content into a list of player dicts.

    Handles both plain JSON arrays and markdown-fenced code blocks.

    Args:
        content: Raw string content from the model response.

    Returns:
        A list of dicts, each with at minimum ``name`` and ``position`` keys.

    Raises:
        ValueError: If the content cannot be parsed or does not match the
                    expected schema.
    """
    stripped = content.strip()

    # Strip markdown code fences if present (for example ```json ... ```,
    # ``` JSON ... ```, ``` json ... ```, or ``` ... ```).
    fenced = re.match(
        r"^```\s*(?:json)?\s*\n?(.*?)\n?```$",
        stripped,
        re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        stripped = fenced.group(1).strip()

    try:
        parsed = json.loads(stripped)
    except (json.JSONDecodeError, ValueError) as exc:
        preview = stripped[:200]
        suffix = "..." if len(stripped) > 200 else ""
        raise ValueError(
            f"Could not parse TRAPI response as JSON "
            f"(content length={len(stripped)}): {preview}{suffix}"
        ) from exc

    if not isinstance(parsed, list):
        raise ValueError(
            f"Expected a JSON array from TRAPI response, got {type(parsed).__name__}"
        )

    for idx, item in enumerate(parsed):
        if not isinstance(item, dict):
            raise ValueError(
                f"Player entry at index {idx} is not a JSON object: expected object, "
                f"got {type(item).__name__}"
            )
        for field in ("name", "position"):
            if field not in item:
                raise ValueError(
                    f"Player entry at index {idx} is missing required field '{field}'"
                )

    return parsed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def fetch_1985_yankees_roster() -> list:
    """Query TRAPI / Azure OpenAI GPT-4o for the 1985 New York Yankees roster.

    Configuration is read from environment variables:
        TRAPI_ENDPOINT        - Base URL of the Azure OpenAI resource (required)
        TRAPI_DEPLOYMENT_NAME - Deployment name (default: gpt-4o)
        TRAPI_API_VERSION     - API version (default: 2024-02-01)

    Authentication uses DefaultAzureCredential bearer token — no API keys.

    Returns:
        A list of dicts with at minimum ``name`` and ``position`` keys.

    Raises:
        ValueError: If TRAPI_ENDPOINT is not set, or if the response body is
                    not valid JSON, or if the response structure is unexpected,
                    or if roster parsing fails.
        RuntimeError: If the HTTP request returns a 4xx or 5xx status code.
    """
    endpoint = os.environ.get("TRAPI_ENDPOINT")
    if not endpoint:
        raise ValueError("TRAPI_ENDPOINT environment variable is not set")

    deployment = os.environ.get("TRAPI_DEPLOYMENT_NAME", _DEFAULT_DEPLOYMENT)
    api_version = os.environ.get("TRAPI_API_VERSION", _DEFAULT_API_VERSION)

    base = endpoint.rstrip("/")
    url = (
        f"{base}/openai/deployments/{deployment}"
        f"/chat/completions?api-version={api_version}"
    )

    token = _get_bearer_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_PROMPT},
        ],
        "temperature": 0,
    }

    for attempt in range(_MAX_RETRIES + 1):
        response = requests.post(url, headers=headers, json=payload, timeout=60)

        if response.ok:
            break

        retryable = response.status_code == 429 or 500 <= response.status_code < 600
        if retryable and attempt < _MAX_RETRIES:
            delay = 2 ** attempt  # 1 s, 2 s, 4 s
            logger.warning(
                "TRAPI request returned HTTP %s (attempt %d/%d); "
                "retrying in %ds — endpoint=%s",
                response.status_code,
                attempt + 1,
                _MAX_RETRIES + 1,
                delay,
                url,
            )
            time.sleep(delay)
            continue

        body_preview = response.text[:200] + ("..." if len(response.text) > 200 else "")
        logger.error(
            "TRAPI request failed — endpoint=%s, status=%s, body_length=%d: %s",
            url,
            response.status_code,
            len(response.text),
            body_preview,
        )
        raise RuntimeError(
            f"TRAPI request failed with HTTP {response.status_code} "
            f"(body length={len(response.text)}): {body_preview}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise ValueError(
            f"TRAPI returned a non-JSON body (HTTP {response.status_code}): "
            f"{response.text[:200]}"
        ) from exc

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        top_keys = str(list(body.keys())) if isinstance(body, dict) else type(body).__name__
        raise ValueError(
            f"Unexpected TRAPI response structure (top-level keys: {top_keys})"
        ) from exc

    return _parse_roster_content(content)
