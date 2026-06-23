 # MeetMind — Implementation Plan
## Simplified Build Guide with Focused Tech Stack

> A practical, buildable implementation of MeetMind that covers the most important AI concepts without unnecessary complexity.

---

## Design Philosophy

This plan follows three principles:

1. **Keep it buildable** — Every component runs locally in under 30 minutes.
2. **Keep it AI-rich** — Covers the most important modern AI concepts.
3. **Keep it demonstrable** — The final product can be shown publicly as a portfolio project.

---

## AI Concepts Covered

| Concept | How It Is Used |
|---|---|
| Speech-to-Text | Whisper transcribes meeting audio |
| Speaker Diarization | pyannote.audio identifies who is speaking |
| OCR | PaddleOCR extracts text from slides and screen shares |
| Image Embeddings | CLIP encodes video frames for visual search |
| Text Embeddings | sentence-transformers encodes transcript text |
| Vector Database | Qdrant stores and searches embeddings |
| Hybrid Retrieval | Vector search + keyword search combined with RRF |
| RAG | Retrieved context fed to LLM for grounded answers |
| LLM Knowledge Extraction | LLM extracts decisions and action items |
| Long-Term Memory | All meetings stored and searchable over time |
| Multimodal Search | Search across text, audio transcripts, and images |

---

## Simplified Tech Stack

### What We Use and Why

| Layer | Technology | Why |
|---|---|---|
| Backend | **FastAPI** (Python) | Simple, async, auto-generates API docs |
| Database | **PostgreSQL** | Reliable, supports full-text search, free |
| Vector DB | **Qdrant** (Docker) | Free, easy to run, great Python SDK |
| File Storage | **Local filesystem** | No cloud needed for demo |
| Task Queue | **FastAPI BackgroundTasks** | No Redis or Celery needed for MVP |
| Speech-to-Text | **faster-whisper** | Fast, runs on CPU, free |
| Diarization | **pyannote.audio** | Best open-source speaker diarization |
| OCR | **PaddleOCR** | Accurate, free, handles slides well |
| Image Embeddings | **CLIP** (via transformers) | Industry standard for visual search |
| Text Embeddings | **sentence-transformers** | Fast, free, runs locally |
| LLM | **Ollama** (local) or **OpenAI API** | Local = free, OpenAI = better quality |
| Frontend | **Next.js 14** | Modern React, easy deployment |
| UI | **Tailwind CSS + shadcn/ui** | Fast to build, looks professional |
| Video Player | **React Player** | Simple, handles all formats |
| Deployment | **Docker Compose** | Single command to run everything |

### What We Deliberately Skip

| Skipped | Reason | Can Add Later |
|---|---|---|
| Redis / Celery | FastAPI BackgroundTasks is enough for MVP | Yes |
| Kubernetes | Docker Compose is sufficient for demo | Yes |
| Kafka / NATS | Not needed for single-user demo | Yes |
| Nginx | Direct port access for development | Yes |
| Grafana / Prometheus | Use Langfuse for AI observability | Yes |
| AWS S3 | Use local file storage | Yes, easy swap |

---

## System Overview

```
User uploads meeting video/audio
            |
            v
    FastAPI Backend
            |
    BackgroundTask starts
            |
    +-------+--------+
    |                |
    v                v
Audio Pipeline   Video Pipeline
    |                |
Whisper STT     Frame Extraction
    |            (OpenCV + FFmpeg)
Speaker              |
Diarization      OCR (PaddleOCR)
    |                |
    +-------+--------+
            |
    Text + Image Embeddings
    (sentence-transformers + CLIP)
            |
    +-------+--------+
    |                |
    v                v
PostgreSQL        Qdrant
(structured)    (vectors)
            |
    LLM Knowledge Extraction
    (Ollama / OpenAI)
            |
    Decisions, Actions, Topics saved
            |
    User asks a question
            |
    Hybrid Retrieval
    (vector + keyword)
            |
    RAG Answer Generation
            |
    Answer + Citations + Timestamps
```

