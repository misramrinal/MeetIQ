# MeetMind — Project Status & Run Guide

_Last verified: 2026-06-26. This document reflects what is **actually working and tested**
on the current backend (not the aspirational design in `README.md`)._

---

## 1. What's Working

### Core pipeline (verified end-to-end)

Upload a meeting recording (audio **or** video) and the backend runs the full pipeline
and stores everything for search.

| Stage | Tool | Status |
|---|---|---|
| Audio extraction | FFmpeg | ✅ Working |
| Transcription | faster-whisper (`base`, int8 CPU / float16 GPU) | ✅ Working |
| Speaker diarization | pyannote.audio 3.1 | ✅ Working (real `Speaker 1/2/…` labels) |
| Transcript → speaker alignment | custom | ✅ Working |
| Text embeddings | `BAAI/bge-base-en-v1.5` | ✅ Working |
| Vector indexing | Qdrant | ✅ Working |
| Frame extraction (video) | OpenCV | ✅ Working (every 5s) |
| OCR on frames | PaddleOCR (**isolated subprocess**) | ✅ Working |
| Image embeddings | CLIP `clip-vit-base-patch32` | ✅ Working |
| Knowledge extraction | Ollama `llama3.2` (JSON mode) | ✅ Working (decisions, action items, topics, summary, entities) |
| Persistence | SQLite (`meetmind.db`) | ✅ Working |

### APIs (verified)

- **Upload & process**: `POST /api/v1/meetings/upload`
- **Status / list / detail**: `GET /api/v1/meetings/...`
- **Transcript**: `GET /api/v1/meetings/{id}/transcript`
- **Frames (with OCR text)**: `GET /api/v1/meetings/{id}/frames`
- **Frame image**: `GET /api/v1/meetings/{id}/frames/{frameId}/image`
- **RAG text search**: `POST /api/v1/search/?query=...` — hybrid vector + keyword +
  structured decision/action retrieval with an LLM-generated, cited answer
- **Visual search**: `POST /api/v1/search/visual?query=...` — CLIP text-to-image frame search
- **Decisions / Action items**: `GET /api/v1/decisions/`, `GET /api/v1/actions/`
- **Get single action item**: `GET /api/v1/actions/{id}`
- **Update action item**: `PATCH /api/v1/actions/{id}` — update `status`, `owner`, `due_date`
- **Recording streaming**: `GET /api/v1/meetings/{id}/recording` (HTTP range support)
- **Chat import**: `POST /api/v1/meetings/{id}/chat`
- **Get chat messages**: `GET /api/v1/meetings/{id}/chat`
- **Delete meeting**: `DELETE /api/v1/meetings/{id}` — removes DB rows, Qdrant vectors, and uploaded files

### Action item status lifecycle

`PATCH /api/v1/actions/{id}` accepts `status`, `owner`, and `due_date`. Valid statuses:

| Status | Meaning |
|---|---|
| `open` | Default; not yet started |
| `in_progress` | Being worked on |
| `done` | Completed |
| `cancelled` | Will not be done |

### Search behavior (verified)

Text search returns answer-quality metadata:

```json
{
  "query": "what did we decide about the database",
  "answer": "...",
  "status": "answered",
  "confidence": 0.893,
  "sources": []
}
```

`status` is one of:

| Status | Meaning |
|---|---|
| `answered` | Retrieval found enough evidence and the LLM generated an answer |
| `no_evidence` | Retrieval did not find strong enough evidence to answer |
| `non_search` | The input is conversational / too low-information (for example `hi`) |
| `llm_error` | Retrieval succeeded, but answer generation failed |

Important verified cases:

- `query=hi` returns `status: "non_search"` with no sources instead of searching random
  transcript snippets.
- `query=what decisions were made` returns `decision` sources from the structured
  decisions table.
- `query=what action items are assigned` returns `action_item` sources with owners,
  due dates when available, and item status.
- `query=what did we decide about the database` returns a normal RAG answer, now mixing
  structured decision sources with transcript evidence when useful.

**Intent detection**: queries containing words like `decision/decided` are routed to
the structured decisions table first; queries containing `action/task/todo/assigned/owner`
are routed to the structured action-items table first.

**Evidence gating**: vector-only results below cosine score 0.72 are rejected unless
a keyword hit or direct term overlap is also present, preventing unrelated nearest-neighbor
answers.

**Confidence scoring**: `confidence` is the highest source score plus a 0.08 bonus when
a structured decision or action-item source is present, capped at 1.0.

