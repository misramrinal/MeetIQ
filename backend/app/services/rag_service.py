"""Hybrid retrieval (vector + keyword) and RAG answer generation."""
from __future__ import annotations

import logging
import re

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models import ActionItem, Decision, TranscriptSegment, Meeting
from app.services.embedder import embed_text, embed_text_for_image_search
from app.services.llm_client import chat, LLMError
from app.services.qdrant_service import search_transcripts, search_frames

logger = logging.getLogger(__name__)

NO_RELEVANT_ANSWER = "I could not find this in the meeting recordings."
NON_SEARCH_RESPONSE = (
    "Hi. Ask me a specific question about your meeting recordings, and I will "
    "search the transcripts for a cited answer."
)
STATUS_ANSWERED = "answered"
STATUS_NO_EVIDENCE = "no_evidence"
STATUS_NON_SEARCH = "non_search"
STATUS_LLM_ERROR = "llm_error"

_GREETING_QUERIES = {
    "hi", "hello", "hey", "hiya", "yo", "sup", "thanks", "thank you",
    "good morning", "good afternoon", "good evening",
}
_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "could", "did",
    "do", "does", "for", "from", "how", "i", "in", "is", "it", "me", "of",
    "on", "or", "our", "please", "show", "tell", "that", "the", "this", "to",
    "was", "we", "were", "what", "when", "where", "which", "who", "why",
    "with", "you",
}
_SHORT_DOMAIN_TERMS = {"ai", "db", "ui", "ux"}
_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_+#.-]*")
_TOKEN_BOUNDARY = r"(?<![A-Za-z0-9]){term}(?![A-Za-z0-9])"


def _normalize_query(query: str) -> str:
    """Collapse whitespace and strip punctuation that only frames the query."""
    return re.sub(r"\s+", " ", (query or "").strip()).strip(" \t\r\n?!.,;:")


def _query_terms(query: str) -> list[str]:
    """Return useful lexical terms for keyword matching and evidence checks."""
    terms: list[str] = []
    seen: set[str] = set()
    for raw in _WORD_RE.findall(query.lower()):
        term = raw.strip("._-")
        if not term or term in _STOPWORDS:
            continue
        if len(term) < 3 and term not in _SHORT_DOMAIN_TERMS:
            continue
        if term not in seen:
            seen.add(term)
            terms.append(term)
    return terms


def _term_in_text(term: str, text: str) -> bool:
    """Token-aware term match used after broad SQL candidate selection."""
    if not term or not text:
        return False
    pattern = _TOKEN_BOUNDARY.format(term=re.escape(term.lower()))
    return re.search(pattern, text.lower()) is not None


def _term_hit_count(terms: list[str], text: str) -> int:
    return sum(1 for term in terms if _term_in_text(term, text))


def _canonical_text(text: str | None) -> str:
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return re.sub(r"[^a-z0-9+#. ]+", "", normalized)


def _is_non_search_query(query: str) -> bool:
    """Detect conversational inputs that should not search meeting memory."""
    normalized = _normalize_query(query).lower()
    if not normalized:
        return True
    if normalized in _GREETING_QUERIES:
        return True
    return not _query_terms(normalized)


def _wants_decisions(query: str) -> bool:
    return bool(re.search(r"\b(decision|decisions|decided|decide)\b", query.lower()))


def _wants_actions(query: str) -> bool:
    return bool(re.search(r"\b(action|actions|task|tasks|todo|todos|assigned|owner)\b", query.lower()))


def _normalize_result(item: dict) -> dict:
    """Give Qdrant and SQL rows the same ID shape for dedupe/citations."""
    normalized = dict(item)
    if not normalized.get("id") and normalized.get("segment_id"):
        normalized["id"] = normalized["segment_id"]
    return normalized


def _has_direct_term_evidence(query_terms: list[str], segments: list[dict]) -> bool:
    """Whether retrieved excerpts contain at least one meaningful query term."""
    if not query_terms:
        return False
    for seg in segments:
        text = (seg.get("text") or "").lower()
        if any(_term_in_text(term, text) for term in query_terms):
            return True
    return False


