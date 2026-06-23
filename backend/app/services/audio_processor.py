"""Audio extraction and transcription using FFmpeg + openai-whisper."""
from __future__ import annotations

import logging
import os
import subprocess
from threading import Lock

from app.config import settings

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_lock = Lock()


def _get_whisper():
    """Lazy-load the Whisper model (loaded once, shared)."""
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            logger.info("Loading Whisper model: %s", settings.whisper_model)
            import whisper
            _whisper_model = whisper.load_model(settings.whisper_model)
            logger.info("Whisper model loaded.")
    return _whisper_model


def extract_audio(video_path: str, output_path: str) -> str:
    """
    Extract mono 16kHz WAV audio from a video file using FFmpeg.

    Args:
        video_path: Path to input video or audio file.
        output_path: Path where WAV output will be written.

    Returns:
        The output path.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    logger.info("Extracting audio: %s -> %s", video_path, output_path)

    cmd = [
        "ffmpeg", "-i", video_path,
        "-ar", "16000",
        "-ac", "1",
        "-vn",
        "-y", output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg failed: %s", result.stderr[-500:])
        raise RuntimeError(f"FFmpeg audio extraction failed: {result.stderr[-200:]}")

    return output_path


def transcribe(audio_path: str) -> tuple[list[dict], float]:
    """
    Transcribe audio file using openai-whisper.

    Returns:
        (segments, duration_seconds)
        segments: list of {"text": str, "start": float, "end": float, "confidence": float}
    """
    model = _get_whisper()
    logger.info("Transcribing: %s", audio_path)

    result = model.transcribe(audio_path, verbose=False)

    segments: list[dict] = []
    for seg in result.get("segments", []):
        # avg_logprob is negative; shift by +1 to get a rough 0..1 confidence
        confidence = max(0.0, min(1.0, seg.get("avg_logprob", -0.5) + 1.0))
        segments.append({
            "text": seg["text"].strip(),
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "confidence": confidence,
        })

    # openai-whisper returns total duration via the last segment end or audio info
    duration = float(segments[-1]["end"]) if segments else 0.0
    logger.info("Transcription done: %d segments, %.1fs of audio", len(segments), duration)
    return segments, duration


def get_video_duration(video_path: str) -> float:
    """Use ffprobe to get the duration of a video/audio file in seconds."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", video_path, e)
    return 0.0
