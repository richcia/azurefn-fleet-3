"""
trapi_client.py

Authenticates to Azure OpenAI via Managed Identity (DefaultAzureCredential),
sends a structured prompt to GPT-4o requesting the 1985 New York Yankees roster,
and returns a parsed list of player names.
"""

import os
import logging
from typing import List

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI, APIError, APITimeoutError

logger = logging.getLogger(__name__)

ROSTER_PROMPT = (
    "List every player who appeared on the 1985 New York Yankees roster. "
    "Return ONLY a plain text list with one player name per line, no numbering, "
    "no extra commentary, no blank lines. Include all pitchers, catchers, "
    "infielders, outfielders, and designated hitters."
)


def get_client() -> AzureOpenAI:
    """Build and return an AzureOpenAI client authenticated via Managed Identity."""
    endpoint = os.environ["TRAPI_ENDPOINT"]
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://cognitiveservices.azure.com/.default",
    )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        azure_ad_token_provider=token_provider,
        api_version="2024-02-01",
    )


def fetch_roster(client: AzureOpenAI | None = None) -> List[str]:
    """
    Fetch the 1985 New York Yankees roster from GPT-4o.

    Parameters
    ----------
    client : AzureOpenAI, optional
        An AzureOpenAI client instance.  If omitted, one is created via
        ``get_client()``.  Accepts an injected client for testability.

    Environment Variables
    ---------------------
    AZURE_OPENAI_DEPLOYMENT_NAME : str
        The Azure OpenAI deployment name (model alias) to call.
        Defaults to ``"gpt-4o"`` if not set.

    Returns
    -------
    List[str]
        Non-empty list of player name strings.

    Raises
    ------
    ValueError
        If the model returns an empty or unparseable response.
    openai.APIError
        Propagated from the SDK on HTTP / server errors.
    openai.APITimeoutError
        Propagated from the SDK on request timeouts.
    """
    if client is None:
        client = get_client()

    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")

    logger.info("Requesting 1985 Yankees roster from deployment '%s'", deployment)

    response = client.chat.completions.create(
        model=deployment,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a precise baseball historian. "
                    "Answer factual questions with complete accuracy."
                ),
            },
            {"role": "user", "content": ROSTER_PROMPT},
        ],
        temperature=0,
        max_tokens=1024,
    )

    raw = ""
    if response.choices:
        raw = (response.choices[0].message.content or "").strip()

    if not raw:
        raise ValueError("Received empty or null response content from the model.")

    players = [line.strip() for line in raw.splitlines() if line.strip()]

    if not players:
        raise ValueError("Could not parse any player names from the model response.")

    logger.info("Fetched %d players from the 1985 Yankees roster", len(players))
    return players
