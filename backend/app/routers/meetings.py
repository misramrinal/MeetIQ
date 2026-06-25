"""Meeting upload and management endpoints."""
from __future__ import annotations

import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import List

from fastapi import (
    APIRouter, UploadFile, File, Form, BackgroundTasks,
    Depends, HTTPException, Request, status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import nulls_last

from app.config import settings
from app.database import get_db
from app.models import Meeting, TranscriptSegment, VideoFrame, ChatMessage
from app.schemas import (
    MeetingOut, MeetingStatusOut, TranscriptSegmentOut,
    UploadResponse, VideoFrameOut, ChatMessageOut,
)
from app.services.processing_pipeline import process_meeting
from app.services.qdrant_service import delete_meeting_vectors
from app.services import chat_parser, embedder, qdrant_service

logger = logging.getLogger(__name__)

router = APIRouter()


ALLOWED_EXTENSIONS = {
    ".mp4", ".mov", ".webm", ".mkv", ".avi",
    ".mp3", ".wav", ".m4a", ".ogg", ".flac",
}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_meeting(
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a meeting audio/video file and queue it for processing."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    meeting_id = str(uuid.uuid4())
    safe_name = f"{meeting_id}{ext}"
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, safe_name)

    size = 0
    max_bytes = settings.max_upload_mb * 1024 * 1024
    with open(file_path, "wb") as out:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                out.close()
                os.remove(file_path)
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds maximum size of {settings.max_upload_mb} MB",
                )
            out.write(chunk)

    meeting = Meeting(
        id=meeting_id,
        title=title,
        date=datetime.utcnow().date(),
        recording_path=file_path,
        status="processing",
        processing_stage="queued",
        progress_percent=0,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)

    background_tasks.add_task(process_meeting, meeting_id)
    logger.info("Queued meeting %s (%s) for processing", meeting_id, title)

    return UploadResponse(
        meeting_id=meeting.id,
        status="processing",
        processing_stage="queued",
        progress_percent=0,
        message="Meeting uploaded and queued for processing.",
    )


@router.get("/", response_model=List[MeetingOut])
def list_meetings(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List all meetings, newest first."""
    return (
        db.query(Meeting)
        .order_by(Meeting.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """Get a single meeting by ID."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


@router.get("/{meeting_id}/status", response_model=MeetingStatusOut)
def get_meeting_status(meeting_id: str, db: Session = Depends(get_db)):
    """Get the processing status of a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return MeetingStatusOut(
        meeting_id=meeting.id,
        status=meeting.status,
        processing_stage=meeting.processing_stage,
        progress_percent=meeting.progress_percent or 0,
        error_message=meeting.error_message,
    )


@router.get("/{meeting_id}/transcript", response_model=List[TranscriptSegmentOut])
def get_transcript(meeting_id: str, db: Session = Depends(get_db)):
    """Get the full transcript for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.start_time)
        .all()
    )