def _has_enough_evidence(query: str, segments: list[dict]) -> bool:
    """Gate weak retrieval so irrelevant snippets are not sent to the LLM."""
    if not segments:
        return False

    terms = _query_terms(query)
    best_score = max(float(seg.get("score") or 0.0) for seg in segments)
    has_keyword_hit = any(seg.get("retrieval") == "keyword" for seg in segments)
    has_structured_hit = any(seg.get("type") in {"decision", "action_item"} for seg in segments)
    has_direct_terms = _has_direct_term_evidence(terms, segments)

    # Keyword hits are literal evidence; vector-only hits need either direct
    # term overlap or a strong cosine score. This prevents short vague inputs
    # from producing confident answers from unrelated nearest neighbors.
    return has_structured_hit or has_keyword_hit or has_direct_terms or best_score >= 0.72


def _result_confidence(segments: list[dict]) -> float:
    """Map retrieved evidence into a compact 0..1 confidence value."""
    if not segments:
        return 0.0
    best = max(float(seg.get("score") or 0.0) for seg in segments)
    structured_bonus = 0.08 if any(seg.get("type") in {"decision", "action_item"} for seg in segments) else 0.0
    return round(min(1.0, best + structured_bonus), 3)


# ── Reciprocal Rank Fusion ───────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
    key_fn=lambda r: r.get("id") or r.get("segment_id") or r.get("text", "")[:120],
) -> list[dict]:
    """
    Combine multiple ranked result lists using RRF.

    For each item, its RRF score = sum over lists of 1 / (k + rank).
    """
    scores: dict = {}
    items: dict = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            item = _normalize_result(item)
            key = key_fn(item)
            if not key:
                continue
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            # Keep the version with the highest original score for display
            if key not in items or item.get("score", 0) > items[key].get("score", 0):
                items[key] = item

    ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    result: list[dict] = []
    for key, rrf_score in ordered:
        item = dict(items[key])
        item["rrf_score"] = rrf_score
        result.append(item)
    return result


def rerank_and_diversify(
    results: list[dict],
    query: str,
    *,
    top_k: int,
    max_per_meeting: int = 2,
    max_per_text: int = 2,
) -> list[dict]:
    """Rerank with lexical overlap and prevent repeated rows from dominating."""
    terms = _query_terms(query)
    scored: list[dict] = []
    for rank, item in enumerate(results):
        item = _normalize_result(item)
        text = item.get("text") or ""
        lexical = _term_hit_count(terms, text) / max(len(terms), 1)
        base = float(item.get("score") or 0.0)
        rrf = float(item.get("rrf_score") or 0.0)
        source_bonus = 0.08 if item.get("type") in {"decision", "action_item"} else 0.0
        keyword_bonus = 0.05 if item.get("retrieval") in {"keyword", "structured"} else 0.0
        item["rank_score"] = round(
            (0.62 * base) + (0.25 * lexical) + (0.08 * min(rrf * 60, 1.0))
            + source_bonus + keyword_bonus - (rank * 0.002),
            6,
        )
        scored.append(item)

    scored.sort(key=lambda r: r.get("rank_score", 0.0), reverse=True)

    selected: list[dict] = []
    meeting_counts: dict[str, int] = {}
    text_counts: dict[str, int] = {}
    seen_ids: set[str] = set()
    for item in scored:
        item_id = item.get("id") or item.get("segment_id") or item.get("source_id")
        if item_id and item_id in seen_ids:
            continue
        meeting_id = str(item.get("meeting_id") or "")
        text_key = _canonical_text(item.get("text"))[:180]
        if meeting_id and meeting_counts.get(meeting_id, 0) >= max_per_meeting:
            continue
        if text_key and text_counts.get(text_key, 0) >= max_per_text:
            continue
        selected.append(item)
        if item_id:
            seen_ids.add(item_id)
        if meeting_id:
            meeting_counts[meeting_id] = meeting_counts.get(meeting_id, 0) + 1
        if text_key:
            text_counts[text_key] = text_counts.get(text_key, 0) + 1
        if len(selected) >= top_k:
            return selected

    for item in scored:
        item_id = item.get("id") or item.get("segment_id") or item.get("source_id")
        if item_id and item_id in seen_ids:
            continue
        selected.append(item)
        if item_id:
            seen_ids.add(item_id)
        if len(selected) >= top_k:
            break
    return selected


