"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime settings, loaded from .env or environment."""

    # ── Application ──────────────────────────────────────────────────────
    app_env: str = "development"
    app_name: str = "MeetMind"
    api_version: str = "v1"
    allowed_origins: str = "http://localhost:3000,http://localhost:3001,http://localhost:3002,http://localhost:8000"

    # ── Database ─────────────────────────────────────────────────────────
    # SQLite by default — no installation required
    # For PostgreSQL: postgresql://user:pass@localhost:5432/meetmind
    database_url: str = "sqlite:///./meetmind.db"

    # ── Qdrant ───────────────────────────────────────────────────────────
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    # ── QGenie LLM ───────────────────────────────────────────────────────
    # QGenie is an OpenAI-compatible proxy that routes to Gemini, Claude, etc.
    # Pattern follows jira_hop_detector.py: POST {endpoint}/chat/completions
    qgenie_endpoint: str = "https://qgenie-api.qualcomm.com/v1"
    qgenie_api_key: str = "8720595d-a824-4a8f-8da2-b42e98324e07"

    # Model name passed to QGenie — it routes to the underlying provider.
    # Examples:
    #   vertexai::gemini-3.1-pro-preview
    #   anthropic::claude-3-5-sonnet-20241022
    #   openai::gpt-4o
    llm_model_name: str = "vertexai::gemini-3.1-pro-preview"
    llm_timeout_seconds: int = 180
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # ── Audio (Whisper) ──────────────────────────────────────────────────
    whisper_model: str = "base"             # tiny | base | small | medium | large-v3
    whisper_device: str = "cpu"             # cpu | cuda
    whisper_compute_type: str = "int8"      # int8 | float16 | float32

    # ── Speaker Diarization (pyannote.audio) ─────────────────────────────
    pyannote_auth_token: str = ""           # leave empty to skip diarization
    enable_diarization: bool = True

    # ── Embeddings ───────────────────────────────────────────────────────
    text_embedding_model: str = "BAAI/bge-base-en-v1.5"
    text_embedding_dim: int = 768
    clip_model: str = "openai/clip-vit-base-patch32"
    clip_dim: int = 512

    # ── Video Frame Extraction ───────────────────────────────────────────
    frame_interval_seconds: int = 5
    enable_frame_extraction: bool = True
    enable_ocr: bool = True

    # ── Storage ──────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    frames_dir: str = "frames"
    audio_dir: str = "audio"
    max_upload_mb: int = 500

    # ── Processing ───────────────────────────────────────────────────────
    processing_timeout_seconds: int = 3600

    # ── Pydantic settings config ─────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


# Convenience for imports
settings = get_settings()
