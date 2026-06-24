"""Hybrid retrieval (vector + keyword) and RAG answer generation."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models import TranscriptSegment, Meeting
from app.services.embedder import embed_text, embed_text_for_image_search
from app.services.llm_client import chat, LLMError
from app.services.qdrant_service import search_transcripts, search_frames

logger = logging.getLogger(__name__)


# ── Reciprocal Rank Fusion ───────────────────────────────────────────────

def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
    key_fn=lambda r: r.get("id") or r.get("text", "")[:120],
) -> list[dict]:
    """
    Combine multiple ranked result lists using RRF.

    For each item, its RRF score = sum over lists of 1 / (k + rank).
    """
    scores: dict = {}
    items: dict = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
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
    # 1. Vector search (skipped when embeddings are disabled)
    try:
        query_vec = embed_text(query)
        vec_results = search_transcripts(query_vec, limit=top_k * 2) if query_vec else []
    except Exception as e:
        logger.warning("Vector search failed: %s", e)
        vec_results = []

    # 2. Keyword search via PostgreSQL ILIKE
    try:
        kw_rows = (
            db.query(TranscriptSegment, Meeting.title)
            .join(Meeting, TranscriptSegment.meeting_id == Meeting.id)
            .filter(TranscriptSegment.text.ilike(f"%{query}%"))
            .limit(top_k * 2)
            .all()
        )
        kw_results = [
            {
                "id": str(row[0].id),
                "meeting_id": str(row[0].meeting_id),
                "meeting_title": row[1],
                "speaker": row[0].speaker,
                "start_time": row[0].start_time,
                "end_time": row[0].end_time,
                "text": row[0].text,
                "score": 0.5,  # placeholder for display
            }
            for row in kw_rows
        ]
    except Exception as e:
        logger.warning("Keyword search failed: %s", e)
        kw_results = []

    # 3. Merge with RRF
    fused = reciprocal_rank_fusion([vec_results, kw_results])
    return fused[:top_k]


# ── RAG Answer Generation ────────────────────────────────────────────────

def _build_context(segments: list[dict]) -> str:
    """Format retrieved segments into a context block for the LLM."""
    lines = []
    for i, seg in enumerate(segments[:5], 1):
        speaker = seg.get("speaker", "Unknown")
        start = seg.get("start_time", 0.0)
        text = (seg.get("text") or "").strip()
        title = seg.get("meeting_title", "")
        meeting_part = f" — {title}" if title else ""
        lines.append(f"[{i}] {speaker} at {start:.1f}s{meeting_part}: {text}")
    return "\n\n".join(lines)


ANSWER_SYSTEM_PROMPT = """You are a helpful assistant that answers questions about past meetings.

You will receive a question and a list of relevant transcript excerpts from those meetings.

Rules:
1. Answer ONLY using information present in the provided excerpts.
2. If the answer is not in the excerpts, say "I could not find this in the meeting recordings."
3. Be concise but complete. Reference speakers by name when relevant.
4. Do not invent timestamps, names, or details that are not in the excerpts.
5. When citing a fact, you may reference the excerpt number in square brackets, e.g. [1] or [2].
"""


def generate_answer(query: str, segments: list[dict]) -> str:
    """Generate an answer to the query using the provided context segments."""
    if not segments:
        return "I could not find anything relevant in the meeting recordings."

    context = _build_context(segments)
    messages = [
        {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
        {"role": "user", "content":
            f"Question: {query}\n\nMeeting Excerpts:\n{context}\n\n"
            "Answer the question using only these excerpts."},
    ]

    try:
        return chat(messages, temperature=0.2, max_tokens=512).strip()
    except LLMError as e:
        logger.error("Answer generation failed: %s", e)
        return f"(LLM error while generating answer: {e})"


def search_and_answer(query: str, db: Session, top_k: int = 5) -> dict:
    """
    Full RAG pipeline: hybrid search + LLM answer.

    Returns:
        {"query": str, "answer": str, "sources": [SearchSource-shaped dicts]}
    """
    segments = hybrid_search_transcripts(query, db, top_k=top_k)
    answer = generate_answer(query, segments)

    sources = []
    for seg in segments[:top_k]:
        sources.append({
            "type": "transcript",
            "meeting_id": seg.get("meeting_id"),
            "meeting_title": seg.get("meeting_title"),
            "speaker": seg.get("speaker"),
            "text": seg.get("text"),
            "start_time": seg.get("start_time"),
            "end_time": seg.get("end_time"),
            "score": float(seg.get("score") or seg.get("rrf_score") or 0.0),
        })

    return {"query": query, "answer": answer, "sources": sources}


# ── Visual Search ────────────────────────────────────────────────────────

def visual_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Search video frames using a CLIP text-to-image query.

    Returns a list of frame hits with payload + score.
    """
    try:
        vec = embed_text_for_image_search(query)
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