# ── Hybrid Retrieval ─────────────────────────────────────────────────────

def hybrid_search_transcripts(
    query: str,
    db: Session,
    top_k: int = 5,
) -> list[dict]:
    """
    Hybrid retrieval over transcript segments:
    - Vector search via Qdrant (semantic)
    - Keyword search via PostgreSQL ILIKE
    - Combined with Reciprocal Rank Fusion
    """
    normalized_query = _normalize_query(query)
    query_terms = _query_terms(normalized_query)
    if not normalized_query or not query_terms:
        return []

    # 1. Vector search (skipped when embeddings are disabled)
    try:
        query_vec = embed_text(normalized_query)
        raw_vec_results = search_transcripts(query_vec, limit=top_k * 3) if query_vec else []
        vec_results = []
        for result in raw_vec_results:
            result = _normalize_result(result)
            result["retrieval"] = "vector"
            vec_results.append(result)
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        vec_results = []

    # 2. Keyword search via SQL ILIKE over meaningful terms. Avoid raw
    # substring search for the full query because short inputs like "hi"
    # otherwise match unrelated words such as "this" or "high".
    try:
        filters = [TranscriptSegment.text.ilike(f"%{term}%") for term in query_terms]
        kw_rows = (
            db.query(TranscriptSegment, Meeting.title)
            .join(Meeting, TranscriptSegment.meeting_id == Meeting.id)
            .filter(or_(*filters))
            .limit(top_k * 5)
            .all()
        )
        kw_results = []
        for row in kw_rows:
            text = row[0].text or ""
            term_hits = _term_hit_count(query_terms, text)
            if term_hits <= 0:
                continue
            coverage = term_hits / max(len(query_terms), 1)
            kw_results.append({
                "id": str(row[0].id),
                "meeting_id": str(row[0].meeting_id),
                "meeting_title": row[1],
                "speaker": row[0].speaker,
                "start_time": row[0].start_time,
                "end_time": row[0].end_time,
                "text": text,
                "score": min(0.95, 0.55 + (0.35 * coverage)),
                "retrieval": "keyword",
            })
        kw_results.sort(key=lambda r: r["score"], reverse=True)
        kw_results = kw_results[:top_k * 2]
    except Exception as e:
        logger.warning("Keyword search failed: %s", e)
        kw_results = []

    # 3. Merge with RRF, then rerank for lexical fit and diversity.
    fused = reciprocal_rank_fusion([vec_results, kw_results])
    return rerank_and_diversify(fused, normalized_query, top_k=top_k)


