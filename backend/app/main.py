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

    # Warm up heavy ML models so the FIRST upload doesn't pay the model-loading
    # penalty inside the request.
    #
    # NOTE: We deliberately do NOT warm up (or load) PaddleOCR in this process.
    # PaddlePaddle and PyTorch conflict over native OpenMP/CRT DLLs on Windows:
    # loading paddle after torch deadlocks, and loading it before torch breaks
    # torch/ctranslate2 ("WinError 127 ... shm.dll"). OCR therefore runs in an
    # isolated subprocess (see app.services.ocr_service).
    import threading
    from app.services import audio_processor, diarizer, embedder, gpu

    # Initialise torch's GPU cuDNN BEFORE anything imports CTranslate2 (via the
    # Whisper warmup below). Otherwise CTranslate2 binds an incompatible cuDNN
    # first and torch's GPU calls (diarization/CLIP) crash. Done synchronously
    # so the ordering is guaranteed before the warmup thread starts.
    gpu.prime_cuda()

    def _warmup() -> None:
        logger.info("Warming up ML models in background...")
        audio_processor.warmup()
        embedder.warmup()
        diarizer.warmup()
        if settings.enable_frame_extraction:
            embedder.warmup_clip()
        logger.info("Model warmup complete.")

    threading.Thread(target=_warmup, name="model-warmup", daemon=True).start()


# ── Health ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model_name,
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
