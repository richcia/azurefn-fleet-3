import json
import os
import time
from pathlib import Path

import requests
from azure.identity import DefaultAzureCredential


_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()


def _get_bearer_token() -> str:
    scope = os.getenv("TRAPI_SCOPE", "https://cognitiveservices.azure.com/.default")
    token = _DEFAULT_AZURE_CREDENTIAL.get_token(scope)
    return token.token


def fetch_roster(prompt_path: str) -> str:
    endpoint = os.environ["TRAPI_ENDPOINT"].rstrip("/")
    deployment = os.getenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("TRAPI_API_VERSION", "2024-02-01")

    prompt = Path(prompt_path).read_text(encoding="utf-8")
    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions"
    payload = {
        "model": deployment,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {_get_bearer_token()}",
        "Content-Type": "application/json",
    }

    retries = 3
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                params={"api-version": api_version},
                json=payload,
                timeout=45,
            )
            if response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response.text
        except (requests.Timeout, requests.HTTPError) as exc:
            if attempt == retries:
                raise
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            if isinstance(exc, requests.HTTPError) and (status_code is None or status_code < 500):
                raise
            time.sleep(2 ** attempt)

    raise RuntimeError("Unreachable retry state")
