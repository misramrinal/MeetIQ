"""Audio extraction and transcription using FFmpeg + faster-whisper."""
from __future__ import annotations

import logging
import os
import subprocess
from threading import Lock

from app.config import settings, resolve_device, resolve_whisper_compute_type

# Use all available CPU cores for transcription (faster-whisper default is 4).
_CPU_THREADS = os.cpu_count() or 4

logger = logging.getLogger(__name__)

_whisper_model = None
_whisper_lock = Lock()


def _get_whisper():
    """Lazy-load the Whisper model (loaded once, shared)."""
    global _whisper_model
    with _whisper_lock:
        if _whisper_model is None:
            device = resolve_device(settings.whisper_device)
            compute_type = resolve_whisper_compute_type(device)
            logger.info(
                "Loading faster-whisper model: %s (device=%s, compute_type=%s)",
                settings.whisper_model, device, compute_type,
            )
            from faster_whisper import WhisperModel
            try:
                _whisper_model = WhisperModel(
                    settings.whisper_model,
                    device=device,
                    compute_type=compute_type,
                    cpu_threads=_CPU_THREADS,
                )
            except Exception as e:
                # GPU init can fail if CUDA/cuDNN libs are missing — fall back
                # to CPU so transcription always works.
                if device != "cpu":
                    logger.warning(
                        "Whisper GPU init failed (%s); falling back to CPU int8.", e
                    )
                    _whisper_model = WhisperModel(
                        settings.whisper_model,
                        device="cpu",
                        compute_type="int8",
                        cpu_threads=_CPU_THREADS,
                    )
                else:
                    raise
            logger.info("Whisper model loaded (device=%s, cpu_threads=%d).",
                        device, _CPU_THREADS)
    return _whisper_model


def warmup() -> None:
    """Eagerly load the Whisper model so the first request doesn't pay for it."""
    try:
        _get_whisper()
    except Exception as e:  # pragma: no cover - warmup is best-effort
        logger.warning("Whisper warmup failed: %s", e)


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
    Transcribe audio file using faster-whisper.

    Returns:
        (segments, duration_seconds)
        segments: list of {"text": str, "start": float, "end": float, "confidence": float}
    """
    model = _get_whisper()
    logger.info("Transcribing: %s", audio_path)

    # Performance tuning:
    #   - beam_size=1 (greedy) is ~2-4x faster than the default beam search
    #     with only a small accuracy cost on clear speech.
    #   - vad_filter skips silence so we don't transcribe dead air (big win on
    #     real meetings with pauses).
    #   - condition_on_previous_text=False avoids slow repetition loops.
    segments: list[dict] = []
    duration = 0.0
    try:
        segments_iter, info = model.transcribe(
            audio_path,
            word_timestamps=False,
            beam_size=1,
            vad_filter=True,
            condition_on_previous_text=False,
        )
        for seg in segments_iter:
            avg_logprob = getattr(seg, "avg_logprob", -0.5)
            confidence = max(0.0, min(1.0, avg_logprob + 1.0))
            segments.append({
                "text": seg.text.strip(),
                "start": float(seg.start),
                "end": float(seg.end),
                "confidence": confidence,
            })
        duration = float(getattr(info, "duration", 0.0) or (segments[-1]["end"] if segments else 0.0))
    except ValueError as e:
        # faster-whisper raises "max() arg is an empty sequence" when VAD removes
        # the entire audio track (pure silence / no speech). Return empty segments
        # so video files can still have their frames OCR'd.
        logger.warning("Whisper found no speech (%s); continuing with empty transcript.", e)

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
