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
import uuid
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

logger = logging.getLogger(__name__)


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
        db.commit()
        logger.info("[%s] Processing started: %s", meeting_id, meeting.title)

        _run_pipeline(meeting, db)

        meeting.status = "done"
        meeting.processed_at = datetime.utcnow()
        db.commit()
        logger.info("[%s] Processing complete.", meeting_id)

    except Exception as e:
        logger.exception("[%s] Processing failed: %s", meeting_id, e)
        try:
            meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
            if meeting:
                meeting.status = "failed"
                meeting.error_message = str(e)[:1000]
                db.commit()
        except Exception:
            pass
    finally:
        db.close()


# ── Pipeline Implementation ──────────────────────────────────────────────

def _run_pipeline(meeting: Meeting, db: Session) -> None:
    meeting_id_str = str(meeting.id)
    video_path = meeting.recording_path

    # ── Step 1: Extract audio ────────────────────────────────────────────
    audio_path = os.path.join(settings.audio_dir, f"{meeting_id_str}.wav")
    audio_processor.extract_audio(video_path, audio_path)
    meeting.audio_path = audio_path

    duration = audio_processor.get_video_duration(video_path)
    if duration:
        meeting.duration_seconds = int(duration)
    db.commit()

    # ── Step 2: Transcribe ───────────────────────────────────────────────
    raw_segments, audio_duration = audio_processor.transcribe(audio_path)
    if audio_duration and not meeting.duration_seconds:
        meeting.duration_seconds = int(audio_duration)
        db.commit()

    if not raw_segments:
        logger.warning("[%s] No transcript segments produced.", meeting_id_str)
        return

    # ── Step 3 + 4: Diarize and align ────────────────────────────────────
    speakers = diarizer.diarize(audio_path)
    aligned = diarizer.align_speakers(raw_segments, speakers)

    # ── Step 5: Persist transcript segments ──────────────────────────────
    segment_rows: list[TranscriptSegment] = []
    for seg in aligned:
        row = TranscriptSegment(
            id=uuid.uuid4(),
            meeting_id=meeting.id,
            speaker=seg.get("speaker", "Speaker"),
            text=seg["text"],
            start_time=seg["start"],
            end_time=seg["end"],
            confidence=seg.get("confidence"),
        )
        segment_rows.append(row)
        db.add(row)
    db.commit()
    logger.info("[%s] Saved %d transcript segments.", meeting_id_str, len(segment_rows))

    # Participants: distinct speakers
    participants = sorted({row.speaker for row in segment_rows if row.speaker})
    meeting.participants = participants
    db.commit()

    # ── Step 6: Embed and index transcripts ──────────────────────────────
    _index_transcripts_in_qdrant(meeting, segment_rows)

    # ── Steps 7-9: Frames + OCR + CLIP ───────────────────────────────────
    if settings.enable_frame_extraction:
        _process_video_frames(meeting, db)

    # ── Step 10: Extract knowledge via LLM ───────────────────────────────
    extracted = knowledge_extractor.extract_knowledge([
        {
            "speaker": row.speaker,
            "start_time": row.start_time,
            "end_time": row.end_time,
            "text": row.text,
        }
        for row in segment_rows
    ])

    # ── Step 11: Save decisions, action items, summary ───────────────────
    _persist_knowledge(meeting, extracted, db)


def _index_transcripts_in_qdrant(
    meeting: Meeting,
    segment_rows: list[TranscriptSegment],
) -> None:
    """Generate text embeddings and upsert to Qdrant."""
    if not segment_rows:
        return
    texts = [row.text for row in segment_rows]
    try:
        vectors = embedder.embed_texts(texts)
    except Exception as e:
        logger.error("[%s] Text embedding failed: %s", meeting.id, e)
        return

    # Skip Qdrant upsert when embeddings are disabled (empty vectors)
    if not any(vectors):
        logger.info("[%s] Embeddings disabled — skipping Qdrant transcript indexing.", meeting.id)
        return

    points = []
    for row, vec in zip(segment_rows, vectors):
        points.append({
            "id": str(row.id),
            "vector": vec,
            "payload": {
                "meeting_id": str(meeting.id),
                "meeting_title": meeting.title,
                "segment_id": str(row.id),
                "speaker": row.speaker,
                "start_time": row.start_time,
                "end_time": row.end_time,
                "text": row.text,
            },
        })

    try:
        qdrant_service.upsert_transcript_segments(points)
    except Exception as e:
        logger.error("[%s] Qdrant upsert (transcripts) failed: %s", meeting.id, e)


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

    for frame in frames:
        ts = frame["timestamp"]
        path = frame["path"]

        # OCR (may return "")
        try:
            ocr_text = ocr_service.extract_text(path)
        except Exception as e:
            logger.warning("OCR failed on %s: %s", path, e)
            ocr_text = ""

        # CLIP embedding
        try:
            image_vec = embedder.embed_image(path)
        except Exception as e:
            logger.warning("CLIP embedding failed on %s: %s", path, e)
            image_vec = None

        row = VideoFrame(
            id=uuid.uuid4(),
            meeting_id=meeting.id,
            timestamp=ts,
            frame_path=path,
            ocr_text=ocr_text or None,
            scene_type="frame",
        )
        db.add(row)
        frame_rows.append(row)

        if image_vec is not None:
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
    summary = (extracted.get("summary") or "").strip() or None

    for d in decisions:
        try:
            db.add(Decision(
                id=uuid.uuid4(),
                meeting_id=meeting.id,
                text=(d.get("text") or "").strip()[:5000],
                made_by=(d.get("made_by") or None),
                timestamp=_safe_float(d.get("timestamp")),
                confidence=float(d.get("confidence") or 0.0),
                context=d.get("context"),
            ))
        except Exception as e:
            logger.warning("Skipping bad decision row: %s", e)

    for a in actions:
        try:
            due = _parse_date(a.get("due_date"))
            db.add(ActionItem(
                id=uuid.uuid4(),
                meeting_id=meeting.id,
                text=(a.get("text") or "").strip()[:5000],
                owner=(a.get("owner") or None),
                due_date=due,
                timestamp=_safe_float(a.get("timestamp")),
                status="open",
            ))
        except Exception as e:
            logger.warning("Skipping bad action_item row: %s", e)

    meeting.summary = summary
    meeting.topics = topics
    meeting.unresolved = unresolved
    meeting.entities = entities
    db.commit()
    logger.info(
        "[%s] Saved %d decision(s), %d action item(s), %d topic(s).",
        meeting.id, len(decisions), len(actions), len(topics),
    )


# ── Helpers ──────────────────────────────────────────────────────────────

def _safe_float(value) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_date(value) -> date | None:
    if not value or not isinstance(value, str):
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None
