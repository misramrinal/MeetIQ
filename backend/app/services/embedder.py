"""
Embeddings — HuggingFace-free stub.

Vector embeddings are disabled because HuggingFace is blocked on this network.
Text search falls back to keyword search (SQL ILIKE) which is fully functional.
Visual search (CLIP) is also disabled — set ENABLE_FRAME_EXTRACTION=false.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_DISABLED_MSG = "Vector embeddings disabled (HuggingFace blocked). Keyword search is active."


def embed_text(text: str) -> list[float]:
    logger.debug(_DISABLED_MSG)
    return []


def embed_texts(texts: list[str]) -> list[list[float]]:
    logger.debug(_DISABLED_MSG)
    return [[] for _ in texts]


def embed_image(image_path: str) -> list[float]:
    logger.debug(_DISABLED_MSG)
    return []


def embed_text_for_image_search(text: str) -> list[float]:
    logger.debug(_DISABLED_MSG)
    return []
