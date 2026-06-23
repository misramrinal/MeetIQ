"""FastAPI application entry point for MeetMind."""
from __future__ import annotations

# Apply SSL bypass FIRST — before any HuggingFace/requests/httpx imports.
# Required on corporate networks with self-signed certificates.
from app import ssl_patch
ssl_patch.apply()

import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.database import init_db
from app.routers import actions, decisions, meetings, search
from app.services.qdrant_service import ensure_collections

# ── Logging ──────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── FastAPI app ──────────────────────────────────────────────────────────

app = FastAPI(
    title="MeetMind API",
    description="Multimodal Meeting Intelligence Platform",
    version=__version__,
)

origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ──────────────────────────────────────────────────────────────

@app.on_event("startup")
def on_startup() -> None:
    logger.info("Starting %s v%s (env=%s)", settings.app_name, __version__, settings.app_env)

    # Ensure storage dirs exist
    for d in (settings.upload_dir, settings.frames_dir, settings.audio_dir):
        os.makedirs(d, exist_ok=True)

    # Create DB tables (idempotent; Alembic preferred in production)
    try:
        init_db()
        logger.info("Database tables ensured.")
    except Exception as e:
        logger.error("Database init failed: %s", e)

    # Create Qdrant collections
    try:
        ensure_collections()
        logger.info("Qdrant collections ensured.")
    except Exception as e:
        logger.error("Qdrant init failed: %s", e)


# ── Health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_model": settings.llm_model_name,
        "qgenie_endpoint": settings.qgenie_endpoint,
        "whisper_model": settings.whisper_model,
        "diarization_enabled": bool(settings.pyannote_auth_token) and settings.enable_diarization,
    }


@app.get("/")
def root() -> dict:
    return {
        "name": "MeetMind API",
        "version": __version__,
        "docs": "/docs",
        "health": "/health",
    }


# ── Routers ──────────────────────────────────────────────────────────────

API_PREFIX = f"/api/{settings.api_version}"

app.include_router(meetings.router, prefix=f"{API_PREFIX}/meetings", tags=["meetings"])
app.include_router(search.router, prefix=f"{API_PREFIX}/search", tags=["search"])
app.include_router(actions.router, prefix=f"{API_PREFIX}/actions", tags=["actions"])
app.include_router(decisions.router, prefix=f"{API_PREFIX}/decisions", tags=["decisions"])
