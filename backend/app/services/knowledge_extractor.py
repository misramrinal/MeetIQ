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
# Characters of overlap between consecutive chunks so decisions that straddle
# a boundary aren't invisible to both LLM calls.
CHUNK_OVERLAP_CHARS = 300

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


def _chunk_transcript(transcript: str, max_chars: int, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Split a long transcript into chunks at line boundaries with overlap.

    The last ``overlap`` characters of each chunk are repeated at the start of
    the next one so decisions / action items that straddle a boundary are visible
    to both LLM calls and not silently dropped.
    """
    if len(transcript) <= max_chars:
        return [transcript]
    lines = transcript.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for line in lines:
        line_len = len(line) + 1
        if current_len + line_len > max_chars and current:
            chunk_text = "\n".join(current)
            chunks.append(chunk_text)
            # Carry the tail of the current chunk into the next one
            tail = chunk_text[-overlap:] if overlap else ""
            current = [tail] if tail else []
            current_len = len(tail) + 1 if tail else 0
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
            # K3 fix: normalise to title-case so "JOHN DOE" and "john doe" merge
            # into a single entry with a consistent display name.
            name_normalised = name.strip().title()
            key = (name_normalised.lower(), etype)
            if key not in entity_map:
                entity_map[key] = {"name": name_normalised, "type": etype, "mentions": 0}
            # Issue-4 fix: LLM sometimes returns mentions as a string ("two").
            # Coerce safely with a fallback to 1 rather than crashing on int().
            raw_mentions = ent.get("mentions") if isinstance(ent, dict) else 1
            try:
                entity_map[key]["mentions"] += int(raw_mentions or 1)
            except (TypeError, ValueError):
                entity_map[key]["mentions"] += 1

        s = coerce_text(r.get("summary"), keys=("summary", "text", "value"))
        if s:
            summaries.append(s)

    # K2 fix: instead of naively joining per-chunk summaries (which produces
    # a multi-paragraph blob with repeated facts), consolidate via a second
    # LLM call when there are multiple chunks.  Single-chunk meetings skip it.
    if len(summaries) == 0:
        merged["summary"] = ""
    elif len(summaries) == 1:
        merged["summary"] = summaries[0]
    else:
        merged["summary"] = _consolidate_summaries(summaries)
    merged["entities"] = [
        ent
        for ent in sorted(entity_map.values(), key=lambda x: -x["mentions"])
    ][:20]
    return merged


def _consolidate_summaries(summaries: list[str]) -> str:
    """Merge per-chunk summaries into a single cohesive summary via one LLM call.

    Falls back to joining the summaries with a separator if the LLM call fails,
    which is still better than the old verbatim concatenation.
    """
    joined = "\n\n".join(f"Chunk {i+1}: {s}" for i, s in enumerate(summaries))
    messages = [
        {"role": "system", "content":
            "You are a meeting summarisation assistant. You will receive several "
            "partial summaries of consecutive segments of the same meeting. "
            "Write a single, concise, non-repetitive 2-4 sentence executive summary "
            "covering the whole meeting. Return only the summary text, no preamble."},
        {"role": "user", "content": joined},
    ]
    try:
        from app.services.llm_client import chat
        return chat(messages, temperature=0.1, max_tokens=300).strip()
    except Exception as e:
        logger.warning("Summary consolidation LLM call failed (%s); using joined fallback.", e)
        # Deduplicated join as a graceful fallback
        seen: set[str] = set()
        parts: list[str] = []
        for s in summaries:
            key = s.lower()[:60]
            if key not in seen:
                seen.add(key)
                parts.append(s)
        return " ".join(parts)


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