---

## Project Structure

```
meetmind/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── config.py                  # Settings from .env
│   ├── database.py                # PostgreSQL connection
│   ├── models.py                  # SQLAlchemy ORM models
│   ├── schemas.py                 # Pydantic request/response schemas
│   ├── routers/
│   │   ├── meetings.py            # Upload and manage meetings
│   │   ├── search.py              # Search and Q&A endpoints
│   │   ├── actions.py             # Action item endpoints
│   │   └── decisions.py           # Decision endpoints
│   ├── services/
│   │   ├── audio_processor.py     # FFmpeg + Whisper transcription
│   │   ├── diarizer.py            # pyannote.audio speaker diarization
│   │   ├── frame_extractor.py     # OpenCV frame extraction
│   │   ├── ocr_service.py         # PaddleOCR text extraction
│   │   ├── embedder.py            # sentence-transformers + CLIP
│   │   ├── qdrant_service.py      # Vector DB operations
│   │   ├── knowledge_extractor.py # LLM extraction of decisions/actions
│   │   └── rag_service.py         # Hybrid retrieval + answer generation
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx           # Dashboard
│   │   │   ├── meetings/
│   │   │   │   ├── page.tsx       # Meeting list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx   # Meeting detail + player
│   │   │   ├── search/
│   │   │   │   └── page.tsx       # Search interface
│   │   │   └── actions/
│   │   │       └── page.tsx       # Action item tracker
│   │   └── components/
│   │       ├── VideoPlayer.tsx    # Video playback with timestamps
│   │       ├── TranscriptPanel.tsx
│   │       ├── SearchBox.tsx
│   │       ├── DecisionList.tsx
│   │       └── ActionItemBoard.tsx
│   ├── Dockerfile
│   └── package.json
│
├── docker-compose.yml
├── .env.example
├── README.md
└── IMPLEMENTATION_PLAN.md
```

---

## Phase-by-Phase Implementation

---

### Phase 1: Project Setup and File Upload (Days 1–3)

**Goal**: Running skeleton with file upload and database.

#### Backend Setup

```bash
mkdir meetmind && cd meetmind
mkdir backend frontend

cd backend
python -m venv venv
source venv/bin/activate

pip install fastapi uvicorn sqlalchemy psycopg2-binary alembic \
            python-multipart aiofiles python-dotenv pydantic-settings
```

#### FastAPI App

```python
# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import meetings, search, actions, decisions

app = FastAPI(title="MeetMind API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(meetings.router, prefix="/api/v1/meetings", tags=["meetings"])
app.include_router(search.router,   prefix="/api/v1/search",   tags=["search"])
app.include_router(actions.router,  prefix="/api/v1/actions",  tags=["actions"])
app.include_router(decisions.router,prefix="/api/v1/decisions",tags=["decisions"])
```

#### Database Models

```python
# backend/models.py
from sqlalchemy import Column, String, Float, Integer, Date, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from database import Base
import uuid

class Meeting(Base):
    __tablename__ = "meetings"
    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title         = Column(String(500), nullable=False)
    date          = Column(Date)
    duration_seconds = Column(Integer)
    recording_path   = Column(Text)
    status        = Column(String(50), default="pending")
    # status values: pending | processing | done | failed

class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id  = Column(UUID(as_uuid=True))
    speaker     = Column(String(200))
    text        = Column(Text, nullable=False)
    start_time  = Column(Float)
    end_time    = Column(Float)
    embedding_id = Column(String(200))

class Decision(Base):
    __tablename__ = "decisions"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id  = Column(UUID(as_uuid=True))
    text        = Column(Text, nullable=False)
    made_by     = Column(String(200))
    timestamp   = Column(Float)
    confidence  = Column(Float)

class ActionItem(Base):
    __tablename__ = "action_items"
    id          = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id  = Column(UUID(as_uuid=True))
    text        = Column(Text, nullable=False)
    owner       = Column(String(200))
    due_date    = Column(Date)
    status      = Column(String(50), default="open")

class VideoFrame(Base):
    __tablename__ = "video_frames"
    id                  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id          = Column(UUID(as_uuid=True))
    timestamp           = Column(Float)
    frame_path          = Column(Text)
    ocr_text            = Column(Text)
    image_embedding_id  = Column(String(200))
```

