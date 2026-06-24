"""SQLAlchemy ORM models — SQLite compatible."""
from __future__ import annotations

import json
import uuid
from datetime import date, datetime

from sqlalchemy import Column, String, Float, Integer, Date, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    title = Column(String(500), nullable=False)
    date = Column(Date, default=date.today)
    duration_seconds = Column(Integer, nullable=True)
    recording_path = Column(Text, nullable=False)
    audio_path = Column(Text, nullable=True)
    status = Column(String(50), default="pending", index=True)
    # status: pending | processing | done | failed
    error_message = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    # JSON stored as text for SQLite compatibility
    _participants = Column("participants", Text, default="[]")
    _topics = Column("topics", Text, default="[]")
    _unresolved = Column("unresolved", Text, default="[]")
    _entities = Column("entities", Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)

    transcript_segments = relationship(
        "TranscriptSegment", back_populates="meeting", cascade="all, delete-orphan"
    )
    decisions = relationship(
        "Decision", back_populates="meeting", cascade="all, delete-orphan"
    )
    action_items = relationship(
        "ActionItem", back_populates="meeting", cascade="all, delete-orphan"
    )
    video_frames = relationship(
        "VideoFrame", back_populates="meeting", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="meeting", cascade="all, delete-orphan"
    )

    @property
    def participants(self):
        try:
            return json.loads(self._participants or "[]")
        except Exception:
            return []

    @participants.setter
    def participants(self, value):
        self._participants = json.dumps(value or [])

    @property
    def topics(self):
        try:
            return json.loads(self._topics or "[]")
        except Exception:
            return []

    @topics.setter
    def topics(self, value):
        self._topics = json.dumps(value or [])

    @property
    def unresolved(self):
        try:
            return json.loads(self._unresolved or "[]")
        except Exception:
            return []

    @unresolved.setter
    def unresolved(self, value):
        self._unresolved = json.dumps(value or [])

    @property
    def entities(self):
        try:
            return json.loads(self._entities or "[]")
        except Exception:
            return []

    @entities.setter
    def entities(self, value):
        self._entities = json.dumps(value or [])


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    speaker = Column(String(200), default="Speaker")
    text = Column(Text, nullable=False)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="transcript_segments")


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    text = Column(Text, nullable=False)
    made_by = Column(String(200), nullable=True)
    timestamp = Column(Float, nullable=True)
    confidence = Column(Float, default=0.0)
    context = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="decisions")


class ActionItem(Base):
    __tablename__ = "action_items"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    text = Column(Text, nullable=False)
    owner = Column(String(200), nullable=True, index=True)
    due_date = Column(Date, nullable=True)
    timestamp = Column(Float, nullable=True)
    status = Column(String(50), default="open", index=True)
    # status: open | in_progress | done | cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="action_items")


class VideoFrame(Base):
    __tablename__ = "video_frames"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    timestamp = Column(Float, nullable=False)
    frame_path = Column(Text, nullable=False)
    ocr_text = Column(Text, nullable=True)
    scene_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="video_frames")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=_new_uuid)
    meeting_id = Column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), index=True)
    sender = Column(String(200), nullable=True)
    text = Column(Text, nullable=False)
    timestamp = Column(Float, nullable=True)
    platform = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meeting = relationship("Meeting", back_populates="chat_messages")