Search source types currently include `transcript`, `chat`, `decision`, `action_item`,
and `frame` (visual search).

### Knowledge stored per meeting

The LLM extracts the following from the transcript and stores each in the database:

| Field | Description |
|---|---|
| `summary` | One-paragraph meeting summary |
| `decisions` | Explicit decisions made, with `made_by`, `timestamp`, `confidence`, and `context` |
| `action_items` | Tasks assigned, with `owner`, `due_date`, `status` |
| `topics` | Key topics discussed (JSON list) |
| `unresolved` | Open questions or unresolved issues (JSON list) |
| `entities` | Named entities (PERSON, ORG, PRODUCT, TECHNOLOGY) with mention counts (JSON list) |
| `participants` | Distinct speaker labels found in the transcript |

Long transcripts are split into ~12 000-character chunks; the LLM is called once per
chunk and results are merged with deduplication.

### Processing stage tracking

The meeting `status` field progresses through:

`pending` → `processing` → `done` (or `failed`)

The `processing_stage` field provides finer-grained progress during the `processing`
state:

`audio_extracted` → `transcribed` → `aligning_speakers` → `saving_transcript` →
`indexing_and_extracting_knowledge` → `processing_video_frames` → `extracting_knowledge`
→ `saving_knowledge` → `complete`

`progress_percent` (0–100) is also updated cooperatively between pipeline stages.

### Chat import

`POST /api/v1/meetings/{id}/chat` accepts `.json`, `.txt`, `.log`, `.csv` files up to
10 MB. The parser auto-detects:

- **Slack JSON export** — `user` / `text` / `ts` fields
- **Zoom / Teams timestamp format** — `HH:MM:SS Speaker: text` lines
- **Generic plain text** — one message per line

Parsed messages are stored in the `chat_messages` table and immediately embedded in
Qdrant as `source_type: "chat"`, so they appear in RAG search results alongside
transcript segments.

### Frontend

- A Next.js 14 app exists in `frontend/` (dashboard, meeting views, search). Configured to
  call the API at `http://localhost:8000`. _Backend is the primary tested surface; run the
  frontend with the commands below._

### Verified sample results

Using `e2e_samples/sample_meeting.wav` (~16.5s) and `e2e_samples/sample_meeting.mp4`:
- Video meeting processes in **~27s** warm on GPU (dominated by fixed OCR + LLM costs on this
  tiny clip; the GPU win shows on longer recordings — see Performance Notes).
- OCR correctly reads slide text; RAG answers _"We decided to use PostgreSQL as the main
  database…"_; visual search ranks the matching slide first; diarization labels `Speaker 1`.
- Text search rejects greetings/low-information queries, includes `status` + `confidence`,
  and can answer directly from extracted decisions/action items.

---

## 2. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11 | A virtualenv already exists at `.venv` |
| FFmpeg | Must be on `PATH` (installed via WinGet at `%LOCALAPPDATA%\Microsoft\WinGet\Links`) |
| Qdrant | Running on `localhost:6333` (Docker image `qdrant/qdrant`, or standalone binary) |
| Ollama | Running on `localhost:11434` with the `llama3.2` model pulled |
| Node.js 18+ | Only needed for the frontend |
| NVIDIA GPU + CUDA PyTorch | **Optional but recommended** — ~6× faster audio processing. Install with `pip install torch==2.4.1+cu121 torchaudio==2.4.1+cu121 --index-url https://download.pytorch.org/whl/cu121`. Falls back to CPU automatically if absent. |

> **Database:** Defaults to SQLite (`meetmind.db` in the project root) — no setup required.
> `docker-compose.yml` uses PostgreSQL instead; switch via `DATABASE_URL` in `.env`.

> **Corporate networks:** If HuggingFace model downloads fail due to TLS inspection, set
> `MEETMIND_DISABLE_SSL_VERIFY=true` in `.env`. This patches ssl, urllib3, requests, httpx,
> and huggingface\_hub to skip certificate verification. Download models once to local
> `models/` paths and point `WHISPER_MODEL`, `TEXT_EMBEDDING_MODEL`, `CLIP_MODEL` at them.

---

## 3. Starting the Project

All commands are for **PowerShell on Windows**, run from the project root `c:\Ai_Proj\MeetMind_Mrinal\MeetMind`.

### Step 1 — Start the dependencies

