"""Search endpoints: natural-language Q&A and visual search."""
from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import SearchResponse, SearchSource, VisualSearchResponse
from app.services.rag_service import search_and_answer, visual_search

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=SearchResponse)
def text_search(
    query: str = Query(..., min_length=1, max_length=500, description="Natural language question"),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    """
    Hybrid search across all meetings + RAG answer generation.

    Returns an LLM-generated answer with cited transcript sources and timestamps.
    """
    try:
        result = search_and_answer(query, db, top_k=top_k)
    except Exception as e:
        logger.exception("Search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Search failed: {e}")

    sources = [SearchSource(**s) for s in result["sources"]]
    return SearchResponse(
        query=result["query"],
        answer=result["answer"],
        status=result["status"],
        confidence=result["confidence"],
        sources=sources,
    )


@router.post("/visual", response_model=VisualSearchResponse)
def visual_search_endpoint(
    query: str = Query(..., min_length=1, max_length=500, description="Visual search description"),
    top_k: int = Query(5, ge=1, le=20),
):
    """
    Search video frames using a CLIP text-to-image query.

    Example queries:
        - "database schema diagram"
        - "code editor with Python code"
        - "presentation slide with bullet points"
    """
    try:
        frames = visual_search(query, top_k=top_k)
    except Exception as e:
        logger.exception("Visual search failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Visual search failed: {e}")

    return VisualSearchResponse(
        query=query,
        frames=[SearchSource(**f) for f in frames],
    )