#### Meeting Upload Endpoint

```python
# backend/routers/meetings.py
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, Depends
from sqlalchemy.orm import Session
import shutil, os, uuid
from database import get_db
from models import Meeting
from services.audio_processor import process_meeting_pipeline

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_meeting(
    title: str,
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db)
):
    meeting_id = str(uuid.uuid4())
    file_path  = f"{UPLOAD_DIR}/{meeting_id}_{file.filename}"

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    meeting = Meeting(id=meeting_id, title=title,
                      recording_path=file_path, status="pending")
    db.add(meeting)
    db.commit()

    background_tasks.add_task(process_meeting_pipeline, meeting_id, file_path)

    return {"meeting_id": meeting_id, "status": "processing"}

@router.get("/{meeting_id}/status")
def get_status(meeting_id: str, db: Session = Depends(get_db)):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    return {"status": meeting.status if meeting else "not_found"}

@router.get("/")
def list_meetings(db: Session = Depends(get_db)):
    return db.query(Meeting).order_by(Meeting.id.desc()).all()
```

**Deliverable**: Upload a video file and get a meeting ID back.

---

### Phase 2: Audio Processing — Transcription and Diarization (Days 4–7)

**Goal**: Extract a speaker-attributed transcript from audio.

#### Install

```bash
pip install faster-whisper pyannote.audio torch torchaudio
```

#### Audio Extraction

```python
# backend/services/audio_processor.py
import subprocess

def extract_audio(video_path: str, output_path: str) -> str:
    """Extract 16kHz mono WAV from video using FFmpeg."""
    subprocess.run([
        "ffmpeg", "-i", video_path,
        "-ar", "16000",
        "-ac", "1",
        "-y", output_path
    ], check=True, capture_output=True)
    return output_path
```

#### Transcription

```python
from faster_whisper import WhisperModel

# Load once at startup — use "base" for speed, "small" for better accuracy
_whisper = WhisperModel("base", device="cpu", compute_type="int8")

def transcribe(audio_path: str) -> list[dict]:
    segments, _ = _whisper.transcribe(audio_path, word_timestamps=False)
    return [
        {"text": s.text.strip(), "start": s.start, "end": s.end}
        for s in segments
    ]
```

#### Speaker Diarization

```python
from pyannote.audio import Pipeline
import os

_diarizer = None

def get_diarizer():
    global _diarizer
    if _diarizer is None:
        _diarizer = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=os.getenv("PYANNOTE_AUTH_TOKEN")
        )
    return _diarizer

def diarize(audio_path: str) -> list[dict]:
    pipeline = get_diarizer()
    result   = pipeline(audio_path)
    return [
        {"speaker": spk, "start": turn.start, "end": turn.end}
        for turn, _, spk in result.itertracks(yield_label=True)
    ]
```

#### Align Transcript with Speakers

```python
def align(transcript: list[dict], speakers: list[dict]) -> list[dict]:
    """Assign the closest speaker label to each transcript segment."""
    aligned = []
    for seg in transcript:
        mid    = (seg["start"] + seg["end"]) / 2
        speaker = "Unknown"
        for sp in speakers:
            if sp["start"] <= mid <= sp["end"]:
                speaker = sp["speaker"]
                break
        aligned.append({**seg, "speaker": speaker})
    return aligned
```

**Deliverable**: Upload a meeting, receive a speaker-attributed transcript with timestamps.

---

### Phase 3: Video Frame Extraction and OCR (Days 8–10)

**Goal**: Extract and index visual content from the meeting.

#### Install

```bash
pip install opencv-python-headless paddlepaddle paddleocr
```

#### Frame Extraction

