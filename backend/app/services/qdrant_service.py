"""Qdrant vector database operations."""
from __future__ import annotations

import logging
from threading import Lock

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue,
    FilterSelector, SearchRequest as QdrantSearchRequest,
)

from app.config import settings

logger = logging.getLogger(__name__)

TRANSCRIPT_COLLECTION = "transcript_segments"
FRAME_COLLECTION = "video_frames"

_client: QdrantClient | None = None
_client_lock = Lock()


def get_client() -> QdrantClient:
    """Get or create the shared Qdrant client."""
    global _client
    with _client_lock:
        if _client is None:
            kwargs = {
                "host": settings.qdrant_host,
                "port": settings.qdrant_port,
                "check_compatibility": False,
            }
            if settings.qdrant_api_key:
                kwargs["api_key"] = settings.qdrant_api_key
            _client = QdrantClient(**kwargs)
            logger.info("Qdrant client connected to %s:%d",
                        settings.qdrant_host, settings.qdrant_port)
    return _client


def ensure_collections() -> None:
    """Create transcript and frame collections if they don't exist."""
    client = get_client()
    existing = {c.name for c in client.get_collections().collections}

    if TRANSCRIPT_COLLECTION not in existing:
        client.create_collection(
            collection_name=TRANSCRIPT_COLLECTION,
            vectors_config=VectorParams(
                size=settings.text_embedding_dim, distance=Distance.COSINE
            ),
        )
        logger.info("Created Qdrant collection: %s (dim=%d)",
                    TRANSCRIPT_COLLECTION, settings.text_embedding_dim)

    if FRAME_COLLECTION not in existing:
        client.create_collection(
            collection_name=FRAME_COLLECTION,
            vectors_config=VectorParams(
                size=settings.clip_dim, distance=Distance.COSINE
            ),
        )
        logger.info("Created Qdrant collection: %s (dim=%d)",
                    FRAME_COLLECTION, settings.clip_dim)


# ── Transcript operations ────────────────────────────────────────────────

def upsert_transcript_segments(points: list[dict]) -> None:
    """
    Upsert transcript segment vectors.

    Each point must contain:
        {
          "id":       str (UUID),
          "vector":   list[float],
          "payload":  {meeting_id, speaker, start_time, end_time, text, meeting_title, ...}
        }
    """
    points = [p for p in points if p.get("vector")]
    if not points:
        return
    client = get_client()
    qdrant_points = [
        PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
        for p in points
    ]
    client.upsert(collection_name=TRANSCRIPT_COLLECTION, points=qdrant_points)
    logger.info("Upserted %d transcript segments to Qdrant", len(qdrant_points))


def search_transcripts(
    query_vector: list[float],
    limit: int = 5,
    meeting_id: str | None = None,
) -> list[dict]:
    """Search transcript segments by vector similarity."""
    if not query_vector:
        return []
    client = get_client()
    qfilter = None
    if meeting_id:
        qfilter = Filter(
            must=[FieldCondition(key="meeting_id", match=MatchValue(value=meeting_id))]
        )
    hits = _search_points(
        client,
        collection_name=TRANSCRIPT_COLLECTION,
        query_vector=query_vector,
        limit=limit,
        query_filter=qfilter,
    )
    return [{"score": h.score, **(h.payload or {})} for h in hits]


# ── Frame operations ─────────────────────────────────────────────────────

def upsert_frames(points: list[dict]) -> None:
    """Upsert video-frame CLIP vectors."""
    points = [p for p in points if p.get("vector")]
    if not points:
        return
    client = get_client()
    qdrant_points = [
        PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
        for p in points
    ]
    client.upsert(collection_name=FRAME_COLLECTION, points=qdrant_points)
    logger.info("Upserted %d frames to Qdrant", len(qdrant_points))


def search_frames(
    query_vector: list[float],
    limit: int = 5,
    meeting_id: str | None = None,
) -> list[dict]:
    """Search video frames by CLIP vector similarity."""
    if not query_vector:
        return []
    client = get_client()
    qfilter = None
    if meeting_id:
        qfilter = Filter(
            must=[FieldCondition(key="meeting_id", match=MatchValue(value=meeting_id))]
        )
    hits = _search_points(
        client,
        collection_name=FRAME_COLLECTION,
        query_vector=query_vector,
        limit=limit,
        query_filter=qfilter,
    )
    return [{"score": h.score, **(h.payload or {})} for h in hits]


def delete_meeting_vectors(meeting_id: str) -> None:
    """Delete all vectors belonging to a meeting from both collections."""
    client = get_client()
    qfilter = Filter(
        must=[FieldCondition(key="meeting_id", match=MatchValue(value=meeting_id))]
    )
    for collection in (TRANSCRIPT_COLLECTION, FRAME_COLLECTION):
        try:
            client.delete(
                collection_name=collection,
                points_selector=FilterSelector(filter=qfilter),
            )
            logger.info("Deleted vectors for meeting %s from %s", meeting_id, collection)
        except Exception as e:
            logger.warning("Could not delete from %s: %s", collection, e)


def _search_points(
    client: QdrantClient,
    *,
    collection_name: str,
    query_vector: list[float],
    limit: int,
    query_filter: Filter | None,
):
    """Search using the legacy endpoint supported by the bundled Qdrant image."""
    request = QdrantSearchRequest(
        vector=query_vector,
        filter=query_filter,
        limit=limit,
        with_payload=True,
    )
    response = client.http.search_api.search_points(
        collection_name=collection_name,
        search_request=request,
    )
    return response.result or []
