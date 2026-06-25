"""
End-to-end processing pipeline for a single meeting.

Sequence:
    1.  Extract audio (FFmpeg)
    2.  Transcribe (faster-whisper)
    3.  Diarize speakers (pyannote.audio, optional)
    4.  Align transcript with speakers
    5.  Persist transcript segments
    6.  Generate text embeddings + index in Qdrant
    7.  Extract video frames (OpenCV)
    8.  Run OCR on frames (PaddleOCR)
    9.  Generate image embeddings (CLIP) + index in Qdrant
    10. Extract knowledge (decisions, actions, topics) via LLM
    11. Save decisions, action items, summary to PostgreSQL
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import (
    Meeting, TranscriptSegment, Decision, ActionItem, VideoFrame,
)
from app.services import (
    audio_processor, diarizer, embedder, frame_extractor,
    knowledge_extractor, ocr_service, qdrant_service,
)
from app.services.knowledge_extractor import coerce_text

logger = logging.getLogger(__name__)


class ProcessingTimeout(RuntimeError):
    """Raised when processing exceeds PROCESSING_TIMEOUT_SECONDS."""


def _set_progress(meeting: Meeting, db: Session, stage: str, percent: int) -> None:
    """Persist user-visible processing progress."""
    meeting.processing_stage = stage
    meeting.progress_percent = max(0, min(100, int(percent)))
    db.commit()


def _check_deadline(deadline: float, stage: str) -> None:
    """Abort the pipeline if the wall-clock deadline has passed.

    This is a cooperative check between stages: it cannot interrupt a single
    long-running native call (e.g. Whisper/pyannote), but it prevents the
    pipeline from proceeding into further work once the budget is exhausted.
    """
    if deadline and time.monotonic() > deadline:
        raise ProcessingTimeout(
            f"Processing exceeded the {settings.processing_timeout_seconds}s time "
            f"limit (aborted before '{stage}'). Try a shorter recording, a smaller "
            f"Whisper model, or disabling diarization/OCR."
        )


# ── Public Entry Point ───────────────────────────────────────────────────

def process_meeting(meeting_id: str) -> None:
    """
    Background task entry point. Loads its own DB session.
    Updates Meeting.status as it progresses.
    """
    db: Session = SessionLocal()
    try:
        meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
        if not meeting:
            logger.error("Meeting %s not found, aborting processing.", meeting_id)
            return

        meeting.status = "processing"
        _set_progress(meeting, db, "starting", 1)
        logger.info("[%s] Processing started: %s", meeting_id, meeting.title)

        deadline = (
            time.monotonic() + settings.processing_timeout_seconds
            if settings.processing_timeout_seconds and settings.processing_timeout_seconds > 0
            else 0.0
        )
        _run_pipeline(meeting, db, deadline)

        meeting.status = "done"
        meeting.processing_stage = "complete"
        meeting.progress_percent = 100
        meeting.processed_at = datetime.utcnow()
        db.commit()
        logger.info("[%s] Processing complete.", meeting_id)

    except Exception as e:
        logger.exception("[%s] Processing failed: %s", meeting_id, e)
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                meeting.status = "failed"
                meeting.processing_stage = "failed"
                meeting.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Pipeline Implementation ──────────────────────────────────────────────

def _run_pipeline(meeting: Meeting, db: Session, deadline: float = 0.0) -> None:
    meeting_id_str = str(meeting.id)
    video_path = meeting.recording_path

    # ── Step 1: Extract audio ────────────────────────────────────────────
    _set_progress(meeting, db, "extracting_audio", 5)
    audio_path = os.path.join(settings.audio_dir, f"{meeting_id_str}.wav")
    audio_processor.extract_audio(video_path, audio_path)
    meeting.audio_path = audio_path

    duration = audio_processor.get_video_duration(video_path)
    if duration:
        meeting.duration_seconds = int(duration)
    _set_progress(meeting, db, "audio_extracted", 12)

    _check_deadline(deadline, "transcription")

    # ── Step 2 + 3: Transcribe and diarize concurrently ──────────────────
    _set_progress(meeting, db, "transcribing_and_diarizing", 18)
    # Both only need the audio file and are independent, so overlap them.
    with ThreadPoolExecutor(max_workers=1) as pool:
        diarize_future = pool.submit(diarizer.diarize, audio_path)
        raw_segments, audio_duration = audio_processor.transcribe(audio_path)
        speakers = diarize_future.result()

    if audio_duration and not meeting.duration_seconds:
        meeting.duration_seconds = int(audio_duration)
        _set_progress(meeting, db, "transcribed", 35)
    else:
        _set_progress(meeting, db, "transcribed", 35)

    if not raw_segments:
        raise RuntimeError("No transcript segments produced from the uploaded recording.")

    _check_deadline(deadline, "knowledge extraction & indexing")

    # ── Step 4: Align transcript with speakers ───────────────────────────
    _set_progress(meeting, db, "aligning_speakers", 42)
    aligned = diarizer.align_speakers(raw_segments, speakers)

    # ── Step 5: Persist transcript segments ──────────────────────────────
    _set_progress(meeting, db, "saving_transcript", 48)
    segment_rows: list[TranscriptSegment] = []
    for seg in aligned:
        row = TranscriptSegment(
            id=str(uuid.uuid4()),
            meeting_id=meeting.id,
            speaker=seg.get("speaker", "Speaker"),
            text=seg["text"],
            start_time=seg["start"],
            end_time=seg["end"],
            confidence=seg.get("confidence"),
        )
        segment_rows.append(row)
        db.add(row)
    _set_progress(meeting, db, "transcript_saved", 55)
    logger.info("[%s] Saved %d transcript segments.", meeting_id_str, len(segment_rows))

    # Participants: distinct speakers
    participants = sorted({row.speaker for row in segment_rows if row.speaker})
    meeting.participants = participants
    _set_progress(meeting, db, "indexing_and_extracting_knowledge", 60)

    # Snapshot transcript data as plain dicts so background threads never touch
    # the SQLAlchemy session (which is owned exclusively by this main thread).
    meeting_title = meeting.title
    seg_snapshot = [
        {
            "id": str(row.id),
            "speaker": row.speaker,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "text": row.text,
        }
        for row in segment_rows
    ]

    # ── Steps 6 + 10 run concurrently with frame processing ──────────────
    #   Step 6:  embed transcripts + index in Qdrant   (background thread)
    #   Step 10: extract knowledge via the LLM         (background thread)
    #   Steps 7-9: frame extraction / OCR / CLIP        (this thread; owns DB)
    # The LLM call is the long pole, so overlapping it with embedding and
    # frame work cuts wall-clock time noticeably.
    with ThreadPoolExecutor(max_workers=2) as pool:
        index_future = pool.submit(
            _index_transcripts_in_qdrant, meeting_id_str, meeting_title, seg_snapshot
        )
        knowledge_future = pool.submit(knowledge_extractor.extract_knowledge, seg_snapshot)

        # ── Steps 7-9: Frames + OCR + CLIP (main thread, uses DB) ────────
        if settings.enable_frame_extraction:
            _set_progress(meeting, db, "processing_video_frames", 68)
            _process_video_frames(meeting, db)

        # Surface indexing errors (logged inside), then collect knowledge.
        index_future.result()
        _set_progress(meeting, db, "extracting_knowledge", 82)
        extracted = knowledge_future.result()

    # ── Step 11: Save decisions, action items, summary ───────────────────
    _set_progress(meeting, db, "saving_knowledge", 90)
    _persist_knowledge(meeting, extracted, db)


def _index_transcripts_in_qdrant(
    meeting_id: str,
    meeting_title: str,
    segments: list[dict],
) -> None:
    """Generate text embeddings and upsert to Qdrant.

    Operates on plain dicts (not ORM rows) so it is safe to run in a background
    thread without sharing the SQLAlchemy session.
    """
    if not segments:
        return
    texts = [seg["text"] for seg in segments]
    try:
        vectors = embedder.embed_texts(texts)
    except Exception as e:
        logger.error("[%s] Text embedding failed: %s", meeting_id, e)
        return

    # Skip Qdrant upsert when embeddings are disabled (empty vectors)
    if not any(vectors):
        logger.info("[%s] Embeddings disabled — skipping Qdrant transcript indexing.", meeting_id)
        return

    points = []
    for seg, vec in zip(segments, vectors):
        if not vec:
            continue
        points.append({
            "id": seg["id"],
            "vector": vec,
            "payload": {
                "meeting_id": meeting_id,
                "meeting_title": meeting_title,
                "segment_id": seg["id"],
                "speaker": seg["speaker"],
                "start_time": seg["start_time"],
                "end_time": seg["end_time"],
                "text": seg["text"],
            },
        })

    try:
        qdrant_service.upsert_transcript_segments(points)
    except Exception as e:
        logger.error("[%s] Qdrant upsert (transcripts) failed: %s", meeting_id, e)


def _process_video_frames(meeting: Meeting, db: Session) -> None:
    """Extract frames, run OCR, generate CLIP embeddings, persist to DB + Qdrant."""
    meeting_id_str = str(meeting.id)
    frames_dir = os.path.join(settings.frames_dir, meeting_id_str)

    try:
        frames = frame_extractor.extract_frames(meeting.recording_path, frames_dir)
    except Exception as e:
        logger.warning("[%s] Frame extraction failed: %s", meeting_id_str, e)
        return

    if not frames:
        logger.info("[%s] No frames extracted (probably audio-only).", meeting_id_str)
        return

    frame_rows: list[VideoFrame] = []
    qdrant_points: list[dict] = []

    frame_paths = [f["path"] for f in frames]

    # OCR every frame in ONE isolated subprocess call (paddle inits once).
    try:
        ocr_map = ocr_service.extract_text_batch(frame_paths)
    except Exception as e:
        logger.warning("Batch OCR failed: %s", e)
        ocr_map = {}

    # CLIP-embed all frames in batches (one forward pass per batch instead of
    # one per frame). Order matches ``frames``.
    try:
        image_vecs = embedder.embed_images(frame_paths)
    except Exception as e:
        logger.warning("Batch CLIP embedding failed: %s", e)
        image_vecs = [[] for _ in frame_paths]

    for frame, image_vec in zip(frames, image_vecs):
        ts = frame["timestamp"]
        path = frame["path"]

        ocr_text = ocr_map.get(path, "")

        row = VideoFrame(
            id=str(uuid.uuid4()),
            meeting_id=meeting.id,
            timestamp=ts,
            frame_path=path,
            ocr_text=ocr_text or None,
            scene_type="frame",
        )
        db.add(row)
        frame_rows.append(row)

        if image_vec:
            qdrant_points.append({
                "id": str(row.id),
                "vector": image_vec,
                "payload": {
                    "meeting_id": meeting_id_str,
                    "meeting_title": meeting.title,
                    "frame_id": str(row.id),
                    "timestamp": ts,
                    "frame_path": path,
                    "ocr_text": ocr_text or "",
                },
            })

    db.commit()
    logger.info("[%s] Saved %d frame rows.", meeting_id_str, len(frame_rows))

    try:
        qdrant_service.upsert_frames(qdrant_points)
    except Exception as e:
        logger.error("[%s] Qdrant upsert (frames) failed: %s", meeting_id_str, e)


def _persist_knowledge(meeting: Meeting, extracted: dict, db: Session) -> None:
    """Save decisions, action items, topics, summary to PostgreSQL."""
    decisions = extracted.get("decisions") or []
    actions = extracted.get("action_items") or []
    topics = extracted.get("topics") or []
    unresolved = extracted.get("unresolved") or []
    entities = extracted.get("entities") or []
    summary = coerce_text(extracted.get("summary"), keys=("summary", "text")) or None

    saved_decisions = 0
    saved_actions = 0

    for d in decisions:
        if not isinstance(d, dict):
            continue
        try:
            text = _clean_text(coerce_text(d.get("text"), keys=("text", "decision", "value")))
            if not text:
                continue
            made_by = _clean_text(coerce_text(d.get("made_by"), keys=("made_by", "name", "speaker"))) or None
            context = _clean_text(coerce_text(d.get("context"), keys=("context", "text", "value"))) or None
            db.add(Decision(
                id=str(uuid.uuid4()),
                meeting_id=meeting.id,
                text=text[:5000],
                made_by=made_by,
                timestamp=_safe_float(d.get("timestamp")),
                confidence=_safe_confidence(d.get("confidence")),
                context=context,
            ))
            saved_decisions += 1
        except Exception as e:
            logger.warning("Skipping bad decision row: %s", e)

    for a in actions:
        if not isinstance(a, dict):
            continue
        try:
            text = _clean_text(coerce_text(a.get("text"), keys=("text", "action", "task", "value")))
            if not text:
                continue
            owner = _clean_text(coerce_text(a.get("owner"), keys=("owner", "name", "assignee"))) or None
            due = _parse_date(a.get("due_date"))
            db.add(ActionItem(
                id=str(uuid.uuid4()),
                meeting_id=meeting.id,
                text=text[:5000],
                owner=owner,
                due_date=due,
                timestamp=_safe_float(a.get("timestamp")),
                status="open",
            ))
            saved_actions += 1
        except Exception as e:
            logger.warning("Skipping bad action_item row: %s", e)

    meeting.summary = summary
    meeting.topics = _clean_text_list(topics)
    meeting.unresolved = _clean_text_list(unresolved)
    meeting.entities = entities
    db.commit()
    logger.info(
        "[%s] Saved %d decision(s), %d action item(s), %d topic(s).",
        meeting.id, saved_decisions, saved_actions, len(meeting.topics),
    )


# ── Helpers ──────────────────────────────────────────────────────────────

def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_confidence(value) -> float:
    try:
        if value is None:
            return 0.0
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _clean_text(value: str | None) -> str:
    text = (value or "").strip()
    if text.lower() in {"none", "null", "n/a", "na", "unknown", "not specified"}:
        return ""
    return text


def _clean_text_list(values) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values or []:
        text = _clean_text(coerce_text(value))
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            cleaned.append(text)
    return cleaned


def _parse_date(value) -> date | None:
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
