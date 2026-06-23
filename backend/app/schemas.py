"""Pydantic request/response schemas — SQLite compatible (string IDs)."""
from __future__ import annotations

from datetime import date as DateType, datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Common ───────────────────────────────────────────────────────────────

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Meeting ──────────────────────────────────────────────────────────────

class MeetingBase(BaseModel):
    title: str
    date: Optional[DateType] = None


class MeetingCreate(MeetingBase):
    pass


class MeetingOut(ORMModel):
    id: str
    title: str
    date: Optional[DateType]
    duration_seconds: Optional[int]
    status: str
    error_message: Optional[str] = None
    summary: Optional[str] = None
    participants: List[Any] = []
    topics: List[Any] = []
    unresolved: List[Any] = []
    entities: List[Any] = []
    created_at: datetime
    processed_at: Optional[datetime] = None


class MeetingStatusOut(BaseModel):
    meeting_id: str
    status: str
    error_message: Optional[str] = None


# ── Transcript ───────────────────────────────────────────────────────────

class TranscriptSegmentOut(ORMModel):
    id: str
    meeting_id: str
    speaker: str
    text: str
    start_time: float
    end_time: float
    confidence: Optional[float] = None


# ── Decision ─────────────────────────────────────────────────────────────

class DecisionOut(ORMModel):
    id: str
    meeting_id: str
    text: str
    made_by: Optional[str] = None
    timestamp: Optional[float] = None
    confidence: float = 0.0
    context: Optional[str] = None


# ── Action Item ──────────────────────────────────────────────────────────

class ActionItemOut(ORMModel):
    id: str
    meeting_id: str
    text: str
    owner: Optional[str] = None
    due_date: Optional[DateType] = None
    timestamp: Optional[float] = None
    status: str


class ActionItemUpdate(BaseModel):
    status: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[DateType] = None


# ── Video Frame ──────────────────────────────────────────────────────────

class VideoFrameOut(ORMModel):
    id: str
    meeting_id: str
    timestamp: float
    frame_path: str
    ocr_text: Optional[str] = None
    scene_type: Optional[str] = None


# ── Chat Message ─────────────────────────────────────────────────────────

class ChatMessageOut(ORMModel):
    id: str
    meeting_id: str
    sender: Optional[str] = None
    text: str
    timestamp: Optional[float] = None
    platform: Optional[str] = None


# ── Search ───────────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchSource(BaseModel):
    type: str
    meeting_id: Optional[str] = None
    meeting_title: Optional[str] = None
    speaker: Optional[str] = None
    text: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    frame_id: Optional[str] = None
    frame_path: Optional[str] = None
    timestamp: Optional[float] = None
    ocr_text: Optional[str] = None
    score: float


class SearchResponse(BaseModel):
    query: str
    answer: str
    sources: List[SearchSource]


class VisualSearchResponse(BaseModel):
    query: str
    frames: List[SearchSource]


# ── Upload ───────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    meeting_id: str
    status: str
    message: str = "Meeting uploaded and queued for processing."
