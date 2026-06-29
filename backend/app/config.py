"""Application configuration loaded from environment variables."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent


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

    # ── LLM ──────────────────────────────────────────────────────────────
    # Providers:
    #   ollama: local Ollama server, no API key required
    #   openai: OpenAI or any OpenAI-compatible /chat/completions endpoint
    llm_provider: str = "ollama"
    llm_model_name: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_ssl_verify: bool = True
    llm_timeout_seconds: int = 180
    llm_temperature: float = 0.1
    llm_max_tokens: int = 2048

    # ── Audio (Whisper) ──────────────────────────────────────────────────
    whisper_model: str = "base"             # tiny | base | small | medium | large-v3
    whisper_device: str = "auto"            # auto | cpu | cuda
    whisper_compute_type: str = "auto"      # auto | int8 | float16 | float32

    # ── Speaker Diarization (pyannote.audio) ─────────────────────────────
    pyannote_auth_token: str = ""           # leave empty to skip diarization
    enable_diarization: bool = True
    diarization_device: str = "auto"        # auto | cpu | cuda

    # ── Embeddings ───────────────────────────────────────────────────────
    text_embedding_model: str = "BAAI/bge-base-en-v1.5"
    text_embedding_dim: int = 768
    clip_model: str = "openai/clip-vit-base-patch32"
    clip_dim: int = 512
    # Embeddings stay on CPU by default to leave VRAM for the diarization +
    # Whisper bottleneck on small (e.g. 4 GB) GPUs. Set to "cuda" if you have
    # headroom.
    embedding_device: str = "cpu"           # auto | cpu | cuda

    # ── Video Frame Extraction ───────────────────────────────────────────
    frame_interval_seconds: int = 5
    enable_frame_extraction: bool = True
    enable_ocr: bool = True

    # ── Storage ──────────────────────────────────────────────────────────
    upload_dir: str = "uploads"
    frames_dir: str = "frames"
    audio_dir: str = "audio"
    max_upload_mb: int = 2048

    # ── Processing ───────────────────────────────────────────────────────
    # Wall-clock budget for one meeting. Enforced cooperatively between
    # pipeline stages (see processing_pipeline._check_deadline). Set to 0 to
    # disable the limit.
    processing_timeout_seconds: int = 7200

    # ── Pydantic settings config ─────────────────────────────────────────
    model_config = SettingsConfigDict(
        env_file=(PROJECT_DIR / ".env", BACKEND_DIR / ".env", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached settings singleton."""
    return Settings()


@lru_cache
def cuda_available() -> bool:
    """Whether a CUDA-capable GPU + CUDA-enabled torch is usable.

    Cached so we probe torch only once. Any import/init error is treated as
    "no GPU" so the app always degrades safely to CPU.
    """
    try:
        import torch
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def resolve_device(preference: str) -> str:
    """Resolve a device preference ('auto'|'cpu'|'cuda') to 'cpu' or 'cuda'.

    'auto' -> 'cuda' when available, else 'cpu'. An explicit 'cuda' that isn't
    actually available also degrades to 'cpu' (with the caller free to log it).
    """
    pref = (preference or "auto").strip().lower()
    if pref == "cpu":
        return "cpu"
    if pref in ("auto", "cuda"):
        return "cuda" if cuda_available() else "cpu"
    return "cpu"


def resolve_whisper_compute_type(device: str) -> str:
    """Pick a sensible CTranslate2 compute type for the resolved device."""
    pref = (get_settings().whisper_compute_type or "auto").strip().lower()
    if pref != "auto":
        return pref
    # float16 is the fast, well-supported default on GPU; int8 on CPU.
    return "float16" if device == "cuda" else "int8"


# Convenience for imports
settings = get_settings()
