import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import requests
from azure.identity import DefaultAzureCredential

LOGGER = logging.getLogger(__name__)

PROMPT_TEMPLATE_PATH = Path(__file__).resolve().parent / "prompts" / "get_1985_yankees.txt"
DEFAULT_TIMEOUT_SECONDS = 45
MAX_RETRIES = 3
RETRY_STATUS_CODES = {429, 500, 502, 503}
DEFAULT_TRAPI_AUTH_SCOPE = "https://cognitiveservices.azure.com/.default"

_DEFAULT_AZURE_CREDENTIAL = DefaultAzureCredential()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _load_prompt_template() -> dict[str, str]:
    prompt_content = PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")
    system_marker = "\nsystem:\n"
    user_marker = "\n\nuser:\n"

    if system_marker not in prompt_content or user_marker not in prompt_content:
        raise ValueError("Prompt template format is invalid.")

    model_section, system_and_user = prompt_content.split(system_marker, 1)
    system_content, user_content = system_and_user.split(user_marker, 1)

    model = ""
    for line in model_section.splitlines():
        if line.startswith("model:"):
            model = line.split(":", 1)[1].strip()
            break

    if not model:
        raise ValueError("Prompt template is missing model declaration.")

    return {
        "model": model,
        "system": system_content.strip(),
        "user": user_content.strip(),
        "raw": prompt_content,
    }


def _get_bearer_token() -> str:
    auth_scope = os.getenv("TRAPI_AUTH_SCOPE", DEFAULT_TRAPI_AUTH_SCOPE)
    token = _DEFAULT_AZURE_CREDENTIAL.get_token(auth_scope)
    return token.token


def _build_trapi_url(endpoint: str, deployment_name: str, api_version: str) -> str:
    base = endpoint.rstrip("/")
    return f"{base}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"


def _parse_trapi_response(response_body: Any) -> dict[str, Any]:
    if isinstance(response_body, dict) and "players" in response_body:
        return response_body

    choices = response_body.get("choices") if isinstance(response_body, dict) else None
    if not isinstance(choices, list) or not choices:
        raise ValueError("TRAPI response missing choices.")

    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise ValueError("TRAPI response missing message object.")

    content = message.get("content")
    if not isinstance(content, str):
        raise ValueError("TRAPI response message content must be a string.")

    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("TRAPI response JSON content must be an object.")
    return parsed


def fetch_roster() -> dict[str, Any]:
    endpoint = _get_required_env("TRAPI_ENDPOINT")
    deployment_name = os.getenv("TRAPI_DEPLOYMENT_NAME", "gpt-4o")
    api_version = os.getenv("TRAPI_API_VERSION", "2024-02-01")

    prompt = _load_prompt_template()
    prompt_hash = hashlib.sha256(prompt["raw"].encode("utf-8")).hexdigest()
    url = _build_trapi_url(endpoint, deployment_name, api_version)

    for attempt in range(MAX_RETRIES + 1):
        LOGGER.info(
            "Sending TRAPI request",
            extra={"event": "trapi_request_sent", "prompt_sha256": prompt_hash, "attempt": attempt + 1},
        )
        try:
            response = requests.post(
                url,
                headers={
                    "Authorization": f"Bearer {_get_bearer_token()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": prompt["model"],
                    "messages": [
                        {"role": "system", "content": prompt["system"]},
                        {"role": "user", "content": prompt["user"]},
                    ],
                    "temperature": 0,
                },
                timeout=DEFAULT_TIMEOUT_SECONDS,
            )
        except (requests.Timeout, requests.ConnectionError):
            if attempt < MAX_RETRIES:
                time.sleep(2**attempt)
                continue
            raise

        if response.status_code in RETRY_STATUS_CODES and attempt < MAX_RETRIES:
            time.sleep(2**attempt)
            continue

        response.raise_for_status()
        response_body = response.json()
        return _parse_trapi_response(response_body)

    raise RuntimeError("Failed to get successful response from TRAPI after retries.")
