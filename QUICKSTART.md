   # MeetMind V1 — Quickstart Guide

This is the V1 implementation of MeetMind, a multimodal meeting intelligence platform.

It currently provides a **backend API**. Frontend will be added in V2.

---

## What V1 Does

You upload a meeting recording (audio or video). The backend:

1. Extracts audio with FFmpeg
2. Transcribes with **faster-whisper**
3. Identifies speakers with **pyannote.audio** (if HF token configured)
4. Extracts video frames every 5 seconds
5. Runs **PaddleOCR** on each frame to capture on-screen text
6. Generates **CLIP** image embeddings for visual search
7. Generates **sentence-transformers** text embeddings
8. Indexes everything in **Qdrant**
9. Calls the configured **LLM provider** to extract decisions, action items, topics, summary
10. Saves all structured data to **PostgreSQL**

You can then:

- **Ask natural-language questions** — hybrid (vector + keyword) retrieval + RAG answer
- **Visual search** — find frames matching a text description via CLIP
- **List action items / decisions** — filter by meeting, owner, status
- **Stream the recording** — for any meeting

---

## Setup

### Prerequisites

- Docker Desktop 4.x+ (with Compose v2)
- 8 GB RAM minimum, 16 GB recommended
- 10 GB free disk space
- Internet access to pull models on first run

### Steps

```bash
# 1. Enter the project directory
cd MeetMind

# 2. Copy environment file
cp .env.example .env
# Default uses local Ollama. For OpenAI, edit .env and set OPENAI_API_KEY.

# 3. Build and start everything
docker compose up -d --build

# 4. Watch the logs for the backend to finish starting
docker compose logs -f backend
```

First-time startup downloads models (Whisper, sentence-transformers, CLIP).
This takes 5–10 minutes depending on your bandwidth.

When you see something like:

```
INFO     uvicorn.error: Application startup complete.
```

the backend is ready.

---

## Service URLs

| Service | URL |
|---|---|
| Backend API | http://localhost:8000 |
| Swagger Docs | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health | http://localhost:8000/health |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| Postgres | localhost:5432 (user/pass: meetmind/meetmind) |

---

## Try It Out

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Should return:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_provider": "ollama",
  "llm_model": "llama3.2",
  "whisper_model": "base",
  "diarization_enabled": false
}
```

### 2. Upload a Meeting

```bash
curl -X POST "http://localhost:8000/api/v1/meetings/upload" \
  -F "title=My First Meeting" \
  -F "file=@/path/to/your/meeting.mp4"
```

Response:

```json
{
  "meeting_id": "c2f1c1a7-...",
  "status": "processing",
  "message": "Meeting uploaded and queued for processing."
}
```

### 3. Check Processing Status

```bash
curl http://localhost:8000/api/v1/meetings/<meeting_id>/status
```

Wait until `"status": "done"`.

You can also watch the backend logs to follow progress:

```bash
docker compose logs -f backend
```

Typical timings for a 5-minute audio recording:

| Stage | Time (CPU, base model) |
|---|---|
| Audio extraction | 5–10 s |
| Whisper transcription | 60–120 s |
| Frame extraction + OCR + CLIP | 30–60 s |
| LLM extraction | 10–30 s |
| **Total** | **2–4 minutes** |

### 4. Get the Transcript

```bash
curl http://localhost:8000/api/v1/meetings/<meeting_id>/transcript
```

### 5. List Decisions

```bash
curl "http://localhost:8000/api/v1/decisions/?meeting_id=<meeting_id>"
```

### 6. List Action Items

```bash
curl "http://localhost:8000/api/v1/actions/?meeting_id=<meeting_id>"
```

### 7. Ask a Question (Hybrid RAG)

```bash
curl -X POST "http://localhost:8000/api/v1/search/?query=What+did+we+decide+about+the+database"
```

Response:

```json
{
  "query": "What did we decide about the database",
  "answer": "The team decided to use PostgreSQL as the primary database...",
  "sources": [
    {
      "type": "transcript",
      "meeting_id": "...",
      "speaker": "Speaker 1",
      "text": "I think we should use PostgreSQL...",
      "start_time": 148.2,
      "score": 0.87
    }
  ]
}
```

### 8. Visual Search (CLIP Text-to-Image)

```bash
curl -X POST "http://localhost:8000/api/v1/search/visual?query=code+editor"
```

---

## Configuration

All settings live in `.env`. The most important ones for V1:

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` for local models, `openai` for hosted/OpenAI-compatible APIs |
| `LLM_MODEL_NAME` | `llama3.2` | Model name sent to the provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama URL for native runs; Docker Compose overrides this to `host.docker.internal` |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | OpenAI-compatible API base URL |
| `OPENAI_API_KEY` | (empty) | Required only when `LLM_PROVIDER=openai` |
| `WHISPER_MODEL` | `base` | Use `small` for better accuracy |
| `PYANNOTE_AUTH_TOKEN` | (empty) | Optional; enables speaker diarization |
| `FRAME_INTERVAL_SECONDS` | `5` | How often to extract frames |
| `ENABLE_FRAME_EXTRACTION` | `true` | Set `false` for audio-only speedup |
| `ENABLE_OCR` | `true` | Set `false` to skip OCR |