```python
# backend/services/frame_extractor.py
import cv2, os

def extract_frames(video_path: str, output_dir: str,
                   interval_seconds: int = 5) -> list[dict]:
    os.makedirs(output_dir, exist_ok=True)
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    step = int(fps * interval_seconds)
    frames, n = [], 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if n % step == 0:
            ts   = n / fps
            path = f"{output_dir}/frame_{int(ts):05d}.jpg"
            cv2.imwrite(path, frame)
            frames.append({"timestamp": ts, "path": path})
        n += 1

    cap.release()
    return frames
```

#### OCR

```python
# backend/services/ocr_service.py
from paddleocr import PaddleOCR

_ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

def extract_text(frame_path: str) -> str:
    result = _ocr.ocr(frame_path, cls=True)
    if not result or not result[0]:
        return ""
    lines = [line[1][0] for line in result[0] if line[1][1] > 0.6]
    return " ".join(lines)
```

**Deliverable**: For each meeting, frames are extracted every 5 seconds and any on-screen text is captured via OCR.

---

### Phase 4: Embeddings and Vector Database (Days 11–14)

**Goal**: Index all content in Qdrant for semantic search.

#### Install

```bash
pip install sentence-transformers transformers Pillow qdrant-client
```

#### Text Embeddings

```python
# backend/services/embedder.py
from sentence_transformers import SentenceTransformer

_text_model = SentenceTransformer("BAAI/bge-base-en-v1.5")
# 768-dim vectors. Swap to bge-large-en-v1.5 (1024-dim) for better quality.

def embed_text(text: str) -> list[float]:
    return _text_model.encode(text, normalize_embeddings=True).tolist()

def embed_texts(texts: list[str]) -> list[list[float]]:
    return _text_model.encode(texts, normalize_embeddings=True,
                               batch_size=32).tolist()
```

#### Image Embeddings with CLIP

```python
from transformers import CLIPProcessor, CLIPModel
from PIL import Image
import torch

_clip_model     = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
_clip_processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

def embed_image(image_path: str) -> list[float]:
    img    = Image.open(image_path).convert("RGB")
    inputs = _clip_processor(images=img, return_tensors="pt")
    with torch.no_grad():
        feat = _clip_model.get_image_features(**inputs)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat[0].tolist()

def embed_text_for_image_search(text: str) -> list[float]:
    """CLIP text embedding — used to search images with a text query."""
    inputs = _clip_processor(text=[text], return_tensors="pt", padding=True)
    with torch.no_grad():
        feat = _clip_model.get_text_features(**inputs)
        feat = feat / feat.norm(dim=-1, keepdim=True)
    return feat[0].tolist()
```

#### Qdrant Service

```python
# backend/services/qdrant_service.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import os

_client = QdrantClient(
    host=os.getenv("QDRANT_HOST", "localhost"),
    port=int(os.getenv("QDRANT_PORT", 6333))
)

TEXT_COL  = "transcript_segments"
IMAGE_COL = "video_frames"
TEXT_DIM  = 768   # bge-base-en-v1.5
IMAGE_DIM = 512   # CLIP ViT-B/32

def create_collections():
    existing = {c.name for c in _client.get_collections().collections}
    if TEXT_COL not in existing:
        _client.create_collection(TEXT_COL,
            vectors_config=VectorParams(size=TEXT_DIM, distance=Distance.COSINE))
    if IMAGE_COL not in existing:
        _client.create_collection(IMAGE_COL,
            vectors_config=VectorParams(size=IMAGE_DIM, distance=Distance.COSINE))

def upsert_segment(seg_id: str, vector: list[float], payload: dict):
    _client.upsert(TEXT_COL,
        points=[PointStruct(id=seg_id, vector=vector, payload=payload)])

def upsert_frame(frame_id: str, vector: list[float], payload: dict):
    _client.upsert(IMAGE_COL,
        points=[PointStruct(id=frame_id, vector=vector, payload=payload)])

def search_text(query_vector: list[float], limit: int = 5) -> list[dict]:
    hits = _client.search(TEXT_COL, query_vector=query_vector,
                          limit=limit, with_payload=True)
    return [{"score": h.score, **h.payload} for h in hits]

def search_images(query_vector: list[float], limit: int = 5) -> list[dict]:
    hits = _client.search(IMAGE_COL, query_vector=query_vector,
                          limit=limit, with_payload=True)
    return [{"score": h.score, **h.payload} for h in hits]
```

