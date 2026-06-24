"""Portable LLM client for Ollama and OpenAI-compatible chat APIs."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

import requests

from app.config import settings

logger = logging.getLogger(__name__)

LLM_MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds; wait = base ** (attempt - 1)


class LLMError(RuntimeError):
    """Raised when an LLM provider call fails after all retries."""


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
            body = e.response.text[:300] if e.response is not None else ""
            if status < 500:
                raise LLMError(f"{label} HTTP {status}: {body}") from e
            last_exc = e
            if attempt == max_retries:
                raise LLMError(f"{label} HTTP {status} after {attempt} attempt(s): {body}") from e
            wait = RETRY_BACKOFF_BASE ** (attempt - 1)
            logger.warning("[%s] HTTP %d, retry %d/%d in %ds",
                           label, status, attempt, max_retries, wait)
            time.sleep(wait)
    if last_exc:
        raise LLMError(f"{label} exhausted retries") from last_exc


def _call_ollama(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
) -> str:
    """Call a local Ollama chat model."""
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"
    payload = {
        "model": settings.llm_model_name,
        "messages": messages,
        "stream": False,
        # Keep the model resident in RAM between requests so back-to-back
        # meetings don't pay the multi-second model (re)load cost each time.
        "keep_alive": "30m",
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }
    if json_mode:
        # Native JSON-constrained decoding: avoids stray prose / code fences
        # and reduces failed parses (and the retries they cause).
        payload["format"] = "json"

    def _do_call() -> str:
        response = requests.post(url, json=payload, timeout=settings.llm_timeout_seconds)
        response.raise_for_status()
        data = response.json()
        content = data.get("message", {}).get("content", "")
        if not content:
            raise LLMError("Ollama returned empty content")
        return content

    return _retry(_do_call, LLM_MAX_RETRIES, "Ollama")


def _call_openai_compatible(
    messages: list[dict],
    temperature: float,
    max_tokens: int,
    json_mode: bool = False,
) -> str:
    """Call OpenAI or any OpenAI-compatible /chat/completions endpoint."""
    if not settings.openai_api_key:
        raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

    url = f"{settings.openai_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model_name,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    def _do_call() -> str:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=settings.llm_timeout_seconds,
            verify=settings.openai_ssl_verify,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("OpenAI-compatible provider returned no choices")
        content = choices[0].get("message", {}).get("content", "")
        if not content:
            raise LLMError("OpenAI-compatible provider returned empty content")
        return content

    return _retry(_do_call, LLM_MAX_RETRIES, "OpenAI-compatible")


def chat(
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
    json_mode: bool = False,
) -> str:
    """
    Send a chat request to the configured LLM provider and return response text.

    Supported providers:
      - ollama: local Ollama /api/chat
      - openai: OpenAI or compatible /chat/completions endpoint
    """
    temp = temperature if temperature is not None else settings.llm_temperature
    toks = max_tokens if max_tokens is not None else settings.llm_max_tokens
    provider = settings.llm_provider.lower().strip()

    t0 = time.time()
    logger.info("LLM call: provider=%s, model=%s, messages=%d",
                provider, settings.llm_model_name, len(messages))

    if provider == "ollama":
        result = _call_ollama(messages, temp, toks, json_mode)
    elif provider == "openai":
        result = _call_openai_compatible(messages, temp, toks, json_mode)
    else:
        raise LLMError("Unsupported LLM_PROVIDER. Use 'ollama' or 'openai'.")

    elapsed = time.time() - t0
    logger.info("LLM call done in %.1fs (%d chars)", elapsed, len(result))
    return result


def chat_json(
    messages: list[dict],
    *,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict:
    """
    Send a chat request and parse the response as JSON.

    Requests native JSON-constrained output from the provider and still
    handles common LLM quirks (markdown code fences, extra text around JSON).
    """
    raw = chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
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

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    raise LLMError(f"Could not parse JSON from LLM response: {raw[:300]}")
