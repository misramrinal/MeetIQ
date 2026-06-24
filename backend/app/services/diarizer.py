"""
Speaker diarization using pyannote.audio.

Gracefully degrades to a single-speaker default if PYANNOTE_AUTH_TOKEN is not set
or pyannote fails to load.
"""
from __future__ import annotations

import logging
from threading import Lock

from app.config import settings, resolve_device

logger = logging.getLogger(__name__)

_pipeline = None
_pipeline_lock = Lock()
_pipeline_load_failed = False


def is_enabled() -> bool:
    """Whether diarization is configured and available."""
    return settings.enable_diarization and bool(settings.pyannote_auth_token)


def _get_pipeline():
    """Lazy-load the pyannote.audio diarization pipeline."""
    global _pipeline, _pipeline_load_failed
    if _pipeline_load_failed:
        return None
    with _pipeline_lock:
        if _pipeline is None:
            try:
                logger.info("Loading pyannote.audio speaker-diarization-3.1...")
                from pyannote.audio import Pipeline
                _pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=settings.pyannote_auth_token,
                )
                # pyannote returns None (without raising) when the token is
                # invalid or the gated model conditions haven't been accepted.
                if _pipeline is None:
                    _pipeline_load_failed = True
                    logger.warning(
                        "Diarization pipeline could not be loaded — the model is "
                        "gated. Ensure PYANNOTE_AUTH_TOKEN is valid AND you have "
                        "accepted the user conditions at "
                        "https://hf.co/pyannote/speaker-diarization-3.1 and "
                        "https://hf.co/pyannote/segmentation-3.0 . "
                        "Falling back to single-speaker."
                    )
                else:
                    device = resolve_device(settings.diarization_device)
                    if device == "cuda":
                        try:
                            import torch
                            _pipeline.to(torch.device("cuda"))
                            logger.info("Diarization pipeline moved to GPU (cuda).")
                        except Exception as e:
                            logger.warning(
                                "Could not move diarization pipeline to GPU (%s); "
                                "running on CPU.", e
                            )
                    logger.info("Diarization pipeline loaded (device=%s).", device)
            except Exception as e:
                logger.warning("Could not load diarization pipeline: %s. Falling back to single-speaker.", e)
                _pipeline_load_failed = True
                _pipeline = None
    return _pipeline


def warmup() -> None:
    """Eagerly load the diarization pipeline so the first request is fast."""
    if not is_enabled():
        return
    try:
        _get_pipeline()
    except Exception as e:  # pragma: no cover - warmup is best-effort
        logger.warning("Diarization warmup failed: %s", e)


def diarize(audio_path: str) -> list[dict]:
    """
    Identify speaker segments in the audio.

    Returns:
        List of {"speaker": str, "start": float, "end": float}
        Returns empty list if diarization is disabled or fails.
    """
    if not is_enabled():
        logger.info("Diarization disabled (no PYANNOTE_AUTH_TOKEN). Skipping.")
        return []

    pipeline = _get_pipeline()
    if pipeline is None:
        return []

    logger.info("Diarizing: %s", audio_path)
    try:
        diarization = pipeline(audio_path)
        speakers: list[dict] = []
        for turn, _, speaker_id in diarization.itertracks(yield_label=True):
            speakers.append({
                "speaker": _humanize_speaker(speaker_id),
                "start": float(turn.start),
                "end": float(turn.end),
            })
        logger.info("Diarization found %d speaker turn(s)", len(speakers))
        return speakers
    except Exception as e:
        logger.error("Diarization failed: %s", e)
        return []


def _humanize_speaker(raw_id: str) -> str:
    """Convert 'SPEAKER_00' style to 'Speaker 1', 'Speaker 2', etc."""
    if raw_id and raw_id.startswith("SPEAKER_"):
        try:
            idx = int(raw_id.split("_", 1)[1]) + 1
            return f"Speaker {idx}"
        except ValueError:
            pass
    return raw_id or "Speaker"


def align_speakers(transcript: list[dict], speakers: list[dict]) -> list[dict]:
    """
    Assign each transcript segment to the most-overlapping speaker.

    If no speaker information is available, all segments get speaker="Speaker".
    """
    if not speakers:
        return [{**seg, "speaker": "Speaker"} for seg in transcript]

    aligned: list[dict] = []
    for seg in transcript:
        seg_start = seg["start"]
        seg_end = seg["end"]
        seg_mid = (seg_start + seg_end) / 2

        # Find the speaker whose segment contains the midpoint
        best_speaker = "Speaker"
        best_overlap = 0.0
        for sp in speakers:
            # Pick the speaker with the most overlap with this segment
            overlap = max(0.0, min(sp["end"], seg_end) - max(sp["start"], seg_start))
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = sp["speaker"]
            elif best_overlap == 0.0 and sp["start"] <= seg_mid <= sp["end"]:
                best_speaker = sp["speaker"]

        aligned.append({**seg, "speaker": best_speaker})

    return aligned