```powershell
# Qdrant — Docker
docker start qdrant   # or: docker run -d --name qdrant -p 6333:6333 qdrant/qdrant

# Qdrant — standalone binary (if Docker is not available)
Start-Process 'C:\qdrant\qdrant.exe' -WorkingDirectory 'C:\qdrant' -WindowStyle Hidden

# Ollama (LLM) — make sure the model is available
ollama serve          # if not already running as a service
ollama pull llama3.2
```

Verify they're listening:

```powershell
Get-NetTCPConnection -State Listen | Where-Object { $_.LocalPort -in 6333,11434 } | Select-Object LocalPort
```

### Step 2 — Start the backend

FFmpeg must be on `PATH` for the same shell that launches uvicorn:

```powershell
$env:PATH = "$env:LOCALAPPDATA\Microsoft\WinGet\Links;" + $env:PATH
.\.venv\Scripts\python.exe -m uvicorn --app-dir backend app.main:app --host 127.0.0.1 --port 8000
```

On startup the server warms up the Whisper, embedding, diarization, and CLIP models in the
background (PaddleOCR is intentionally **not** loaded in-process — see Notes). Wait for:

```
INFO:     Application startup complete.
... app.main: Model warmup complete.
```

Check health:

```powershell
(Invoke-WebRequest http://localhost:8000/health -UseBasicParsing).Content
```

- API docs (Swagger): http://localhost:8000/docs
- Health: http://localhost:8000/health

### Step 3 — Start the frontend (optional)

```powershell
cd frontend
npm install        # first time only
npm run dev        # serves http://localhost:3000
```

---

## 4. Running / Testing It

### Upload and process a meeting

```powershell
$form = @{ title = "My Meeting"; file = Get-Item ".\e2e_samples\sample_meeting.mp4" }
$resp = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/meetings/upload" -Method Post -Form $form
$id = $resp.meeting_id
```

### Poll until done

```powershell
do {
  Start-Sleep -Seconds 1
  $s = Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id/status"
  "$($s.status) — $($s.processing_stage) ($($s.progress_percent)%)"
} while ($s.status -notin "done","failed")
```

### Inspect results

```powershell
# Transcript (with speaker labels)
Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id/transcript"

# Frames + OCR text (video only)
Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id/frames"

# LLM-extracted knowledge
$m = Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id"
$m.summary
$m.topics
$m.unresolved
$m.entities

# RAG question answering
$search = Invoke-RestMethod "http://localhost:8000/api/v1/search/?query=What did we decide about the database" -Method Post
$search.answer
$search.status
$search.confidence

# Structured decision/action search
(Invoke-RestMethod "http://localhost:8000/api/v1/search/?query=what decisions were made" -Method Post).sources
(Invoke-RestMethod "http://localhost:8000/api/v1/search/?query=what action items are assigned" -Method Post).sources

# Low-information input guard
Invoke-RestMethod "http://localhost:8000/api/v1/search/?query=hi" -Method Post

# Visual search (CLIP)
(Invoke-RestMethod "http://localhost:8000/api/v1/search/visual?query=database decision slide" -Method Post).frames

# Action items — list, filter by status or owner
Invoke-RestMethod "http://localhost:8000/api/v1/actions/?status=open"
Invoke-RestMethod "http://localhost:8000/api/v1/actions/?owner=Alice"

# Update an action item
Invoke-RestMethod "http://localhost:8000/api/v1/actions/$actionId" -Method Patch `
  -ContentType "application/json" -Body '{"status":"done"}'

# Delete a meeting (removes DB rows, vectors, and uploaded files)
Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id" -Method Delete

# Chat import
$chat = @{ file = Get-Item ".\slack_export.json" }
Invoke-RestMethod "http://localhost:8000/api/v1/meetings/$id/chat" -Method Post -Form $chat
```

### Regression tests

```powershell
$env:PYTHONPATH = "backend"
.\.venv\Scripts\python.exe -m unittest backend.tests.test_logic_fixes
.\.venv\Scripts\python.exe -m compileall -q backend\app backend\tests