def structured_search(
    query: str,
    db: Session,
    top_k: int = 5,
) -> list[dict]:
    """Retrieve explicit decisions and action items alongside transcript RAG."""
    normalized_query = _normalize_query(query)
    query_terms = _query_terms(normalized_query)
    if not query_terms:
        return []
    wants_decisions = _wants_decisions(normalized_query)
    wants_actions = _wants_actions(normalized_query)

    def _score(text: str, extra: str = "", intent_match: bool = False) -> float:
        haystack = f"{text or ''} {extra or ''}"
        hits = _term_hit_count(query_terms, haystack)
        if intent_match and hits <= 0:
            return 0.72
        if hits <= 0:
            return 0.0
        coverage = hits / max(len(query_terms), 1)
        intent_bonus = 0.06 if intent_match else 0.0
        return min(0.98, 0.66 + (0.28 * coverage) + intent_bonus)

    filters = [Decision.text.ilike(f"%{term}%") for term in query_terms]
    filters.extend(Decision.context.ilike(f"%{term}%") for term in query_terms)
    filters.extend(Decision.made_by.ilike(f"%{term}%") for term in query_terms)

    results: list[dict] = []
    try:
        decision_query = (
            db.query(Decision, Meeting.title)
            .join(Meeting, Decision.meeting_id == Meeting.id)
        )
        if not wants_decisions:
            decision_query = decision_query.filter(or_(*filters))
        decision_query = decision_query.limit(top_k * 3)
        rows = decision_query.all()
        for decision, meeting_title in rows:
            if not (decision.text or "").strip():
                continue
            score = _score(
                decision.text,
                f"{decision.context or ''} {decision.made_by or ''}",
                intent_match=wants_decisions,
            )
            if score <= 0:
                continue
            results.append({
                "id": f"decision:{decision.id}",
                "source_id": str(decision.id),
                "type": "decision",
                "meeting_id": str(decision.meeting_id),
                "meeting_title": meeting_title,
                "speaker": decision.made_by,
                "made_by": decision.made_by,
                "start_time": decision.timestamp,
                "end_time": decision.timestamp,
                "text": decision.text,
                "score": score,
                "retrieval": "structured",
            })
    except Exception as e:
        logger.warning("Decision structured search failed: %s", e)

    action_filters = [ActionItem.text.ilike(f"%{term}%") for term in query_terms]
    action_filters.extend(ActionItem.owner.ilike(f"%{term}%") for term in query_terms)
    action_filters.extend(ActionItem.status.ilike(f"%{term}%") for term in query_terms)

    try:
        action_query = (
            db.query(ActionItem, Meeting.title)
            .join(Meeting, ActionItem.meeting_id == Meeting.id)
        )
        if not wants_actions:
            action_query = action_query.filter(or_(*action_filters))
        action_query = action_query.limit(top_k * 3)
        rows = action_query.all()
        for action, meeting_title in rows:
            if not (action.text or "").strip():
                continue
            score = _score(
                action.text,
                f"{action.owner or ''} {action.status or ''}",
                intent_match=wants_actions,
            )
            if score <= 0:
                continue
            due = action.due_date.isoformat() if action.due_date else None
            results.append({
                "id": f"action_item:{action.id}",
                "source_id": str(action.id),
                "type": "action_item",
                "meeting_id": str(action.meeting_id),
                "meeting_title": meeting_title,
                "speaker": action.owner,
                "owner": action.owner,
                "due_date": due,
                "status": action.status,
                "start_time": action.timestamp,
                "end_time": action.timestamp,
                "text": action.text,
                "score": score,
                "retrieval": "structured",
            })
    except Exception as e:
        logger.warning("Action-item structured search failed: %s", e)

    return rerank_and_diversify(
        sorted(results, key=lambda r: r["score"], reverse=True),
        normalized_query,
        top_k=top_k,
    )


# ── RAG Answer Generation ────────────────────────────────────────────────

def _build_context(segments: list[dict]) -> str:
    """Format retrieved segments into a context block for the LLM."""
    lines = []
    for i, seg in enumerate(segments[:5], 1):
        source_type = seg.get("type") or "transcript"
        start = seg.get("start_time", 0.0)
        text = (seg.get("text") or "").strip()
        title = seg.get("meeting_title", "")
        meeting_part = f" — {title}" if title else ""
        time_part = f" at {float(start):.1f}s" if start is not None else ""
        if source_type == "decision":
            made_by = seg.get("made_by") or seg.get("speaker") or "Unknown"
            lines.append(f"[{i}] Decision{time_part}{meeting_part} (made by {made_by}): {text}")
        elif source_type == "action_item":
            owner = seg.get("owner") or seg.get("speaker") or "Unassigned"
            due = f", due {seg.get('due_date')}" if seg.get("due_date") else ""
            state = f", status {seg.get('status')}" if seg.get("status") else ""
            lines.append(f"[{i}] Action item{time_part}{meeting_part} (owner {owner}{due}{state}): {text}")
        else:
            speaker = seg.get("speaker", "Unknown")
            lines.append(f"[{i}] {speaker}{time_part}{meeting_part}: {text}")
    return "\n\n".join(lines)


ANSWER_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about past meetings.

You will receive a question and a list of relevant transcript excerpts from those meetings.

