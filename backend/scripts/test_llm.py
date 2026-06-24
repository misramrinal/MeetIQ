"""
LLM smoke test for MeetMind.

Verifies that the configured LLM provider is reachable and returns valid
plain-text and JSON responses.

Run from inside the backend container:
    docker compose exec backend python scripts/test_llm.py

Or locally (after pip install -r requirements.txt and creating .env):
    cd MeetMind/backend
    python scripts/test_llm.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.services.llm_client import chat, chat_json, LLMError  # noqa: E402


def test_plain_chat() -> None:
    print(f"\n[1/2] Plain chat")
    print(f"      Provider : {settings.llm_provider}")
    print(f"      Model    : {settings.llm_model_name}")
    if settings.llm_provider.lower() == "ollama":
        print(f"      Endpoint : {settings.ollama_base_url}")
    else:
        print(f"      Endpoint : {settings.openai_base_url}")
        print(f"      API key  : {'set (' + settings.openai_api_key[:8] + '...)' if settings.openai_api_key else 'MISSING'}")

    try:
        reply = chat(
            [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user",   "content": "In one sentence, what is Retrieval-Augmented Generation?"},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        print("      Status   : OK")
        print(f"      Response : {reply.strip()[:300]}")
    except LLMError as e:
        print(f"      Status   : FAILED — {e}")
        sys.exit(1)


def test_json_extraction() -> None:
    print(f"\n[2/2] JSON extraction (decisions + action items)")

    transcript = (
        "Alice: We've decided to go with PostgreSQL for the main database. "
        "Bob: Sounds good. I'll set up the migration scripts by Friday. "
        "Priya: I'll handle the staging environment deployment next week."
    )
    messages = [
        {
            "role": "system",
            "content": (
                "Extract decisions and action items from the transcript. "
                "Return ONLY valid JSON with keys 'decisions' (list of strings) "
                "and 'action_items' (list of {text, owner})."
            ),
        },
        {"role": "user", "content": f"Transcript:\n{transcript}\n\nReturn JSON only."},
    ]

    try:
        result = chat_json(messages, temperature=0.1, max_tokens=512)
        print("      Status   : OK")
        print(json.dumps(result, indent=2))
    except LLMError as e:
        print(f"      Status   : FAILED — {e}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("  MeetMind — LLM Smoke Test")
    print("=" * 60)
    test_plain_chat()
    test_json_extraction()
    print("\n" + "=" * 60)
    print("  All tests passed.")
    print("=" * 60)