### Optional: Enable Speaker Diarization

By default, all transcript segments are labelled `"Speaker"`. To enable real speaker labels:

1. Accept the license at https://huggingface.co/pyannote/speaker-diarization-3.1
2. Create a token at https://huggingface.co/settings/tokens (read access is enough)
3. Set `PYANNOTE_AUTH_TOKEN=hf_xxxx` in `.env`
4. Restart: `docker compose restart backend`

### Switching the LLM Provider or Model

```env
# Local Ollama (default)
LLM_PROVIDER=ollama
LLM_MODEL_NAME=llama3.2
OLLAMA_BASE_URL=http://localhost:11434

# OpenAI or compatible hosted API
LLM_PROVIDER=openai
LLM_MODEL_NAME=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
```

Restart the backend after changing: `docker compose restart backend`

---

## Project Layout

```
MeetMind/
├── backend/
│   ├── app/
│   │   ├── main.py                       # FastAPI entry point
│   │   ├── config.py                     # Pydantic settings
│   │   ├── database.py                   # SQLAlchemy setup
│   │   ├── models.py                     # ORM models
│   │   ├── schemas.py                    # Pydantic schemas
│   │   ├── routers/
│   │   │   ├── meetings.py               # Upload, list, transcript, frames
│   │   │   ├── search.py                 # RAG + visual search
│   │   │   ├── actions.py                # Action items CRUD
│   │   │   └── decisions.py              # Decisions listing
│   │   └── services/
│   │       ├── llm_client.py             # Ollama / OpenAI-compatible LLM client
│   │       ├── audio_processor.py        # FFmpeg + faster-whisper
│   │       ├── diarizer.py               # pyannote.audio
│   │       ├── frame_extractor.py        # OpenCV
│   │       ├── ocr_service.py            # PaddleOCR
│   │       ├── embedder.py               # bge-base + CLIP
│   │       ├── qdrant_service.py         # Vector DB
│   │       ├── knowledge_extractor.py    # LLM → decisions/actions
│   │       ├── rag_service.py            # Hybrid retrieval + answer
│   │       └── processing_pipeline.py    # End-to-end orchestrator
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md                             # Full project doc
├── IMPLEMENTATION_PLAN.md                # Detailed implementation guide
└── QUICKSTART.md                         # This file
```

---

## Common Issues

### Backend container fails to start with model download errors

First start downloads several GB of models. Make sure you have:
- Disk space (at least 5 GB free)
- Internet access from inside the container

You can pre-download models on the host and mount them, but Docker volume
`meetmind_models` already caches them after the first run.

### "Database connection refused" on startup

The backend starts before Postgres is ready on slow machines. It will retry,
but if it gives up:

```bash
docker compose restart backend
```

### LLM provider returns 401 / 403

For `LLM_PROVIDER=openai`, check that `OPENAI_API_KEY` and `OPENAI_BASE_URL` are correct.
For `LLM_PROVIDER=ollama`, make sure Ollama is running on the host and that the model has been pulled.

### Frame extraction returns 0 frames

This is normal for audio-only files (.mp3, .wav). Audio files only get
transcription; visual search will be empty for them.

### Whisper is too slow

Switch to a smaller model:

```env
WHISPER_MODEL=tiny
```

Or, if you have an NVIDIA GPU on the host, use CUDA inside the container
(requires `nvidia-container-toolkit`). Update `.env`:

```env
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

and add GPU access to the `backend` service in `docker-compose.yml`.

---

## What's Next (V2)

Planned for V2:

- Next.js frontend with video player, transcript view, search UI
- Topic timeline and analytics dashboard
- WebSocket-based progress updates during processing
- Bulk upload / batch ingest
- User authentication (multi-tenant)
- Optional Slack/Teams integrations

---

## Stopping the Stack

```bash
docker compose down               # stop containers
docker compose down -v            # also remove all volumes (clean slate)