cd frontend
.\node_modules\.bin\tsc.cmd --noEmit
```

Currently covered:
- greeting / low-information search does not enter RAG
- weak vector-only evidence does not trigger answer generation
- vector and SQL duplicates dedupe correctly via `segment_id`
- structured decisions/action items are returned as search sources
- HTTP byte range parsing handles normal, suffix, open-ended, and invalid ranges

### Helper scripts

- `backend/scripts/make_test_video.py` — regenerates the synthetic test video from the sample audio.
- `backend/scripts/profile_pipeline.py` — times each pipeline stage on a sample file.
- `backend/scripts/bench_concurrency.py` — compares sequential vs concurrent transcription +
  diarization (and shows the CPU-vs-GPU difference per stage).

---

## 5. Configuration (`.env`)

Key settings (see `.env` for the full list):

| Variable | Default | Purpose |
|---|---|---|
| `WHISPER_MODEL` | `base` | Transcription model size (`tiny`…`large-v3`) or a local path |
| `WHISPER_DEVICE` | `auto` | `auto` uses GPU when present (float16), else CPU (int8) |
| `DIARIZATION_DEVICE` | `auto` | `auto` runs pyannote on GPU when present |
| `EMBEDDING_DEVICE` | `cpu` | Text + CLIP embeddings device (keep `cpu` on small GPUs) |
| `ENABLE_DIARIZATION` | `true` | Speaker labels (GPU-accelerated; cheap on GPU) |
| `PYANNOTE_AUTH_TOKEN` | _(set)_ | HF token; gated models must be accepted on huggingface.co |
| `LLM_PROVIDER` | `ollama` | `ollama` or `openai` (any OpenAI-compatible endpoint) |
| `LLM_MODEL_NAME` | `llama3.2` | Model name passed to the provider |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | Base URL for OpenAI-compatible provider |
| `OPENAI_API_KEY` | _(set if needed)_ | API key for OpenAI-compatible provider |
| `TEXT_EMBEDDING_MODEL` | `BAAI/bge-base-en-v1.5` | HF model ID or local path |
| `CLIP_MODEL` | `openai/clip-vit-base-patch32` | HF model ID or local path |
| `ENABLE_FRAME_EXTRACTION` | `true` | Video frame processing |
| `ENABLE_OCR` | `true` | OCR on frames (runs in isolated subprocess) |
| `FRAME_INTERVAL_SECONDS` | `5` | Seconds between extracted frames |
| `MAX_UPLOAD_MB` | `2048` | Max upload size (enforced; HTTP 413 if exceeded) |
| `PROCESSING_TIMEOUT_SECONDS` | `7200` | Per-meeting wall-clock budget (enforced; `0` disables) |
| `DATABASE_URL` | `sqlite:///./meetmind.db` | Storage backend |
| `MEETMIND_DISABLE_SSL_VERIFY` | `false` | Set `true` on corporate networks with TLS inspection |

### LLM providers

Two providers are supported, selected via `LLM_PROVIDER`:

- **`ollama`** (default) — local Ollama server; no API key required. Set `OLLAMA_BASE_URL`
  if Ollama is not on `localhost:11434`.