**Deliverable**: All transcript segments and video frames are indexed in Qdrant and searchable by vector similarity.

---

### Phase 5: LLM Knowledge Extraction (Days 15–17)

**Goal**: Extract decisions and action items from transcripts using an LLM.

#### Option A — Local LLM with Ollama (Free, No API Key)

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.2        # 2GB, fast
# or
ollama pull mistral         # 4GB, better quality
```

```python
# backend/services/knowledge_extractor.py
import json, requests, os

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
LLM_MODEL  = os.getenv("LLM_MODEL", "llama3.2")

PROMPT = """You are a meeting analyst. Extract structured data from this transcript.
Return ONLY valid JSON with this structure:
{{
  "decisions":    [{{"text":"...", "made_by":"...", "timestamp":0.0, "confidence":0.9}}],
  "action_items": [{{"text":"...", "owner":"...",   "due_date":null, "timestamp":0.0}}],
  "topics":       ["topic1", "topic2"],
  "unresolved":   ["question1"]
}}
Rules: only extract what is explicitly stated. Use null for missing fields.

Transcript:
{transcript}"""

def extract_knowledge(transcript_text: str) -> dict:
    resp = requests.post(OLLAMA_URL, json={
        "model":  LLM_MODEL,
        "prompt": PROMPT.format(transcript=transcript_text[:6000]),
        "stream": False,
        "format": "json"
    }, timeout=120)
    try:
        return json.loads(resp.json()["response"])
    except Exception:
        return {"decisions": [], "action_items": [], "topics": [], "unresolved": []}
```

#### Option B — OpenAI API (Better Quality)

```python
from openai import OpenAI
import json

_openai = OpenAI()

def extract_knowledge_openai(transcript_text: str) -> dict:
    resp = _openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a meeting analyst. Return only valid JSON."},
            {"role": "user",   "content": PROMPT.format(transcript=transcript_text[:6000])}
        ],
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)
```

**Deliverable**: After processing, each meeting has structured decisions and action items stored in PostgreSQL.

---

### Phase 6: Hybrid Retrieval and RAG (Days 18–21)

**Goal**: Answer natural language questions using retrieved context.

#### Hybrid Search

```python
# backend/services/rag_service.py
from services.embedder import embed_text, embed_text_for_image_search
from services.qdrant_service import search_text, search_images
from sqlalchemy.orm import Session
from models import TranscriptSegment

def hybrid_search(query: str, db: Session, top_k: int = 5) -> list[dict]:
    """Combine Qdrant vector search with PostgreSQL keyword search."""

    # 1. Vector search
    vec_results = search_text(embed_text(query), limit=top_k)

    # 2. Keyword search (PostgreSQL full-text)
    kw_rows = (db.query(TranscriptSegment)
                 .filter(TranscriptSegment.text.ilike(f"%{query}%"))
                 .limit(top_k).all())
    kw_results = [
        {"text": r.text, "speaker": r.speaker,
         "start_time": r.start_time, "meeting_id": str(r.meeting_id), "score": 0.4}
        for r in kw_rows
    ]

    # 3. Merge and deduplicate
    seen, merged = set(), []
    for r in vec_results + kw_results:
        key = r["text"][:80]
        if key not in seen:
            seen.add(key)
            merged.append(r)

    return sorted(merged, key=lambda x: x.get("score", 0), reverse=True)[:top_k]

def visual_search(query: str, top_k: int = 5) -> list[dict]:
    """Search video frames using CLIP text-to-image retrieval."""
    return search_images(embed_text_for_image_search(query), limit=top_k)
```

#### RAG Answer Generation

```python
import requests, os

