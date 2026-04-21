import hashlib
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

import requests
from azure.identity import DefaultAzureCredential

from src.validator import ValidationErrorKind, validate_roster_response


TRAPI_AUTH_SCOPE = os.getenv("TRAPI_AUTH_SCOPE", "api://trapi/.default")
TRAPI_ENDPOINT = os.getenv("TRAPI_ENDPOINT", "").rstrip("/")
TRAPI_DEPLOYMENT_NAME = os.getenv("TRAPI_DEPLOYMENT_NAME", "")
TRAPI_API_VERSION = os.getenv("TRAPI_API_VERSION", "2025-04-01-preview")
TRAPI_TIMEOUT_SECONDS = 45
TRAPI_MAX_RETRIES = 3
TRAPI_FATAL_STATUS_CODES = {400, 401, 403}
TRAPI_MAX_BACKOFF_SECONDS = 8
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "get_1985_yankees.txt"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()
_LOGGER = logging.getLogger(__name__)


class RosterValidationError(RuntimeError):
    def __init__(self, kind: ValidationErrorKind, message: str, response_payload: Any):
        super().__init__(message)
        self.kind = kind
        self.response_payload = response_payload


class TRAPIRetryExhaustedError(RuntimeError):
    def __init__(self, status_code: int, retries: int, response_payload: Any):
        super().__init__(f"TRAPI retries exhausted after {retries} retries with status {status_code}")
        self.status_code = status_code
        self.retries = retries
        self.response_payload = response_payload


def _classify_status_code(status_code: int) -> str:
    if status_code in TRAPI_FATAL_STATUS_CODES:
        return "fatal"
    if status_code == 429 or 500 <= status_code <= 599:
        return "transient"
    return "other"


def _safe_response_payload(response: Any) -> Any:
    try:
        return response.json()
    except Exception:
        return {"status_code": getattr(response, "status_code", None)}


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

        status_classification = _classify_status_code(response.status_code)
        if status_classification == "transient":
            if attempt < TRAPI_MAX_RETRIES:
                retry_attempt = attempt + 1
                jitter = random.uniform(0, delay_seconds)
                sleep_seconds = min(TRAPI_MAX_BACKOFF_SECONDS, delay_seconds + jitter)
                _LOGGER.warning(
                    "trapi_retry_attempt",
                    extra={
                        "attempt_number": retry_attempt,
                        "status_code": response.status_code,
                        "sleep_seconds": sleep_seconds,
                    },
                )
                time.sleep(sleep_seconds)
                delay_seconds *= 2
                continue
            raise TRAPIRetryExhaustedError(
                status_code=response.status_code,
                retries=TRAPI_MAX_RETRIES,
                response_payload=_safe_response_payload(response),
            )

        if status_classification == "fatal":
            response.raise_for_status()

        response.raise_for_status()
        response_json = response.json()
        token_count = (
            int(response_json.get("usage", {}).get("total_tokens", 0))
            if isinstance(response_json, dict)
            else 0
        )
        players = response_json.get("players", []) if isinstance(response_json, dict) else []
        player_count = len(players) if isinstance(players, list) else 0

        validation_result = validate_roster_response(response_json)
        if not validation_result.is_valid and validation_result.error is not None:
            raise RosterValidationError(
                kind=validation_result.error.kind,
                message=validation_result.error.message,
                response_payload=response_json,
            )

        return response_json

    raise RuntimeError("TRAPI request failed after maximum retries")