@router.get("/{meeting_id}/frames", response_model=List[VideoFrameOut])
def get_frames(meeting_id: str, db: Session = Depends(get_db)):
    """Get all extracted video frames for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return (
        db.query(VideoFrame)
        .filter(VideoFrame.meeting_id == meeting_id)
        .order_by(VideoFrame.timestamp)
        .all()
    )


_MIME_TYPES = {
    ".mp4": "video/mp4", ".webm": "video/webm", ".mov": "video/quicktime",
    ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".ogg": "audio/ogg", ".flac": "audio/flac",
}
_STREAM_CHUNK = 1024 * 1024  # 1 MB


def _parse_range_header(range_header: str, file_size: int) -> tuple[int, int] | None:
    """Parse a single HTTP bytes range, returning inclusive start/end."""
    if not range_header.startswith("bytes=") or "," in range_header:
        return None

    spec = range_header.removeprefix("bytes=").strip()
    if "-" not in spec:
        return None

    start_s, end_s = spec.split("-", 1)
    try:
        if start_s == "":
            suffix_len = int(end_s)
            if suffix_len <= 0:
                return None
            start = max(file_size - suffix_len, 0)
            end = file_size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else file_size - 1
    except ValueError:
        return None

    if start < 0 or start >= file_size or end < start:
        return None
    return start, min(end, file_size - 1)


@router.get("/{meeting_id}/recording")
def stream_recording(meeting_id: str, request: Request, db: Session = Depends(get_db)):
    """Stream the original recording file with HTTP Range support for video seeking."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    path = meeting.recording_path
    if not path or not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Recording file missing on disk")

    file_size = os.path.getsize(path)
    ext = os.path.splitext(path)[1].lower()
    mime = _MIME_TYPES.get(ext, "application/octet-stream")

    range_header = request.headers.get("range")
    if range_header:
        parsed = _parse_range_header(range_header, file_size)
        if parsed is None:
            raise HTTPException(
                status_code=416,
                detail="Invalid Range header",
                headers={"Content-Range": f"bytes */{file_size}"},
            )
        start, end = parsed
        length = end - start + 1

        def iter_range():
            with open(path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    data = f.read(min(_STREAM_CHUNK, remaining))
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            iter_range(),
            status_code=206,
            media_type=mime,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    def iter_full():
        with open(path, "rb") as f:
            while data := f.read(_STREAM_CHUNK):
                yield data

    return StreamingResponse(
        iter_full(),
        media_type=mime,
        headers={"Accept-Ranges": "bytes", "Content-Length": str(file_size)},
    )


@router.get("/{meeting_id}/frames/{frame_id}/image")
def get_frame_image(
    meeting_id: str,
    frame_id: str,
    db: Session = Depends(get_db),
):
    """Serve a single frame image."""
    frame = (
        db.query(VideoFrame)
        .filter(VideoFrame.id == frame_id, VideoFrame.meeting_id == meeting_id)
        .first()
    )
    if not frame or not os.path.exists(frame.frame_path):
        raise HTTPException(status_code=404, detail="Frame image not found")
    return FileResponse(frame.frame_path, media_type="image/jpeg")


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: str, db: Session = Depends(get_db)):
    """Delete a meeting and all associated data."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        delete_meeting_vectors(meeting_id)
    except Exception as e:
        logger.warning("Could not remove vectors for %s: %s", meeting_id, e)

    for path in (meeting.recording_path, meeting.audio_path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                logger.warning("Could not remove %s: %s", path, e)

    frames_dir = os.path.join(settings.frames_dir, meeting_id)
    if os.path.isdir(frames_dir):
        try:
            shutil.rmtree(frames_dir)
        except Exception as e:
            logger.warning("Could not remove frames dir %s: %s", frames_dir, e)

    db.delete(meeting)
    db.commit()
    return None


# ── Chat Endpoints ───────────────────────────────────────────────────────

_CHAT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_ALLOWED_CHAT_EXTENSIONS = {".json", ".txt", ".log", ".csv"}


@router.post("/{meeting_id}/chat", status_code=status.HTTP_201_CREATED)
async def upload_chat(
    meeting_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Attach a chat log (Slack JSON, Zoom/Teams export, or plain text) to a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in _ALLOWED_CHAT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported chat file type '{ext}'. Allowed: {sorted(_ALLOWED_CHAT_EXTENSIONS)}",
        )

    raw = await file.read(_CHAT_MAX_BYTES + 1)
    if len(raw) > _CHAT_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Chat file exceeds 10 MB limit")

    messages = chat_parser.parse_chat_file(raw, file.filename or "")
    if not messages:
        return {"inserted": 0, "message": "No messages parsed from file"}

    rows: list[ChatMessage] = []
    for msg in messages:
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        rows.append(ChatMessage(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            sender=msg.get("sender"),
            text=text,
            timestamp=msg.get("timestamp"),
            platform=msg.get("platform"),
        ))

    for row in rows:
        db.add(row)
    db.commit()
    logger.info("[%s] Inserted %d chat messages.", meeting_id, len(rows))

    # Embed and index in Qdrant alongside transcript segments
    texts = [row.text for row in rows]
    try:
        vectors = embedder.embed_texts(texts)
        points = []
        for row, vec in zip(rows, vectors):
            if not vec:
                continue
            points.append({
                "id": row.id,
                "vector": vec,
                "payload": {
                    "meeting_id": meeting_id,
                    "meeting_title": meeting.title,
                    "segment_id": row.id,
                    "speaker": row.sender or "Chat",
                    "start_time": row.timestamp,
                    "end_time": row.timestamp,
                    "text": row.text,
                    "source_type": "chat",
                },
            })
        if points:
            qdrant_service.upsert_transcript_segments(points)
            logger.info("[%s] Indexed %d chat messages in Qdrant.", meeting_id, len(points))
    except Exception as e:
        logger.warning("[%s] Chat embedding/indexing failed (messages saved): %s", meeting_id, e)

    return {"inserted": len(rows)}


@router.get("/{meeting_id}/chat", response_model=List[ChatMessageOut])
def get_chat(meeting_id: str, db: Session = Depends(get_db)):
    """Get all chat messages for a meeting, ordered by timestamp."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.meeting_id == meeting_id)
        .order_by(nulls_last(ChatMessage.timestamp), ChatMessage.created_at)
        .all()
    )