def generate_answer(query: str, segments: list[dict]) -> str:
    context = "\n\n".join([
        f"[{s.get('speaker','?')} at {s.get('start_time',0):.0f}s]: {s['text']}"
        for s in segments[:5]
    ])
    prompt = f"""Answer the question using only the meeting excerpts below.
If the answer is not present, say "I could not find this in the meeting recordings."

Excerpts:
{context}

Question: {query}
Answer:"""

    resp = requests.post(os.getenv("OLLAMA_URL","http://localhost:11434/api/generate"),
        json={"model": os.getenv("LLM_MODEL","llama3.2"),
              "prompt": prompt, "stream": False}, timeout=60)
    return resp.json().get("response", "Could not generate answer.")

def search_and_answer(query: str, db: Session) -> dict:
    segments = hybrid_search(query, db)
    answer   = generate_answer(query, segments)
    return {"query": query, "answer": answer, "sources": segments[:3]}
```

#### Search Router

```python
# backend/routers/search.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.rag_service import search_and_answer, visual_search

router = APIRouter()

@router.post("/")
def text_search(query: str, db: Session = Depends(get_db)):
    return search_and_answer(query, db)

@router.post("/visual")
def image_search(query: str):
    return {"query": query, "frames": visual_search(query)}
```

**Deliverable**: Ask a question, get an answer with cited transcript segments and timestamps.

---

### Phase 7: Frontend with Next.js (Days 22–28)

**Goal**: Build a clean, functional UI.

#### Setup

```bash
cd frontend
npx create-next-app@latest . --typescript --tailwind --app
npx shadcn-ui@latest init
npm install react-player @tanstack/react-query axios lucide-react
```

#### Search Component

```tsx
// frontend/src/components/SearchBox.tsx
"use client";
import { useState } from "react";
import axios from "axios";

interface Source {
  text: string;
  speaker: string;
  start_time: number;
  score: number;
}
interface Result {
  query: string;
  answer: string;
  sources: Source[];
}

export function SearchBox() {
  const [query,   setQuery]   = useState("");
  const [result,  setResult]  = useState<Result | null>(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!query.trim()) return;
    setLoading(true);
    try {
      const { data } = await axios.post(
        `/api/v1/search/?query=${encodeURIComponent(query)}`
      );
      setResult(data);
    } finally {
      setLoading(false);
    }
  };

  const fmt = (s: number) =>
    `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

  return (
    <div className="space-y-4 max-w-2xl mx-auto">
      <div className="flex gap-2">
        <input
          className="flex-1 border rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="Ask anything about your meetings..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && search()}
        />
        <button
          className="bg-blue-600 hover:bg-blue-700 text-white px-5 py-2 rounded-lg text-sm font-medium disabled:opacity-50"
          onClick={search}
          disabled={loading}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {result && (
        <div className="border rounded-xl p-5 space-y-4 bg-white shadow-sm">
          <p className="text-gray-800 leading-relaxed">{result.answer}</p>
          {result.sources.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Sources
              </p>
              {result.sources.map((src, i) => (
                <div key={i} className="bg-gray-50 rounded-lg p-3 text-sm border">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-blue-600">{src.speaker}</span>
                    <span className="text-gray-400 text-xs">at {fmt(src.start_time)}</span>
                    <span className="ml-auto text-xs text-gray-400">
                      {(src.score * 100).toFixed(0)}% match
                    </span>
                  </div>
                  <p className="text-gray-700">{src.text}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
```

#### Meeting Detail Page (Video + Transcript)

