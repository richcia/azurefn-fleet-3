"""TRAPI client module for querying GPT-4o to retrieve the 1985 New York Yankees roster."""

import os

from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI, AuthenticationError, APIStatusError


TRAPI_ENDPOINT = os.environ.get("TRAPI_ENDPOINT", "")
GPT4O_DEPLOYMENT = os.environ.get("GPT4O_DEPLOYMENT", "gpt-4o")
TRAPI_SCOPE = "https://cognitiveservices.azure.com/.default"

ROSTER_PROMPT = (
    "List the complete roster of the 1985 New York Yankees baseball team. "
    "Return only the player names as a newline-separated list with no extra commentary, "
    "numbers, or headers. Each line should contain exactly one player name."
)


def _get_token() -> str:
    """Obtain a bearer token using DefaultAzureCredential (managed identity)."""
    credential = DefaultAzureCredential()
    token = credential.get_token(TRAPI_SCOPE)
    return token.token


def _build_client(bearer_token: str) -> AzureOpenAI:
    """Build an AzureOpenAI client authenticated with a bearer token."""
    return AzureOpenAI(
        azure_endpoint=TRAPI_ENDPOINT,
        azure_ad_token=bearer_token,
        api_version="2024-02-01",
    )


def get_1985_yankees_roster() -> list[str]:
    """Query GPT-4o via TRAPI to retrieve the 1985 New York Yankees roster.

    Returns:
        A non-empty list of player name strings.

    Raises:
        ValueError: If TRAPI_ENDPOINT is not configured.
        AuthenticationError: If token acquisition or API authentication fails.
        APIStatusError: If the API returns a non-success HTTP response.
        ValueError: If the API returns an empty or unparseable roster.
    """
    if not TRAPI_ENDPOINT:
        raise ValueError("TRAPI_ENDPOINT environment variable must be set")
    token = _get_token()
    client = _build_client(bearer_token=token)

    response = client.chat.completions.create(
        model=GPT4O_DEPLOYMENT,
        messages=[
            {
                "role": "system",
                "content": "You are a baseball historian with precise knowledge of MLB rosters.",
            },
            {"role": "user", "content": ROSTER_PROMPT},
        ],
        temperature=0,
        max_tokens=1024,
    )

    content = response.choices[0].message.content or ""
    players = [line.strip() for line in content.splitlines() if line.strip()]

    if not players:
        raise ValueError("GPT-4o returned an empty roster; cannot continue.")

    return players