- **`openai`** — OpenAI or any OpenAI-compatible `/chat/completions` endpoint. Set
  `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and optionally `OPENAI_SSL_VERIFY=false` for
  endpoints with self-signed certificates.

The LLM client retries up to **3 times** with exponential backoff (1 s, 2 s) on network
errors or HTTP 5xx responses.

### Limits

- **Upload size:** hard cap of **2 GB** (`MAX_UPLOAD_MB`). At typical meeting bitrates
  (~15 MB/min) that's roughly **2+ hours** of video; low-bitrate screen-share can be longer.
- **Processing budget:** **2 hours** (`PROCESSING_TIMEOUT_SECONDS`), enforced cooperatively
  between pipeline stages. Jobs that exceed it are marked `failed` with a clear message rather
  than running unbounded. On **GPU**, audio processing runs at roughly **8× real-time**
  (a 60-min audio meeting ≈ 7–9 min, mostly LLM extraction). On **CPU** (no GPU) it runs at
  roughly **0.5–0.8× real-time** with diarization enabled (a 60-min video ≈ 35–50 min). For
  long **videos**, per-frame OCR becomes the dominant cost regardless of device.
- **Chat file size:** hard cap of **10 MB** per upload (HTTP 413 if exceeded).

---

## 6. Performance Notes

The pipeline has been tuned for speed:
- **GPU acceleration (default when a CUDA GPU is present)** — Whisper and pyannote
  diarization run on the GPU. Same models, identical output, no accuracy loss.
- **Model warm-up at startup** — the first upload doesn't pay the model-load cost.
- **Whisper**: greedy decoding (`beam_size=1`) + VAD silence filtering. `float16` on GPU,
  `int8` + all CPU cores on CPU.
- **Batched CLIP** — video frames are embedded in batches (one forward pass per batch)
  instead of one-at-a-time.
- **Single-pass frame extraction** — FFmpeg's `fps` filter emits only the kept frames
  (OpenCV `grab()` fallback), instead of decoding every frame.
- **Ollama**: `keep_alive=30m` keeps the model resident between meetings; JSON-constrained output.
- **Parallelism**: transcription ∥ diarization, and embedding/indexing ∥ LLM extraction.
- **Result diversity**: RRF fusion caps results at 2 per meeting and 2 per identical text
  segment, preventing duplicate uploads from dominating search.

### Measured speedups (132 s audio clip)

| Stage | CPU | GPU (RTX 3050) | Speedup |
|---|---|---|---|
| Transcription (Whisper base) | 28.4 s | 10.0 s | 2.8× |
| Diarization (pyannote) | 90.6 s | 7.1 s | **12.8×** |
| **Audio total** | **~109 s** | **~17 s** | **~6.4×** |

Diarization was ~76% of CPU audio time and is the dominant win. On CPU, diarization was
the bottleneck (~0.7× real-time); on GPU it is ~18× real-time.

### Remaining bottlenecks
- **LLM knowledge-extraction** (~6–7 s/chunk on `llama3.2` CPU) — run Ollama on GPU or
  use a smaller model for more speed.
- **OCR on video frames** (PaddleOCR, ~1 s/frame in an isolated CPU subprocess) — for a
  long video this is now the largest video-only cost. Reduce by raising
  `FRAME_INTERVAL_SECONDS`, or set `ENABLE_OCR=false` if slide text isn't needed.

### GPU notes (4 GB VRAM)
- Whisper (`base`, float16) + pyannote share the GPU and fit within ~4 GB. Text/CLIP
  embeddings stay on CPU (`EMBEDDING_DEVICE=cpu`) to preserve headroom; set to `cuda`
  if you have a larger card.
- **cuDNN load order matters.** CTranslate2 (faster-whisper) and PyTorch both load native
  cuDNN. `app/services/gpu.py:prime_cuda()` initialises torch's cuDNN 9 at startup *before*
  CTranslate2 is imported, so they share one cuDNN. Without this, GPU runs crash with
  `Could not load symbol cudnnGetLibConfig`. Do **not** remove the `prime_cuda()` call from
  startup, and keep it before the first Whisper load.
- Everything degrades gracefully to CPU if CUDA/cuDNN is unavailable.

---

## 7. Important Notes / Known Constraints

- **OCR runs in a subprocess by design.** PaddlePaddle and PyTorch conflict over native
  OpenMP/CRT DLLs in one process on Windows (deadlock or `WinError 127 shm.dll`). OCR therefore
  runs in an isolated subprocess (`backend/scripts/ocr_worker.py`); paddle never loads inside
  the API server. Do **not** re-add PaddleOCR to the in-process startup warm-up.
- **FFmpeg on PATH** is required for the shell that launches the backend.
- **Diarization on a single-voice recording** correctly yields one speaker; multi-voice
  recordings produce `Speaker 1`, `Speaker 2`, etc.
- **Audio-only files** (`.wav`, `.mp3`, …) skip frame/OCR/CLIP steps automatically.
- To disable diarization for speed: set `ENABLE_DIARIZATION=false` and restart.
- **Graceful degradation.** Every ML model (Whisper, embeddings, CLIP, diarization, LLM)
  catches load failures and degrades gracefully: the pipeline continues with reduced
  functionality rather than crashing. A Whisper failure marks the meeting `failed`; embedding
  or CLIP failures disable the relevant search feature until the next restart.
- **Search ranking is still intentionally simple.** It combines structured rows,
  Qdrant vector hits, and SQL keyword hits with lightweight scoring/RRF. It now guards
  against obvious bad inputs and weak evidence, but it is not a full reranker.
- **Duplicate sample uploads can dominate search results.** The current local database has
  multiple copies of the sample PostgreSQL meeting, so repeated decision/action sources are
  expected until the database is cleaned or result diversity is added.
- **Recording streaming supports single byte ranges.** Normal, suffix, and open-ended ranges
  work; malformed or unsatisfiable ranges return HTTP 416. Multipart ranges are not implemented.
- **Meeting deletion is permanent.** `DELETE /api/v1/meetings/{id}` removes the DB record,
  all Qdrant vectors, the uploaded recording file, extracted audio, and the frames directory.
  There is no soft-delete or recovery.
- **Python 3.11 required.** The pinned dependency set (`torch==2.4.1`, `torchaudio==2.4.1`,
  `paddlepaddle==2.6.2`) has wheels for Python 3.11 only. Python 3.12+ breaks
  `torchaudio.AudioMetaData` (diarization) and `paddlepaddle==2.6.2` (OCR).