Rules:
1. Answer ONLY using information present in the provided excerpts.
2. If the answer is not in the excerpts, say exactly "I could not find this in the meeting recordings."
3. Be concise but complete. Reference speakers by name when relevant.
4. Do not infer topics or intent from weakly related excerpts.
5. Do not invent timestamps, names, or details that are not in the excerpts.
6. When citing a fact, you may reference the excerpt number in square brackets, e.g. [1] or [2].
"""


def generate_answer(query: str, segments: list[dict]) -> tuple[str, str]:
    """Generate an answer to the query using the provided context segments."""
    if not segments:
        return NO_RELEVANT_ANSWER, STATUS_NO_EVIDENCE

    context = _build_context(segments)
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content":
            f"Question: {query}\n\nMeeting Excerpts:\n{context}\n\n"
            "Answer the question using only these excerpts."},
    ]

    try:
        return chat(messages, temperature=0.2, max_tokens=512).strip(), STATUS_ANSWERED
    except LLMError as e:
        logger.error("Answer generation failed: %s", e)
        return f"(LLM error while generating answer: {e})", STATUS_LLM_ERROR


def search_and_answer(query: str, db: Session, top_k: int = 5) -> dict:
    """
    Full RAG pipeline: hybrid search + LLM answer.

    Returns:
        {"query": str, "answer": str, "sources": [SearchSource-shaped dicts]}
    """
    normalized_query = _normalize_query(query)
    if _is_non_search_query(normalized_query):
        return {
            "query": normalized_query or query,
            "answer": NON_SEARCH_RESPONSE,
            "status": STATUS_NON_SEARCH,
            "confidence": 0.0,
            "sources": [],
        }

    structured = structured_search(normalized_query, db, top_k=top_k)
    transcript = hybrid_search_transcripts(normalized_query, db, top_k=top_k)
    if structured and (_wants_decisions(normalized_query) or _wants_actions(normalized_query)):
        segments = structured[:top_k]
    else:
        segments = reciprocal_rank_fusion([structured, transcript])[:top_k]
    if not _has_enough_evidence(normalized_query, segments):
        return {
            "query": normalized_query,
            "answer": NO_RELEVANT_ANSWER,
            "status": STATUS_NO_EVIDENCE,
            "confidence": 0.0,
            "sources": [],
        }

    confidence = _result_confidence(segments)
    answer, status = generate_answer(normalized_query, segments)

    sources = []
    for seg in segments[:top_k]:
        sources.append({
            "type": seg.get("type") or "transcript",
            "source_id": seg.get("source_id") or seg.get("id") or seg.get("segment_id"),
            "meeting_id": seg.get("meeting_id"),
            "meeting_title": seg.get("meeting_title"),
            "speaker": seg.get("speaker"),
            "text": seg.get("text"),
            "start_time": seg.get("start_time"),
            "end_time": seg.get("end_time"),
            "made_by": seg.get("made_by"),
            "owner": seg.get("owner"),
            "due_date": seg.get("due_date"),
            "status": seg.get("status"),
            "score": float(seg.get("score") or seg.get("rrf_score") or 0.0),
        })

    return {
        "query": normalized_query,
        "answer": answer,
        "status": status,
        "confidence": confidence if status == STATUS_ANSWERED else 0.0,
        "sources": sources,
    }


# ── Visual Search ────────────────────────────────────────────────────────

def visual_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Search video frames using a CLIP text-to-image query.

    Returns a list of frame hits with payload + score.
    """
    normalized_query = _normalize_query(query)
    if _is_non_search_query(normalized_query):
        return []

    try:
        vec = embed_text_for_image_search(normalized_query)
    except Exception as e:
        logger.error("CLIP text embedding failed: %s", e)
        return []
    if not vec:
        logger.info("Visual search skipped because CLIP embeddings are unavailable.")
        return []

    results = search_frames(vec, limit=top_k)
    sources = []
    for r in results:
        sources.append({
            "type": "frame",
            "meeting_id": r.get("meeting_id"),
            "meeting_title": r.get("meeting_title"),
            "frame_id": r.get("frame_id"),
            "timestamp": r.get("timestamp"),
            "frame_path": r.get("frame_path"),
            "ocr_text": r.get("ocr_text"),
            "score": float(r.get("score") or 0.0),
        })
    return sources
