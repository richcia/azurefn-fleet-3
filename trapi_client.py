import hashlib
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from azure.identity import DefaultAzureCredential


TRAPI_AUTH_SCOPE = os.getenv("TRAPI_AUTH_SCOPE", "api://trapi/.default")
TRAPI_ENDPOINT = os.getenv("TRAPI_ENDPOINT", "").rstrip("/")
TRAPI_DEPLOYMENT_NAME = os.getenv("TRAPI_DEPLOYMENT_NAME", "")
TRAPI_API_VERSION = os.getenv("TRAPI_API_VERSION", "2025-04-01-preview")
TRAPI_TIMEOUT_SECONDS = 45
TRAPI_MAX_RETRIES = 3
TRAPI_RETRYABLE_STATUS_CODES = {429, 500, 503}
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "get_1985_yankees.txt"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()
_LOGGER = logging.getLogger(__name__)


def _normalize_prompt(prompt_text: str) -> str:
    return "\n".join(line.rstrip() for line in prompt_text.strip().splitlines())


def _load_prompt() -> str:
    return _normalize_prompt(PROMPT_PATH.read_text(encoding="utf-8"))


def _prompt_hash(prompt_text: str) -> str:
    return hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()


def _get_bearer_token(scope: str | None = None) -> str:
    resolved_scope = scope or TRAPI_AUTH_SCOPE
    return _DEFAULT_AZURE_CREDENTIAL.get_token(resolved_scope).token


def _build_url() -> str:
    if not TRAPI_ENDPOINT:
        raise ValueError("TRAPI_ENDPOINT is required")
    if not TRAPI_DEPLOYMENT_NAME:
        raise ValueError("TRAPI_DEPLOYMENT_NAME is required")
    return (
        f"{TRAPI_ENDPOINT}/openai/deployments/{TRAPI_DEPLOYMENT_NAME}/chat/completions"
        f"?api-version={TRAPI_API_VERSION}"
    )


def fetch_1985_yankees_roster() -> dict[str, Any]:
    prompt_text = _load_prompt()
    prompt_hash = _prompt_hash(prompt_text)
    bearer_token = _get_bearer_token()
    request_url = _build_url()
    payload = {
        "model": TRAPI_DEPLOYMENT_NAME,
        "messages": [{"role": "user", "content": prompt_text}],
    }

    delay_seconds = 1
    for attempt in range(TRAPI_MAX_RETRIES + 1):
        _LOGGER.info(
            "trapi_request_sent",
            extra={
                "model_version": TRAPI_DEPLOYMENT_NAME,
                "prompt_hash": prompt_hash,
                "token_count": 0,
                "latency_ms": 0,
                "player_count": 0,
            },
        )
        started = time.perf_counter()
        response = requests.post(
            request_url,
            headers={
                "Authorization": f"Bearer {bearer_token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=TRAPI_TIMEOUT_SECONDS,
        )
        latency_ms = int((time.perf_counter() - started) * 1000)

        if response.status_code in TRAPI_RETRYABLE_STATUS_CODES and attempt < TRAPI_MAX_RETRIES:
            time.sleep(delay_seconds)
            delay_seconds *= 2
            continue

        response.raise_for_status()
        response_json = response.json()
        token_count = int(response_json.get("usage", {}).get("total_tokens", 0))
        player_count = len(response_json.get("players", []))

        _LOGGER.info(
            "trapi_response_received",
            extra={
                "model_version": TRAPI_DEPLOYMENT_NAME,
                "prompt_hash": prompt_hash,
                "token_count": token_count,
                "latency_ms": latency_ms,
                "player_count": player_count,
            },
        )
        return response_json

    raise RuntimeError("TRAPI request failed after maximum retries")
