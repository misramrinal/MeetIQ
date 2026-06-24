"""Extract decisions, action items, topics from a transcript using an LLM."""
from __future__ import annotations

import logging

from app.services.llm_client import chat_json, LLMError

logger = logging.getLogger(__name__)

# Common keys LLMs use when they return an object instead of a plain string.
_TEXT_KEYS = ("text", "name", "topic", "value", "title", "question", "issue", "summary")


def coerce_text(value, *, keys: tuple[str, ...] = _TEXT_KEYS) -> str:
    """Normalize LLM JSON values that may be str, number, or nested dict/list."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float, bool)):
        return str(value).strip()
    if isinstance(value, dict):
        for key in keys:
            nested = value.get(key)
            if nested is not None:
                result = coerce_text(nested, keys=keys)
                if result:
                    return result
        return ""
    if isinstance(value, list):
        parts = [coerce_text(v, keys=keys) for v in value]
        return " ".join(p for p in parts if p).strip()
    return ""


# Maximum transcript size sent to the LLM in one call.# For long meetings, we split into chunks.
MAX_CHUNK_CHARS = 12000

SYSTEM_PROMPT = """You are an expert meeting analyst. \
Your job is to extract structured information from meeting transcripts.

You will receive a transcript segment from a meeting. Each line is formatted as:
  [SPEAKER at TIMESTAMP_SECONDS]: text...

Extract the following and return ONLY valid JSON. No markdown, no explanation, no code fences.

OUTPUT SCHEMA:
{
  "decisions": [
    {
      "text":       "<concise statement of what was decided>",
      "made_by":    "<speaker name from the transcript, or null if unclear>",
      "timestamp":  <float seconds from start, or null>,
      "confidence": <float 0.0..1.0>,
      "context":    "<one sentence describing the surrounding discussion, optional>"
    }
  ],
  "action_items": [
    {
      "text":       "<the task to be done>",
      "owner":      "<person responsible, or null>",
      "due_date":   "<YYYY-MM-DD or null>",
      "timestamp":  <float seconds from start, or null>
    }
  ],
  "topics": ["<short topic phrase>", ...],
  "unresolved": ["<unresolved question or open issue>", ...],
  "summary": "<2-3 sentence executive summary of the discussion>",
  "entities": [
    {
      "name":     "<entity name exactly as mentioned>",
      "type":     "<PERSON | ORG | PRODUCT | TECHNOLOGY>",
      "mentions": <integer count of times mentioned>
    }
  ]
}

RULES:
1. Only extract information that is explicitly stated in the transcript.
2. Do not infer, assume, or invent any information.
3. For decisions, look for clear statements like "we decided", "let's go with", "I think we should".
4. For action items, look for assignments like "X will do Y", "can you handle Z", "I'll take care of...".
5. Use null for any field you cannot determine from the text.
6. Keep topics short (1-4 words each), up to 8 topics maximum.
7. For entities: extract up to 20, only concrete named entities (not pronouns or generic nouns).
8. Output MUST be valid parseable JSON.
"""


def _format_transcript(segments: list[dict]) -> str:
    """Convert segment dicts into the [Speaker at TIME]: text format."""
    lines = []
    for seg in segments:
        speaker = seg.get("speaker", "Speaker")
        start = seg.get("start_time", seg.get("start", 0.0))
        text = coerce_text(seg.get("text"))
        if text:
            lines.append(f"[{speaker} at {start:.1f}s]: {text}")
    return "\n".join(lines)


def _chunk_transcript(transcript: str, max_chars: int) -> list[str]:
    """Split a long transcript into roughly equal chunks at line boundaries."""
    if len(transcript) <= max_chars:
        return [transcript]
    lines = transcript.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_chars and current:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += line_len
    if current:
        chunks.append("\n".join(current))
    return chunks


def _empty_result() -> dict:
    return {
        "decisions": [],
        "action_items": [],
        "topics": [],
        "unresolved": [],
        "summary": "",
        "entities": [],
    }


def _merge_results(results: list[dict]) -> dict:
    """Merge LLM results from multiple chunks into one."""
    merged = _empty_result()
    summaries: list[str] = []
    seen_topics: set[str] = set()
    seen_unresolved: set[str] = set()
    entity_map: dict[tuple[str, str], dict] = {}

    for r in results:
        for item in (r.get("decisions") or []):
            if isinstance(item, dict):
                merged["decisions"].append(item)
        for item in (r.get("action_items") or []):
            if isinstance(item, dict):
                merged["action_items"].append(item)

        for topic in (r.get("topics") or []):
            t = coerce_text(topic, keys=("topic", "name", "text", "value", "title"))
            if t and t.lower() not in seen_topics:
                seen_topics.add(t.lower())
                merged["topics"].append(t)

        for u in (r.get("unresolved") or []):
            u_clean = coerce_text(u, keys=("text", "question", "issue", "value", "name"))
            if u_clean and u_clean.lower() not in seen_unresolved:
                seen_unresolved.add(u_clean.lower())
                merged["unresolved"].append(u_clean)

        for ent in (r.get("entities") or []):
            if isinstance(ent, str):
                name, etype = ent.strip(), "ORG"
            elif isinstance(ent, dict):
                name = coerce_text(ent.get("name"), keys=("name", "text"))
                etype = coerce_text(ent.get("type"), keys=("type",)).upper()
            else:
                continue
            if not name or etype not in {"PERSON", "ORG", "PRODUCT", "TECHNOLOGY"}:
                continue
            key = (name.lower(), etype)
            if key not in entity_map:
                entity_map[key] = {"name": name, "type": etype, "mentions": 0}
            mentions = ent.get("mentions") if isinstance(ent, dict) else 1
            entity_map[key]["mentions"] += int(mentions or 1)

        s = coerce_text(r.get("summary"), keys=("summary", "text", "value"))
        if s:
            summaries.append(s)

    merged["summary"] = " ".join(summaries).strip()
    merged["entities"] = [
        ent
        for ent in sorted(entity_map.values(), key=lambda x: -x["mentions"])
    ][:20]
    return merged


def extract_knowledge(segments: list[dict]) -> dict:
    """
    Extract decisions, action items, topics, unresolved questions, and a summary
    from transcript segments using the configured LLM.

    Args:
        segments: List of segment dicts with keys speaker, start_time, end_time, text.

    Returns:
        Dict with keys: decisions, action_items, topics, unresolved, summary.
        Returns an empty result on LLM failure (logged).
    """
    if not segments:
        return _empty_result()

    transcript = _format_transcript(segments)
    if not transcript.strip():
        return _empty_result()

    chunks = _chunk_transcript(transcript, MAX_CHUNK_CHARS)
    logger.info("Extracting knowledge from %d chunk(s) of transcript", len(chunks))

    results: list[dict] = []
    for i, chunk in enumerate(chunks, 1):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Transcript (chunk {i}/{len(chunks)}):\n\n{chunk}\n\n"
                "Extract decisions, action items, topics, unresolved questions, and a summary. "
                "Return ONLY JSON matching the schema."},
        ]
        try:
            result = chat_json(messages, temperature=0.1, max_tokens=2048)
            results.append(result)
        except LLMError as e:
            logger.error("Knowledge extraction failed on chunk %d: %s", i, e)
            continue
        except Exception as e:
            logger.exception("Unexpected error during knowledge extraction: %s", e)
            continue

    if not results:
        return _empty_result()

    return _merge_results(results)
