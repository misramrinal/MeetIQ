"""
QGenie LLM client.

QGenie exposes an OpenAI-compatible /chat/completions endpoint and routes
requests to many underlying models (Vertex AI Gemini, Anthropic Claude, etc.).
Select the model via LLM_MODEL_NAME, e.g. "vertexai::gemini-3.1-pro-preview".

Pattern follows jira_hop_detector.py:
  - POST {QGENIE_ENDPOINT}/chat/completions
  - Authorization: Bearer {QGENIE_API_KEY}
  - verify=False  (internal cert)
  - Retry on 5xx / timeout with exponential backoff
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import requests
import urllib3

from app.config import settings

logger = logging.getLogger(__name__)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LLM_MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; wait = base ** (attempt - 1)


class LLMError(RuntimeError):
    """Raised when a QGenie call fails after all retries."""


# ── Retry helper ─────────────────────────────────────────────────────────

def _retry(call_fn, max_retries: int, label: str) -> Any:
    """Call call_fn(), retrying on transient network errors and HTTP 5xx."""
    last_exc: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return call_fn()
        except (requests.Timeout, requests.ConnectionError) as e:
            last_exc = e
            if attempt == max_retries:
                logger.error("[%s] %s after %d attempt(s)", label, type(e).__name__, attempt)
                raise LLMError(f"{label} failed: {e}") from e
            wait = RETRY_BACKOFF_BASE ** (attempt - 1)
            logger.warning("[%s] Retry %d/%d in %ds (%s)",
                           label, attempt, max_retries, wait, type(e).__name__)
            time.sleep(wait)
        except requests.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status < 500:
                body = e.response.text[:300] if e.response is not None else ""
                raise LLMError(f"{label} HTTP {status}: {body}") from e
            last_exc = e
            if attempt == max_retries:
                raise LLMError(f"{label} HTTP {status} after {attempt} attempt(s)") from e
            wait = RETRY_BACKOFF_BASE ** (attempt - 1)
            logger.warning("[%s] HTTP %d, retry %d/%d in %ds",
                           label, status, attempt, max_retries, wait)
            time.sleep(wait)
    if last_exc:
        raise LLMError(f"{label} exhausted retries") from last_exc


# ── QGenie call ──────────────────────────────────────────────────────────

def _call_qgenie(messages: list[dict], temperature: float, max_tokens: int) -> str:
    """
    POST to QGenie /chat/completions.

    Mirrors the call_llm() pattern from jira_hop_detector.py.
    """
    url = f"{settings.qgenie_endpoint.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.qgenie_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    def _do_call() -> str:
        r = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.llm_timeout_seconds,
            verify=False,   # QGenie uses an internal cert — same as jira_hop_detector.py
        )
        r.raise_for_status()
        data = r.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("QGenie returned no choices")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise LLMError("QGenie returned empty content")
        return content

    return _retry(_do_call, LLM_MAX_RETRIES, "QGenie")


# ── Public interface ─────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """
    Send a chat-completions request to QGenie and return the response text.

    Args:
        messages: List of {"role": "system"|"user"|"assistant", "content": str}
        temperature: Sampling temperature (default: settings.llm_temperature)
        max_tokens:  Max output tokens   (default: settings.llm_max_tokens)

    Returns:
        The assistant's text response.

    Raises:
        LLMError: On any QGenie failure.
    """
    temp = temperature if temperature is not None else settings.llm_temperature
    toks = max_tokens if max_tokens is not None else settings.llm_max_tokens

    t0 = time.time()
    logger.info("QGenie call: model=%s, messages=%d", settings.llm_model_name, len(messages))

    result = _call_qgenie(messages, temp, toks)

    elapsed = time.time() - t0
    logger.info("QGenie call done in %.1fs (%d chars)", elapsed, len(result))
    return result


def chat_json(
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    """
    Send a chat request and parse the response as JSON.

    Handles common LLM quirks: markdown code fences, extra text around JSON.

    Raises:
        LLMError: If the response cannot be parsed as JSON.
    """
    raw = chat(messages, temperature=temperature, max_tokens=max_tokens)
    return _parse_json(raw)


def _parse_json(raw: str) -> dict:
    """Strip code fences and parse JSON from an LLM response."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: find the first {...} block
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMError(f"Could not parse JSON from QGenie response: {raw[:300]}")
