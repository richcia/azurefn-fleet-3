import json
import os

import requests
from azure.identity import DefaultAzureCredential

TRAPI_ENDPOINT = os.environ.get("TRAPI_ENDPOINT", "https://trapi.microsoft.com")
TRAPI_DEPLOYMENT = os.environ.get("TRAPI_DEPLOYMENT", "gpt-4o")
TRAPI_SCOPE = os.environ.get("TRAPI_SCOPE", "api://trapi/.default")
TRAPI_API_VERSION = os.environ.get("TRAPI_API_VERSION", "2024-02-01")


def get_1985_yankees_roster() -> list:
    """Query GPT-4o via TRAPI for the full roster of the 1985 New York Yankees.

    Returns a non-empty list of player name strings.
    Authentication uses DefaultAzureCredential (Managed Identity in production,
    interactive/env-based locally). No API keys or hardcoded tokens are used.

    Environment variables:
        TRAPI_ENDPOINT: Base URL of the TRAPI gateway (default: https://trapi.microsoft.com)
        TRAPI_DEPLOYMENT: GPT-4o deployment name (default: gpt-4o)
        TRAPI_SCOPE: Azure AD token scope for TRAPI (default: api://trapi/.default)
        TRAPI_API_VERSION: Azure OpenAI API version (default: 2024-02-01)

    Raises:
        requests.HTTPError: If the TRAPI request fails.
        ValueError: If the response cannot be parsed as a list of player names.
    """
    credential = DefaultAzureCredential()
    token = credential.get_token(TRAPI_SCOPE)

    url = (
        f"{TRAPI_ENDPOINT}/openai/deployments/{TRAPI_DEPLOYMENT}"
        f"/chat/completions?api-version={TRAPI_API_VERSION}"
    )

    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant that provides accurate historical "
                    "baseball roster data. Always respond with a valid JSON array of "
                    "player name strings and nothing else."
                ),
            },
            {
                "role": "user",
                "content": (
                    "List the complete roster of the 1985 New York Yankees. "
                    "Return ONLY a JSON array of player full names, nothing else. "
                    'Example format: ["Player One", "Player Two"]'
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": 1000,
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.exceptions.Timeout as exc:
        raise requests.exceptions.Timeout(
            "TRAPI request timed out after 30 seconds"
        ) from exc
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"].strip()

    try:
        players = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"TRAPI returned invalid JSON format: {content[:100]}"
        ) from exc

    if not isinstance(players, list) or not players:
        raise ValueError(f"Unexpected response format from TRAPI: {content}")

    return [str(name) for name in players]