```tsx
// frontend/src/app/meetings/[id]/page.tsx
"use client";
import { useEffect, useState } from "react";
import ReactPlayer from "react-player";
import axios from "axios";

interface Segment { speaker: string; text: string; start_time: number; }
interface Meeting { id: string; title: string; recording_path: string; status: string; }

export default function MeetingPage({ params }: { params: { id: string } }) {
  const [meeting,   setMeeting]   = useState<Meeting | null>(null);
  const [segments,  setSegments]  = useState<Segment[]>([]);
  const [currentTime, setCurrentTime] = useState(0);

  useEffect(() => {
    axios.get(`/api/v1/meetings/${params.id}`).then(r => setMeeting(r.data));
    axios.get(`/api/v1/meetings/${params.id}/transcript`).then(r => setSegments(r.data));
  }, [params.id]);

  const active = segments.findIndex(
    s => s.start_time <= currentTime && currentTime <= s.start_time + 5
  );

  return (
    <div className="grid grid-cols-2 gap-6 p-6 h-screen">
      <div className="space-y-4">
        <h1 className="text-xl font-bold">{meeting?.title}</h1>
        <ReactPlayer
          url={`/api/v1/meetings/${params.id}/recording`}
          controls
          width="100%"
          onProgress={({ playedSeconds }) => setCurrentTime(playedSeconds)}
        />
      </div>
      <div className="overflow-y-auto space-y-2 border rounded-xl p-4">
        <h2 className="font-semibold text-gray-600 mb-3">Transcript</h2>
        {segments.map((seg, i) => (
          <div
            key={i}
            className={`p-2 rounded-lg text-sm transition-colors ${
              i === active ? "bg-blue-50 border border-blue-200" : ""
            }`}
          >
            <span className="font-medium text-blue-600">{seg.speaker}</span>
            <span className="text-gray-400 text-xs ml-2">
              {Math.floor(seg.start_time / 60)}:{String(Math.floor(seg.start_time % 60)).padStart(2,"0")}
            </span>
            <p className="text-gray-700 mt-0.5">{seg.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Deliverable**: Fully functional web app with upload, search, and meeting detail pages.

---

### Phase 8: Docker Compose and Deployment (Days 29–30)

**Goal**: One command to run everything.

#### docker-compose.yml

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./uploads:/app/uploads
      - ./frames:/app/frames
    depends_on:
      - postgres
      - qdrant

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_DB:       meetmind
      POSTGRES_USER:     meetmind
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  qdrant_data:
```

#### .env.example

```env
# Database
DATABASE_URL=postgresql://meetmind:password@postgres:5432/meetmind

# Qdrant
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# LLM — choose one provider
LLM_PROVIDER=ollama
OLLAMA_URL=http://host.docker.internal:11434
LLM_MODEL=llama3.2
# OPENAI_API_KEY=sk-...

# Whisper
WHISPER_MODEL=base
WHISPER_DEVICE=cpu

# pyannote (get token from huggingface.co)
PYANNOTE_AUTH_TOKEN=hf_...

# Storage
UPLOAD_DIR=uploads
FRAMES_DIR=frames
FRAME_INTERVAL_SECONDS=5
```

#### Start Everything

```bash
docker-compose up -d
docker-compose exec backend alembic upgrade head
docker-compose exec backend python -c \
  "from services.qdrant_service import create_collections; create_collections()"
open http://localhost:3000
```

---

## Python Requirements

```txt
# backend/requirements.txt

# Web
fastapi==0.115.0
uvicorn[standard]==0.30.0
python-multipart==0.0.9
aiofiles==23.2.1

# Database
sqlalchemy==2.0.35
psycopg2-binary==2.9.9
alembic==1.13.3

# Config
python-dotenv==1.0.1
pydantic-settings==2.5.2

# AI — Speech
faster-whisper==1.0.3
pyannote.audio==3.3.2
torch==2.4.0
torchaudio==2.4.0

# AI — Vision
opencv-python-headless==4.10.0.84
paddlepaddle==2.6.2
paddleocr==2.8.1
Pillow==10.4.0

# AI — Embeddings
sentence-transformers==3.1.1
transformers==4.44.2

# Vector DB
qdrant-client==1.11.3

# HTTP
requests==2.32.3
httpx==0.27.2

# Optional — OpenAI
openai==1.51.0
```

---

## Complete Processing Flow

