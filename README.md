# MeetIQ 🧠
## Multimodal Meeting Intelligence and Organizational Memory Platform

> Transform every meeting into a searchable, queryable knowledge asset using AI-powered multimodal processing, real-time transcription, and long-term organizational memory.

---

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Use Cases](#use-cases)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Data Models](#data-models)
- [API Design](#api-design)
- [AI Pipeline Design](#ai-pipeline-design)
- [Database Schema](#database-schema)
- [Build Roadmap](#build-roadmap)
- [Demo Dataset](#demo-dataset)
- [Evaluation Metrics](#evaluation-metrics)
- [Deployment Guide](#deployment-guide)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Potential Challenges](#potential-challenges)
- [Possible Extensions](#possible-extensions)
- [Resume Value](#resume-value)

---

## Overview

**MeetIQ** is an advanced AI platform that processes live and recorded meetings across audio, video, screen shares, slides, and chat messages. It extracts structured knowledge — decisions, action items, topics, entities — and builds a searchable, queryable organizational memory.

Users can ask natural language questions across all past meetings and receive answers with video timestamp citations, speaker attribution, and visual evidence.

### AI Concepts Demonstrated

| Concept | Implementation |
|---|---|
| Multimodal RAG | Retrieval across text, audio, video frames, OCR |
| Long-Term Memory | Organizational meeting knowledge store |
| Speech-to-Text | Whisper-based transcription |
| Speaker Diarization | pyannote.audio |
| OCR | PaddleOCR on slides and screen shares |
| Image Embeddings | CLIP/SigLIP for visual search |
| Vector Databases | Qdrant for semantic retrieval |
| Hybrid Retrieval | Vector + BM25 keyword search |
| Knowledge Extraction | LLM-based decision and action item extraction |
| LLM Reasoning | GPT-4o / Claude for answer generation |

---

## Problem Statement

Organizations lose enormous amounts of knowledge every day because:

- Meetings are not recorded, or recordings are never watched.
- Transcripts exist but are not searchable or structured.
- Decisions made in meetings are not linked to documents or tickets.
- Action items are forgotten or scattered across tools.
- New employees cannot access historical meeting knowledge.
- The same questions are discussed repeatedly because no one remembers past decisions.
- Slides, screen shares, and whiteboards shown in meetings are never indexed.
- Important moments in long recordings are impossible to find quickly.

### Impact

- **Knowledge loss**: Critical decisions and context disappear after meetings end.
- **Repeated work**: Teams re-discuss solved problems because memory is fragmented.
- **Onboarding friction**: New employees spend weeks catching up on historical context.
- **Accountability gaps**: Action items are not tracked or attributed.
- **Search impossibility**: No way to find "that meeting where we discussed the database migration."

---

## Solution

MeetIQ solves this by:

1. **Processing** every meeting across all modalities: audio, video, slides, screen shares, and chat.
2. **Extracting** structured knowledge: decisions, action items, topics, entities, and unresolved questions.
3. **Indexing** everything in a multimodal vector store with timestamp alignment.
4. **Enabling** natural language search and question answering across all past meetings.
5. **Generating** meeting summaries and action item reports automatically.

---

## Key Features

### 1. Meeting Ingestion
- Upload video recordings (MP4, WebM, MOV)
- Upload audio recordings (MP3, WAV, M4A)
- Live meeting mode via microphone input
- Batch processing for large archives

### 2. Multimodal Processing Pipeline
- **Audio**: Whisper transcription with word-level timestamps
- **Speaker Diarization**: Identify and label each speaker
- **Video Frames**: Extract frames at configurable intervals
- **OCR**: Extract text from slides, whiteboards, and screens
- **Image Embeddings**: CLIP-based visual search indexing

### 3. Knowledge Extraction
- **Decisions**: "We decided to use PostgreSQL for the main database."
- **Action Items**: "Priya will update the API docs by Friday."
- **Topics**: Authentication, deployment, budget, roadmap.
- **Unresolved Questions**: "We still need to decide on the database."
- **Key Entities**: People, projects, tools, dates, technologies.

### 4. Multimodal Search and Retrieval
- Semantic text search over transcripts
- Visual search over video frames and slides
- Structured query over decisions and action items
- Cross-meeting topic aggregation
- Person-based search: "What did Alice say about deployment?"

### 5. Video Clip Navigation
- Jump to exact timestamp in recording
- Playable clip with context
- Synchronized transcript view
- Slide/screen shown at that moment

### 6. Organizational Memory Dashboard
- All meetings indexed and searchable
- Decision timeline across meetings
- Action item tracker with status
- Topic trend analysis
- Contributor activity view

### 7. Automated Meeting Summaries
- Executive summary
- Key decisions with attribution
- Action items with owners and deadlines
- Topics covered
- Unresolved questions

---

## Use Cases

### Use Case 1: Find a Decision
**Query**: "When did we decide to use PostgreSQL instead of MongoDB?"

**Output**:
```
Decision: Use PostgreSQL as the primary database.
Made by: Alice
Meeting: Q3 Product Planning — June 20, 2026
Timestamp: 2:28
[Play Clip]
```

### Use Case 2: Find a Moment in a Recording
**Query**: "Show me the part of the product demo where the checkout flow was shown."

**Output**:
```
Found in: Product Demo — June 15, 2026
Timestamp: 14:32
Speaker: Bob
OCR Text: "Checkout Flow v2 — Payment Integration"
[Play Clip]
```

### Use Case 3: Action Item Tracking
**Query**: "What action items are assigned to Priya in the last two weeks?"

**Output**:
```
1. Update API documentation — Sprint Review (June 18) — Due: June 25 — OPEN
2. Review security audit report — Security Review (June 17) — Due: June 20 — DONE
3. Deploy staging environment — DevOps Sync (June 16) — Due: June 19 — OPEN
```

### Use Case 4: Cross-Meeting Summary
**Query**: "Summarize all discussions about the API rate limiting feature."

**Output**:
```
API Rate Limiting was discussed in 4 meetings:

June 10 — Architecture Review:
  Decided to implement token bucket algorithm.

June 14 — Security Review:
  Raised concern about DDoS protection.

June 18 — Sprint Review:
  Bob completed rate limiter implementation.

June 20 — Q3 Planning:
  Discussed adding per-user rate limits in Q4.
```

### Use Case 5: New Employee Onboarding
**Query**: "What architectural decisions were made about the payment service in the last 6 months?"

A new engineer can query the entire meeting history to understand past decisions without watching hours of recordings.

### Use Case 6: Visual Search
**Query**: "Find all meetings where the database schema diagram was shown."

**Output**:
```
Found in 3 meetings:
1. Architecture Review — June 15 — Timestamp: 8:14
2. Database Migration Planning — June 5 — Timestamp: 22:41
3. Onboarding Session — May 28 — Timestamp: 45:10
```

---

## System Architecture

### High-Level Overview

```
+------------------------------------------------------------------+
|                        MeetIQ Platform                         |
+------------------+----------------------+------------------------+
|   Ingestion      |     Processing       |     Retrieval          |
|                  |                      |                        |
|  Video Upload    |  Whisper STT         |  Vector Search         |
|  Audio Upload    |  Speaker Diarization |  Keyword Search        |
|  Live Stream     |  Frame Extraction    |  Structured Query      |
|  Chat Import     |  OCR                 |  Hybrid Retrieval      |
|                  |  CLIP Embeddings     |  LLM Answer Gen        |
|                  |  Knowledge Extract   |  Citation Builder      |
+------------------+----------------------+------------------------+
```

### Detailed Data Flow

```
Ingestion Layer
    |
    +-- Video/Audio Upload -----> FFmpeg Processor
    +-- Live Mic Input ----------> Real-Time Stream
    +-- Chat Messages -----------> Message Parser
                                        |
                                        v
Processing Pipeline
    |
    +-- Whisper STT -----------------------> Transcript + Timestamps
    +-- pyannote.audio --------------------> Speaker Labels
    +-- OpenCV Frame Extractor ------------> Video Frames
    +-- PySceneDetect ---------------------> Scene Boundaries
    +-- PaddleOCR -------------------------> OCR Text from Frames
    +-- CLIP Encoder ----------------------> Image Embeddings
                                        |
                                        v
Knowledge Extraction
    |
    +-- LLM Extractor --------------------> Decisions
    +-- LLM Extractor --------------------> Action Items
    +-- LLM Extractor --------------------> Topics
    +-- LLM Extractor --------------------> Entities
    +-- LLM Extractor --------------------> Unresolved Questions
                                        |
                                        v
Indexing Layer
    |
    +-- Text Embeddings ------------------> Qdrant (text vectors)
    +-- Image Embeddings -----------------> Qdrant (image vectors)
    +-- Structured Data ------------------> PostgreSQL
    +-- Raw Files ------------------------> MinIO / S3
                                        |
                                        v
Retrieval Layer
    |
    +-- Query Router
    +-- Semantic Text Retrieval ----------> Qdrant
    +-- Visual Retrieval -----------------> Qdrant (image)
    +-- Structured Lookup ----------------> PostgreSQL
    +-- Context Builder ------------------> LLM Answer Generator
                                        |
                                        v
Response Layer
    |
    +-- Answer Text
    +-- Video Timestamp Citations
    +-- Speaker Attribution
    +-- Slide/Frame Thumbnails
    +-- Playable Clips
```

---

## Tech Stack

### Backend

| Component | Technology | Purpose |
|---|---|---|
| API Server | Python FastAPI | REST API and WebSocket |
| Background Jobs | Celery + Redis | Async processing |
| Task Queue | Redis | Job queue |
| Database | PostgreSQL | Structured data |
| Object Storage | MinIO / AWS S3 | Video, audio, frame files |
| Cache | Redis | Query cache |

### AI / ML

| Component | Technology | Purpose |
|---|---|---|
| Speech-to-Text | OpenAI Whisper / faster-whisper | Audio transcription |
| Speaker Diarization | pyannote.audio | Speaker identification |
| OCR | PaddleOCR | Text from slides/screens |
| Image Embeddings | CLIP / SigLIP | Visual search |
| Text Embeddings | bge-large-en / OpenAI text-embedding-3 | Semantic search |
| Knowledge Extraction | GPT-4o / Claude 3.5 / Llama 3 | Structured extraction |
| Answer Generation | GPT-4o / Claude 3.5 / Gemini | RAG answers |

### Retrieval

| Component | Technology | Purpose |
|---|---|---|
| Vector Database | Qdrant | Semantic vector search |
| Keyword Search | PostgreSQL FTS | BM25 keyword search |
| Hybrid Retrieval | Custom RRF fusion | Combine vector + keyword |
| Reranking | bge-reranker-large | Result reranking |

### Video Processing

| Component | Technology | Purpose |
|---|---|---|
| Video Decoding | FFmpeg | Video/audio extraction |
| Frame Extraction | OpenCV | Frame sampling |
| Scene Detection | PySceneDetect | Scene boundary detection |

### Frontend

| Component | Technology | Purpose |
|---|---|---|
| Framework | Next.js 14 | React-based frontend |
| UI Components | Tailwind CSS + shadcn/ui | Styling |
| Video Player | Video.js | Meeting playback |
| Charts | Recharts | Analytics |
| State Management | Zustand | Client state |
| API Client | TanStack Query | Data fetching |

### Infrastructure

| Component | Technology | Purpose |
|---|---|---|
| Containerization | Docker + Docker Compose | Local deployment |
| Reverse Proxy | Nginx | API gateway |
| Observability | OpenTelemetry + Langfuse | AI tracing |
| Monitoring | Prometheus + Grafana | System metrics |

---

## Data Models

### Meeting

```json
{
  "meeting_id": "mtg-001",
  "title": "Q3 Product Planning",
  "date": "2026-06-20",
  "duration_seconds": 3600,
  "participants": [
    { "name": "Alice", "speaker_id": "spk-0" },
    { "name": "Bob", "speaker_id": "spk-1" },
    { "name": "Priya", "speaker_id": "spk-2" }
  ],
  "recording_url": "s3://MeetIQ/recordings/mtg-001.mp4",
  "status": "processed",
  "tags": ["product", "planning", "q3"],
  "created_at": "2026-06-20T10:00:00Z",
  "processed_at": "2026-06-20T10:45:00Z"
}
```

### Transcript Segment

```json
{
  "segment_id": "seg-001",
  "meeting_id": "mtg-001",
  "speaker": "Alice",
  "speaker_id": "spk-0",
  "text": "I think we should use PostgreSQL for the main database.",
  "start_time": 142.5,
  "end_time": 148.2,
  "confidence": 0.96,
  "embedding_id": "emb-001"
}
```

### Decision

```json
{
  "decision_id": "dec-001",
  "meeting_id": "mtg-001",
  "text": "Use PostgreSQL as the primary database.",
  "made_by": "Alice",
  "timestamp": 148.2,
  "confidence": 0.92,
  "segment_ids": ["seg-001", "seg-002"],
  "context": "Discussed MongoDB vs PostgreSQL for 5 minutes before deciding."
}
```

### Action Item

```json
{
  "action_id": "act-001",
  "meeting_id": "mtg-001",
  "text": "Set up PostgreSQL schema and migrations.",
  "owner": "Bob",
  "due_date": "2026-06-27",
  "timestamp": 210.0,
  "status": "open",
  "segment_ids": ["seg-015"]
}
```

### Video Frame

```json
{
  "frame_id": "frm-001",
  "meeting_id": "mtg-001",
  "timestamp": 145.0,
  "frame_url": "s3://MeetIQ/frames/mtg-001/145.jpg",
  "ocr_text": "Database Architecture Options\n- PostgreSQL\n- MongoDB\n- DynamoDB",
  "scene_type": "slide",
  "image_embedding_id": "img-emb-001"
}
```

### Query Result

```json
{
  "query": "What database did we decide to use?",
  "answer": "The team decided to use PostgreSQL as the primary database.",
  "confidence": 0.92,
  "citations": [
    {
      "type": "transcript",
      "meeting_id": "mtg-001",
      "meeting_title": "Q3 Product Planning",
      "speaker": "Alice",
      "timestamp": 148.2,
      "text": "I think we should use PostgreSQL for the main database.",
      "clip_url": "s3://MeetIQ/clips/mtg-001-142-155.mp4"
    },
    {
      "type": "frame",
      "meeting_id": "mtg-001",
      "timestamp": 145.0,
      "frame_url": "s3://MeetIQ/frames/mtg-001/145.jpg",
      "ocr_text": "Database Architecture Options"
    }
  ]
}
```

---

## API Design

### Meetings Endpoints

```
POST   /api/v1/meetings/upload          Upload meeting recording
POST   /api/v1/meetings/live/start      Start live meeting session
POST   /api/v1/meetings/live/stop       Stop live meeting session
GET    /api/v1/meetings                 List all meetings
GET    /api/v1/meetings/{id}            Get meeting details
GET    /api/v1/meetings/{id}/status     Get processing status
DELETE /api/v1/meetings/{id}            Delete meeting
```

### Transcript Endpoints

```
GET    /api/v1/meetings/{id}/transcript         Full transcript
GET    /api/v1/meetings/{id}/transcript/search  Search within transcript
```

### Knowledge Endpoints

```
GET    /api/v1/meetings/{id}/decisions          Decisions from meeting
GET    /api/v1/meetings/{id}/actions            Action items from meeting
GET    /api/v1/meetings/{id}/topics             Topics from meeting
GET    /api/v1/meetings/{id}/summary            Auto-generated summary
GET    /api/v1/actions                          All action items
GET    /api/v1/actions?owner=Alice              Filter by owner
PATCH  /api/v1/actions/{id}                     Update action item status
```

### Search Endpoints

```
POST   /api/v1/search                   Natural language search
POST   /api/v1/search/visual            Visual/image search
POST   /api/v1/search/decisions         Search decisions
POST   /api/v1/search/actions           Search action items
```

### Frame Endpoints

```
GET    /api/v1/meetings/{id}/frames             All frames
GET    /api/v1/meetings/{id}/frames/{timestamp} Frame at timestamp
```

### Analytics Endpoints

```
GET    /api/v1/analytics/topics         Topic trends over time
GET    /api/v1/analytics/participants   Participant activity
GET    /api/v1/analytics/decisions      Decision timeline
GET    /api/v1/analytics/actions        Action item completion rates
```

---

## AI Pipeline Design

### Processing Pipeline Steps

```
Step 1: Audio Extraction
  Input:  Video file (MP4)
  Tool:   FFmpeg
  Output: Audio file (WAV, 16kHz mono)

Step 2: Transcription
  Input:  Audio file
  Tool:   faster-whisper (large-v3 model)
  Output: Transcript with word-level timestamps

Step 3: Speaker Diarization
  Input:  Audio file
  Tool:   pyannote.audio (speaker-diarization-3.1)
  Output: Speaker segments with timestamps

Step 4: Transcript Alignment
  Input:  Transcript + Speaker segments
  Process: Align words to speakers
  Output: Speaker-attributed transcript segments

Step 5: Frame Extraction
  Input:  Video file
  Tool:   OpenCV + PySceneDetect
  Output: Key frames at scene changes + every 5 seconds

Step 6: OCR
  Input:  Video frames
  Tool:   PaddleOCR
  Output: Text extracted from each frame

Step 7: Image Embedding
  Input:  Video frames
  Tool:   CLIP (ViT-L/14)
  Output: 768-dim image vectors

Step 8: Text Embedding
  Input:  Transcript segments + OCR text
  Tool:   bge-large-en-v1.5
  Output: 1024-dim text vectors

Step 9: Knowledge Extraction
  Input:  Full transcript
  Tool:   GPT-4o / Claude 3.5
  Output: Decisions, action items, topics, entities

Step 10: Indexing
  Input:  All embeddings and structured data
  Tool:   Qdrant + PostgreSQL
  Output: Searchable indexes
```

### Retrieval Pipeline Steps

```
Step 1: Query Analysis
  Input:  User query
  Process: Classify query type (text/visual/structured)
  Output: Query routing decision

Step 2: Query Embedding
  Input:  User query text
  Tool:   bge-large-en-v1.5
  Output: Query vector

Step 3: Parallel Retrieval
  Path A: Vector search in Qdrant (text)
  Path B: Vector search in Qdrant (images)
  Path C: BM25 keyword search in PostgreSQL
  Path D: Structured lookup in PostgreSQL

Step 4: Result Fusion
  Input:  Results from all paths
  Process: Reciprocal Rank Fusion (RRF)
  Output: Ranked combined results

Step 5: Reranking
  Input:  Top-K results
  Tool:   bge-reranker-large
  Output: Reranked results

Step 6: Context Building
  Input:  Top results
  Process: Format transcript segments, frames, decisions
  Output: Structured context for LLM

Step 7: Answer Generation
  Input:  Query + Context
  Tool:   GPT-4o / Claude 3.5
  Output: Answer with citations

Step 8: Citation Building
  Input:  Answer + Source segments
  Process: Link claims to timestamps and speakers
  Output: Final response with citations
```

### Knowledge Extraction Prompt

```
System:
You are an expert meeting analyst. Extract structured information
from meeting transcripts accurately and concisely.

Task:
Extract the following from the transcript provided:

1. DECISIONS: Explicit decisions made by the team.
   Include who made the decision and the timestamp.

2. ACTION_ITEMS: Tasks assigned to specific people.
   Include owner, deadline if mentioned, and timestamp.

3. TOPICS: Main topics discussed with time ranges.

4. UNRESOLVED: Questions or issues raised but not resolved.

5. ENTITIES: Key people, projects, tools, and technologies mentioned.

Rules:
- Only extract information explicitly stated in the transcript.
- Do not infer or assume anything not directly said.
- Include the timestamp of each extracted item.
- Assign confidence scores between 0.0 and 1.0.
- Output valid JSON only.
```

---

## Database Schema

### PostgreSQL Tables

```sql
-- Meetings
CREATE TABLE meetings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    date DATE NOT NULL,
    duration_seconds INTEGER,
    recording_url TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

-- Participants
CREATE TABLE participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    name VARCHAR(200),
    speaker_id VARCHAR(50),
    email VARCHAR(200)
);

-- Transcript Segments
CREATE TABLE transcript_segments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    speaker VARCHAR(200),
    speaker_id VARCHAR(50),
    text TEXT NOT NULL,
    start_time FLOAT NOT NULL,
    end_time FLOAT NOT NULL,
    confidence FLOAT,
    embedding_id VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decisions
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    made_by VARCHAR(200),
    timestamp FLOAT,
    confidence FLOAT,
    context TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Action Items
CREATE TABLE action_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    owner VARCHAR(200),
    due_date DATE,
    timestamp FLOAT,
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Video Frames
CREATE TABLE video_frames (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    timestamp FLOAT NOT NULL,
    frame_url TEXT,
    ocr_text TEXT,
    scene_type VARCHAR(50),
    image_embedding_id VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Topics
CREATE TABLE topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    start_time FLOAT,
    end_time FLOAT,
    summary TEXT
);

-- Full-text search indexes
CREATE INDEX idx_transcript_fts ON transcript_segments
    USING gin(to_tsvector('english', text));

CREATE INDEX idx_decisions_fts ON decisions
    USING gin(to_tsvector('english', text));

CREATE INDEX idx_meetings_date ON meetings(date DESC);
CREATE INDEX idx_actions_owner ON action_items(owner);
CREATE INDEX idx_actions_status ON action_items(status);
```

### Qdrant Collections

```
Collection: transcript_segments
  Vector size:  1024 (bge-large-en-v1.5)
  Distance:     Cosine
  Payload:
    - meeting_id      (string)
    - segment_id      (string)
    - speaker         (string)
    - start_time      (float)
    - end_time        (float)
    - text            (string)
    - meeting_title   (string)
    - meeting_date    (string)

Collection: video_frames
  Vector size:  768 (CLIP ViT-L/14)
  Distance:     Cosine
  Payload:
    - meeting_id      (string)
    - frame_id        (string)
    - timestamp       (float)
    - ocr_text        (string)
    - frame_url       (string)
    - scene_type      (string)

Collection: decisions
  Vector size:  1024 (bge-large-en-v1.5)
  Distance:     Cosine
  Payload:
    - meeting_id      (string)
    - decision_id     (string)
    - made_by         (string)
    - timestamp       (float)
    - text            (string)
```

---

## Build Roadmap

### Phase 1: Foundation (Week 1–2)

**Goal**: Basic meeting upload and transcription.

- [ ] Set up FastAPI project structure
- [ ] Set up PostgreSQL with Alembic migrations
- [ ] Set up MinIO for file storage
- [ ] Implement meeting upload endpoint
- [ ] Integrate FFmpeg for audio extraction
- [ ] Integrate faster-whisper for transcription
- [ ] Store transcript segments in PostgreSQL
- [ ] Basic REST API for meetings and transcripts
- [ ] Docker Compose setup

**Deliverable**: Upload a meeting recording and receive a full transcript.

---

### Phase 2: Speaker Diarization and Knowledge Extraction (Week 3–4)

**Goal**: Identify speakers and extract structured knowledge.

- [ ] Integrate pyannote.audio for speaker diarization
- [ ] Align transcript segments with speaker labels
- [ ] Implement LLM-based knowledge extractor
- [ ] Extract decisions, action items, and topics
- [ ] Store structured data in PostgreSQL
- [ ] Meeting summary generation endpoint
- [ ] Action item CRUD API

**Deliverable**: Upload a meeting and receive a speaker-attributed transcript with decisions and action items.

---

### Phase 3: Vector Search (Week 5–6)

**Goal**: Semantic search over transcripts.

- [ ] Set up Qdrant
- [ ] Generate text embeddings with bge-large-en-v1.5
- [ ] Index transcript segments in Qdrant
- [ ] Implement semantic search endpoint
- [ ] Implement BM25 keyword search via PostgreSQL FTS
- [ ] Implement hybrid retrieval with Reciprocal Rank Fusion
- [ ] Implement RAG answer generation
- [ ] Build citation linker

**Deliverable**: Ask a natural language question and receive an answer with transcript citations and timestamps.

---

### Phase 4: Multimodal Processing (Week 7–8)

**Goal**: Index and search video frames and slides.

- [ ] Integrate OpenCV for frame extraction
- [ ] Integrate PySceneDetect for scene boundary detection
- [ ] Integrate PaddleOCR for text extraction from frames
- [ ] Integrate CLIP for image embeddings
- [ ] Index frames in Qdrant image collection
- [ ] Implement visual search endpoint
- [ ] Cross-modal retrieval (text query returning image results)
- [ ] Frame thumbnail generation and storage

**Deliverable**: Ask a visual question and receive matching frames with thumbnails and timestamps.

---

### Phase 5: Frontend (Week 9–10)

**Goal**: Build the complete user interface.

- [ ] Set up Next.js 14 project
- [ ] Dashboard page with stats and recent meetings
- [ ] Meeting list page with filters and search
- [ ] Meeting upload page with progress tracking
- [ ] Meeting detail page with video player
- [ ] Synchronized transcript view with speaker labels
- [ ] Decisions and action items panels
- [ ] Global search interface with citations
- [ ] Action item tracker with status updates
- [ ] Decision timeline view

**Deliverable**: Fully functional web application.

---

### Phase 6: Analytics, Observability, and Polish (Week 11–12)

**Goal**: Analytics, observability, and production readiness.

- [ ] Topic trend analytics over time
- [ ] Participant activity dashboard
- [ ] Action item completion rate charts
- [ ] OpenTelemetry integration
- [ ] Langfuse for LLM call tracing
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboard setup
- [ ] Error handling and retry logic
- [ ] Rate limiting on API
- [ ] OpenAPI documentation
- [ ] Demo dataset creation and seeding script
- [ ] Public deployment

**Deliverable**: Production-ready demo with public URL and full observability.

---

## Demo Dataset

For a public portfolio demo, use synthetic meeting recordings.

### Meetings to Create

| Meeting | Duration | Key Content |
|---|---|---|
| Q3 Product Planning | 60 min | Feature decisions, tech stack choices, roadmap |
| Architecture Review | 45 min | System design diagrams, database selection |
| Sprint Review | 30 min | Completed tasks, live demos, blockers |
| Security Review | 40 min | Vulnerability discussions, auth decisions |
| Onboarding Session | 50 min | Company processes, tools, team structure |

### How to Generate Demo Data

1. Write realistic meeting scripts with natural dialogue.
2. Use text-to-speech (ElevenLabs or Coqui TTS) to generate multi-speaker audio.
3. Create slide decks in Google Slides or PowerPoint.
4. Record screen shares using OBS or QuickTime.
5. Combine audio and screen recording with FFmpeg.
6. Ensure each meeting contains decisions, action items, and visual content.

### Sample Script Excerpt

```
Meeting: Architecture Review — June 15, 2026
Participants: Alice (Tech Lead), Bob (Backend), Priya (DevOps)

[00:08:14] Alice shares screen — "Database Architecture Options" slide
[00:12:28] Alice: "After reviewing all options, I think we should go
           with PostgreSQL. It gives us ACID compliance and we already
           have team expertise with it."
[00:12:45] Bob: "Agreed. MongoDB would add unnecessary complexity for
           our relational data model."
[00:13:02] Priya: "I can set up the RDS instance. Should I target
           Friday for the staging environment?"
[00:13:15] Alice: "Yes, Friday works. Bob, can you have the schema
           migrations ready by Thursday?"
[00:13:22] Bob: "Sure, I'll have them done by Thursday EOD."
[00:22:41] Bob shares screen — database schema diagram visible
[00:44:20] Alice: "We still need to decide on connection pooling.
           PgBouncer or built-in pooling? Let's table that for next week."
```

---

## Evaluation Metrics

### Transcription Quality

| Metric | Target | Measurement Tool |
|---|---|---|
| Word Error Rate (WER) | < 10% | jiwer library |
| Speaker Accuracy | > 85% | Manual evaluation |
| Timestamp Accuracy | within ±0.5s | Manual evaluation |

### Knowledge Extraction Quality

| Metric | Target | Method |
|---|---|---|
| Decision Precision | > 80% | Human evaluation on test set |
| Decision Recall | > 75% | Human evaluation on test set |
| Action Item Precision | > 85% | Human evaluation on test set |
| Action Item Recall | > 80% | Human evaluation on test set |

### Retrieval Quality

| Metric | Target | Tool |
|---|---|---|
| Retrieval Precision@5 | > 70% | RAGAS |
| Answer Faithfulness | > 85% | RAGAS |
| Answer Relevance | > 80% | RAGAS |
| Context Recall | > 75% | RAGAS |

### System Performance

| Metric | Target |
|---|---|
| Processing time per minute of audio | < 30 seconds |
| Search query latency (p95) | < 2 seconds |
| Frame extraction throughput | > 10 fps |
| OCR throughput | > 5 frames/second |
| API response time (p95) | < 500ms |
| Concurrent meeting uploads supported | >= 5 |

---

## Deployment Guide

### Prerequisites

- Docker and Docker Compose installed
- 8 GB RAM minimum (16 GB recommended for Whisper large-v3)
- 20 GB disk space
- GPU optional but recommended for faster Whisper and CLIP inference

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/MeetIQ.git
cd MeetIQ

# Copy and configure environment variables
cp .env.example .env
# Edit .env and add your API keys

# Start all services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run database migrations
docker-compose exec backend alembic upgrade head

# Create Qdrant collections
docker-compose exec backend python scripts/setup_qdrant.py

# Seed demo data (optional)
docker-compose exec backend python scripts/seed_demo_data.py

# Access the application
open http://localhost:3000
```

### Service URLs

| Service | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Qdrant Dashboard | http://localhost:6333/dashboard |
| MinIO Console | http://localhost:9001 |
| Grafana | http://localhost:3001 |
| Prometheus | http://localhost:9090 |

### Docker Compose Configuration

```yaml
version: "3.9"

services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, redis, qdrant, minio]
    volumes:
      - ./backend:/app

  worker:
    build: ./backend
    command: celery -A app.workers worker --loglevel=info --concurrency=2
    env_file: .env
    depends_on: [redis, postgres, qdrant, minio]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    depends_on: [backend]

  postgres:
    image: postgres:16-alpine
    ports: ["5432:5432"]
    environment:
      POSTGRES_DB: MeetIQ
      POSTGRES_USER: MeetIQ
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes:
      - qdrant_data:/qdrant/storage

  minio:
    image: minio/minio:latest
    ports: ["9000:9000", "9001:9001"]
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: MeetIQ
      MINIO_ROOT_PASSWORD: password
    volumes:
      - minio_data:/data

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on: [backend, frontend]

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3001"]
    depends_on: [prometheus]

volumes:
  postgres_data:
  qdrant_data:
  minio_data:
```

### Production Deployment Options

| Platform | Description | Estimated Cost |
|---|---|---|
| Railway | Simple container deployment, easy setup | Free tier / ~$5/month |
| Render | Managed containers with free tier | Free tier / ~$7/month |
| Fly.io | Global edge deployment | Pay per use |
| AWS ECS + RDS | Production-grade managed services | ~$50–100/month |
| GKE / EKS | Full Kubernetes production scale | Variable |

---

## Project Structure

```
MeetIQ/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── meetings.py        # Meeting CRUD and upload
│   │   │       ├── search.py          # Search endpoints
│   │   │       ├── actions.py         # Action item endpoints
│   │   │       ├── decisions.py       # Decision endpoints
│   │   │       └── analytics.py       # Analytics endpoints
│   │   ├── core/
│   │   │   ├── config.py              # Settings and env vars
│   │   │   ├── database.py            # PostgreSQL connection
│   │   │   └── security.py            # Auth utilities
│   │   ├── models/
│   │   │   ├── meeting.py             # SQLAlchemy models
│   │   │   ├── transcript.py
│   │   │   ├── decision.py
│   │   │   ├── action_item.py
│   │   │   └── video_frame.py
│   │   ├── schemas/
│   │   │   ├── meeting.py             # Pydantic schemas
│   │   │   ├── search.py
│   │   │   └── knowledge.py
│   │   ├── services/
│   │   │   ├── transcription.py       # Whisper integration
│   │   │   ├── diarization.py         # pyannote.audio
│   │   │   ├── frame_extractor.py     # OpenCV + FFmpeg
│   │   │   ├── ocr.py                 # PaddleOCR
│   │   │   ├── embeddings.py          # bge-large + CLIP
│   │   │   ├── knowledge_extractor.py # LLM extraction
│   │   │   ├── retrieval.py           # Hybrid retrieval
│   │   │   └── answer_generator.py    # RAG answer gen
│   │   ├── workers/
│   │   │   ├── processing_worker.py   # Celery processing tasks
│   │   │   └── indexing_worker.py     # Celery indexing tasks
│   │   └── main.py                    # FastAPI app entry point
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── scripts/
│   │   ├── setup_qdrant.py            # Create Qdrant collections
│   │   └── seed_demo_data.py          # Load demo meetings
│   ├── tests/
│   │   ├── test_transcription.py
│   │   ├── test_retrieval.py
│   │   ├── test_extraction.py
│   │   └── test_api.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── page.tsx               # Dashboard
│   │   │   ├── layout.tsx
│   │   │   ├── meetings/
│   │   │   │   ├── page.tsx           # Meeting list
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx       # Meeting detail
│   │   │   ├── search/
│   │   │   │   └── page.tsx           # Global search
│   │   │   ├── actions/
│   │   │   │   └── page.tsx           # Action item tracker
│   │   │   └── analytics/
│   │   │       └── page.tsx           # Analytics dashboard
│   │   ├── components/
│   │   │   ├── VideoPlayer.tsx        # Video playback with timestamps
│   │   │   ├── TranscriptView.tsx     # Synchronized transcript
│   │   │   ├── SearchInterface.tsx    # Search bar and results
│   │   │   ├── DecisionCard.tsx       # Decision display
│   │   │   ├── ActionItemList.tsx     # Action item management
│   │   │   ├── FrameGallery.tsx       # Video frame thumbnails
│   │   │   ├── MeetingSummary.tsx     # Auto-generated summary
│   │   │   └── CitationCard.tsx       # Source citation display
│   │   └── lib/
│   │       ├── api.ts                 # API client
│   │       └── types.ts               # TypeScript types
│   ├── Dockerfile
│   └── package.json
│
├── nginx/
│   └── nginx.conf
├── prometheus/
│   └── prometheus.yml
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
├── README.md
└── docs/
    ├── architecture.md
    ├── api.md
    ├── deployment.md
    └── evaluation.md
```

---

## Environment Variables

```env
# ── Application ──────────────────────────────────────────────────
APP_ENV=development
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_ORIGINS=http://localhost:3000

# ── Database ─────────────────────────────────────────────────────
DATABASE_URL=postgresql://MeetIQ:password@postgres:5432/MeetIQ

# ── Redis ────────────────────────────────────────────────────────
REDIS_URL=redis://redis:6379/0

# ── Qdrant ───────────────────────────────────────────────────────
QDRANT_URL=http://qdrant:6333
QDRANT_API_KEY=

# ── Object Storage (MinIO / S3) ───────────────────────────────────
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=MeetIQ
MINIO_SECRET_KEY=password
MINIO_BUCKET=MeetIQ
MINIO_SECURE=false

# ── LLM Provider ─────────────────────────────────────────────────
LLM_PROVIDER=openai                  # openai | anthropic | ollama
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# ── Embeddings ───────────────────────────────────────────────────
TEXT_EMBEDDING_MODEL=BAAI/bge-large-en-v1.5
TEXT_EMBEDDING_DIMENSION=1024
IMAGE_EMBEDDING_MODEL=openai/clip-vit-large-patch14
IMAGE_EMBEDDING_DIMENSION=768

# ── Whisper ──────────────────────────────────────────────────────
WHISPER_MODEL=large-v3               # tiny | base | small | medium | large-v3
WHISPER_DEVICE=cpu                   # cpu | cuda
WHISPER_COMPUTE_TYPE=int8            # int8 | float16 | float32

# ── Speaker Diarization ──────────────────────────────────────────
PYANNOTE_AUTH_TOKEN=hf_...           # HuggingFace token for pyannote

# ── Processing ───────────────────────────────────────────────────
FRAME_EXTRACTION_INTERVAL_SECONDS=5
MAX_UPLOAD_SIZE_MB=500
PROCESSING_TIMEOUT_SECONDS=3600

# ── Observability ────────────────────────────────────────────────
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

---

## Potential Challenges and Mitigations

| Challenge | Impact | Mitigation Strategy |
|---|---|---|
| Transcription accuracy for accented speech | Medium | Use Whisper large-v3; allow manual transcript corrections |
| Speaker diarization errors | High | Provide speaker name mapping UI; allow corrections post-processing |
| OCR quality on low-resolution screens | Medium | Preprocess frames with contrast enhancement; use PaddleOCR |
| Large video file processing time | High | Async Celery workers with progress tracking; chunked processing |
| LLM hallucination in knowledge extraction | High | Validate extractions against transcript; show confidence scores |
| Vector search relevance for short queries | Medium | Hybrid retrieval with RRF; query expansion |
| Storage costs for extracted frames | Medium | Configurable frame sampling rate; compress thumbnails |
| Real-time transcription latency | Medium | Stream audio in chunks; use faster-whisper with VAD |
| Privacy of sensitive meeting content | High | Self-hosted deployment option; encryption at rest and in transit |
| Long meetings exceeding LLM context window | High | Chunked extraction with sliding window; map-reduce summarization |
| Multilingual meetings | Medium | Whisper multilingual model; language detection per segment |
| Speaker overlap and crosstalk | Medium | Confidence thresholds; flag overlapping segments for review |

---

## Possible Extensions

### Short-Term Extensions

- **Slack / Teams Integration**: Auto-import recordings from cloud storage links
- **Calendar Integration**: Link meetings to Google Calendar or Outlook events
- **Jira / Linear Integration**: Auto-create tickets from extracted action items
- **Email Summaries**: Send formatted meeting summaries to all participants
- **Multi-language Support**: Transcription and extraction in 10+ languages
- **Export Options**: Export summaries as PDF, Markdown, Notion, or Confluence pages

### Medium-Term Extensions

- **Live Meeting Mode**: Real-time transcription and extraction during active meetings via WebSocket
- **Meeting Templates**: Define structured agendas with custom extraction rules per meeting type
- **Sentiment Analysis**: Track team morale, engagement, and disagreement over time
- **Knowledge Graph**: Build an entity relationship graph connecting people, projects, and decisions
- **Conflict Detection**: Identify contradictory decisions made across different meetings
- **Meeting Quality Score**: Rate meeting effectiveness based on decision rate and action item clarity

### Research-Level Extensions

- **Automatic Topic Segmentation**: Detect topic boundaries using audio prosody and text signals
- **Argument Mining**: Extract claims, supporting evidence, and conclusions from discussions
- **Decision Outcome Tracking**: Link past decisions to their real-world outcomes in later meetings
- **Federated Meeting Memory**: Privacy-preserving cross-organization knowledge sharing
- **Multimodal Highlight Reels**: Auto-generate video summaries with the most important moments
- **Causal Decision Graph**: Map how decisions in one meeting caused outcomes discussed in later meetings

---

## Resume Value

### Skills Demonstrated

**AI Engineering**
- Multimodal RAG system design and end-to-end implementation
- Speech-to-text pipeline with word-level timestamp alignment
- Speaker diarization and transcript attribution
- OCR and image understanding at scale
- Cross-modal retrieval (text query returning image results)
- Hybrid retrieval with Reciprocal Rank Fusion
- LLM-based structured knowledge extraction with prompt engineering
- RAG answer generation with grounded citations

**Software Engineering**
- Distributed background job processing with Celery
- REST API design with FastAPI and OpenAPI documentation
- Relational database schema design with PostgreSQL
- Vector database design and collection management with Qdrant
- File storage and streaming with MinIO/S3
- Docker Compose multi-service orchestration
- Async processing pipelines with progress tracking

**ML Infrastructure**
- Embedding pipeline design for text and images
- Vector index management and optimization
- Model serving and inference optimization
- Evaluation framework using RAGAS
- AI observability with OpenTelemetry and Langfuse
- System performance benchmarking

### Resume Bullet Examples

**Concise version:**
> Built MeetIQ, a multimodal meeting intelligence platform using FastAPI, Whisper, pyannote.audio, CLIP, PaddleOCR, Qdrant, and Next.js that processes meeting recordings to extract speaker-attributed decisions and action items, indexes video frames and transcripts using hybrid vector/keyword retrieval, and enables natural language search across organizational meeting history with video timestamp citations.

**Metrics-focused version:**
> Developed a multimodal RAG platform that ingests meeting recordings, extracts speaker-attributed transcripts using faster-whisper and pyannote.audio, indexes video frames with CLIP image embeddings and PaddleOCR text extraction, and performs hybrid vector/BM25 retrieval over 50K+ synthetic segments to answer natural language queries with cited video timestamps, achieving >85% answer faithfulness on a RAGAS evaluation benchmark.

---

## License

MIT License

Copyright (c) 2026 MeetIQ

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