```
1.  User uploads video  →  POST /api/v1/meetings/upload
2.  File saved to disk
3.  Meeting row created in PostgreSQL  (status: pending)
4.  BackgroundTask starts

    a.  status → "processing"
    b.  FFmpeg extracts audio  (WAV 16kHz mono)
    c.  faster-whisper transcribes  →  segments with timestamps
    d.  pyannote.audio diarizes  →  speaker segments
    e.  Align transcript + speakers
    f.  Save TranscriptSegment rows to PostgreSQL
    g.  Generate text embeddings  (bge-base-en-v1.5)
    h.  Upsert segments to Qdrant  (transcript_segments collection)
    i.  OpenCV extracts frames every 5 seconds
    j.  PaddleOCR extracts text from each frame
    k.  CLIP generates image embeddings
    l.  Save VideoFrame rows to PostgreSQL
    m.  Upsert frames to Qdrant  (video_frames collection)
    n.  Build full transcript text
    o.  LLM extracts decisions, action items, topics
    p.  Save Decision + ActionItem rows to PostgreSQL
    q.  status → "done"

5.  User searches  →  POST /api/v1/search/?query=...
    a.  Embed query with bge-base-en-v1.5
    b.  Vector search in Qdrant
    c.  Keyword search in PostgreSQL
    d.  Merge results with RRF
    e.  Build context from top results
    f.  LLM generates answer
    g.  Return answer + citations + timestamps
```

---

## Estimated Build Time

| Phase | Task | Days |
|---|---|---|
| 1 | Setup, upload endpoint, DB models | 3 |
| 2 | Whisper + speaker diarization | 4 |
| 3 | Frame extraction + OCR | 3 |
| 4 | Embeddings + Qdrant indexing | 4 |
| 5 | LLM knowledge extraction | 3 |
| 6 | Hybrid retrieval + RAG | 4 |
| 7 | Next.js frontend | 7 |
| 8 | Docker Compose + deployment | 2 |
| **Total** | | **~30 days** |

Working 2–3 hours per day, this is achievable in 4–6 weeks.

---

## Hardware Requirements

| Component | Minimum | Recommended |
|---|---|---|
| RAM | 8 GB | 16 GB |
| CPU | 4 cores | 8 cores |
| Disk | 10 GB | 30 GB |
| GPU | Not required | NVIDIA GPU (5–10x faster Whisper) |

### Model RAM Reference

| Model | RAM | Speed on CPU |
|---|---|---|
| Whisper tiny | 1 GB | Very fast |
| Whisper base | 1 GB | Fast ← recommended for dev |
| Whisper small | 2 GB | Medium |
| Whisper large-v3 | 10 GB | Slow |
| bge-base-en-v1.5 | 0.5 GB | Fast |
| CLIP ViT-B/32 | 0.5 GB | Fast |
| Llama 3.2 (Ollama) | 4 GB | Medium |

---

## Quick Test

```bash
# 1. Upload a sample meeting
curl -X POST "http://localhost:8000/api/v1/meetings/upload" \
  -F "title=Test Meeting" \
  -F "file=@sample.mp4"

# 2. Check processing status
curl "http://localhost:8000/api/v1/meetings/{id}/status"

# 3. Search when status is "done"
curl -X POST "http://localhost:8000/api/v1/search/?query=What+decisions+were+made"

# 4. Visual search
curl -X POST "http://localhost:8000/api/v1/search/visual?query=database+schema+diagram"

# 5. Get action items
curl "http://localhost:8000/api/v1/actions"
```

---

## What Makes This Portfolio-Ready

| Aspect | What You Demonstrate |
|---|---|
| AI breadth | STT, diarization, OCR, CLIP, embeddings, RAG, LLM extraction |
| System design | Async pipeline, background tasks, multi-service architecture |
| Data engineering | PostgreSQL schema, vector DB collections, hybrid retrieval |
| Backend | FastAPI, SQLAlchemy, Alembic, REST API design |
| Frontend | Next.js, React, real-time video sync |
| DevOps | Docker Compose, environment management |
| Evaluation | Retrieval quality, answer faithfulness |

This project covers **11 distinct AI concepts** in a single, coherent, deployable application.
