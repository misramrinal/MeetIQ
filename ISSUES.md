# MeetMind — Known Issues & Improvement Backlog

_Audited: 2026-06-26. Issues found by static code review of the full backend._

---

## Severity Legend

| Level | Meaning |
|---|---|
| **High** | Produces wrong answers, silent data loss, or timeout bypass |
| **Medium** | Accuracy degradation, hard-to-debug failures, NaN/corrupt data |
| **Low** | Robustness, validation gaps, edge-case crashes |

---

## 1. RAG / Search Accuracy

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| R1 | `rag_service.py` | 132 | Evidence gate threshold (0.72) was tuned for raw cosine scores but is checked against post-RRF fused scores (typically 0.01–0.05). The gate almost never fires via the score branch — falling back entirely to keyword/term-overlap checks, so cosine relevance is not actually enforced. | High | **Fixed** (R2 fix makes keyword scores proportional; gate still correctly reads `.score` which is the pre-RRF original cosine score preserved by `reciprocal_rank_fusion`) |
| R2 | `rag_service.py` | 300 | Keyword hits are scored 0.95 regardless of how many query terms they match. A segment matching 1 of 5 terms scores the same as one matching all 5, making partial keyword hits dominate strong semantic matches and inflating confidence. | High | **Fixed** — score is now `min(0.85, 0.85 * coverage)`: 1-of-5 terms → 0.17, 5-of-5 → 0.85 |
| R3 | `rag_service.py` | 149, 161 | RRF dedup key falls back to `text[:120]`. Two different segments with the same opening phrase incorrectly collapse into one, and the same segment with/without an ID in different result lists won't deduplicate. | High | **Fixed** — replaced inline lambda with `_item_key()` covering `id`, `segment_id`, `source_id`, and full canonical text; second loop in `rerank_and_diversify` now tracks text-keyed items |
| R4 | `rag_service.py` | 91–96 | Intent detection (`_wants_decisions`, `_wants_actions`) runs before the non-search gate. A near-empty query like `"action"` bypasses the non-search check and triggers a structured DB lookup with real results. | High | **Fixed** — `_score` returns 0.0 (not 0.72) when `len(query_terms) < 2` and no content hits, so single-term intent queries yield no evidence |

---

## 2. Processing Pipeline

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| P1 | `processing_pipeline.py` | 54–66 | `_check_deadline()` is only called before transcription and knowledge extraction. Diarization, frame extraction, and OCR can silently blow past `PROCESSING_TIMEOUT_SECONDS`. | High | **Fixed** — added deadline checks before speaker alignment, before knowledge extraction & indexing, before video frame processing, and inside `_process_video_frames` before OCR |
| P2 | `frame_extractor.py` | 133 | `int(timestamp)` truncation causes filename collisions: `t=132.0` and `t=132.9` both produce `frame_000132.jpg`. Second frame silently overwrites the first. | High | **Fixed** — filename now uses millisecond precision: `frame_{round(timestamp*1000):09d}ms.jpg` |
| P3 | `ocr_service.py` | 29, 79–80 | `_ocr_disabled = True` is set as a global after any single OCR timeout. OCR is permanently disabled for all subsequent meetings in the process lifetime with no way to re-enable short of restarting. | High | **Fixed** — replaced global bool with `_consecutive_timeouts` counter; OCR is suspended only after 3 consecutive timeouts; a successful run resets the counter |
| P4 | `processing_pipeline.py` | 208–210 | Frame extraction exceptions are caught and logged but processing continues. Meeting is marked `done` even when video indexing never ran. No user-visible signal. | High | **Fixed** — `_append_warning()` helper writes non-fatal warnings to `meeting.error_message` so frame/OCR failures are visible in the API response without failing the whole job |

---

## 3. Knowledge Extraction

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| K1 | `knowledge_extractor.py` | 102–120 | No overlap between transcript chunks. | Medium | **Fixed** — added 300-char overlap at chunk boundaries via `CHUNK_OVERLAP_CHARS` |
| K2 | `knowledge_extractor.py` | 178–182 | Naive concatenation of per-chunk summaries. | Medium | **Fixed** — `_consolidate_summaries()` does a second-pass LLM call for multi-chunk meetings; falls back to deduplicated join |
| K3 | `knowledge_extractor.py` | 172–176 | Inconsistent entity name casing across chunks. | Medium | **Fixed** — names normalised to `title()` before dedup; display name is consistently title-cased |
| K4 | `knowledge_extractor.py` / `llm_client.py` | — | Silent empty dict on schema mismatch. | Medium | Open |

---

## 4. Speaker Alignment

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| S1 | `diarizer.py` | 126–155 | Tie-breaking on equal overlap is non-deterministic (depends on dict iteration order). Midpoint fallback is only used when `best_overlap == 0.0`, not when there's a tie at nonzero overlap. | Medium | **Fixed** — ties now broken by midpoint proximity, deterministically |
| S2 | `diarizer.py` | 150 | Segments with no overlapping speaker are silently labelled `"Speaker"` with no log warning. Can produce dozens of unlabelled segments in a transcript. | Medium | **Fixed** — unlabelled count is logged as a warning at the end of alignment |

---

## 5. Embedder / CLIP

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| E1 | `embedder.py` | 170–171 | `features / features.norm(dim=-1, keepdim=True)` produces `NaN` when norm == 0 (blank or near-blank images). NaN vectors stored in Qdrant corrupt all subsequent visual search results. | Medium | **Fixed** — norm clamped to `1e-8` before division; residual NaN/Inf vectors are dropped with a warning |
| E2 | `embedder.py` | 117–118 | Exception during batch encoding returns `[]` for the entire batch. Caller uses `zip(segments, vectors)` — trailing segments silently never get indexed. No length validation. | Medium | **Fixed** — `embed_texts` guarantees output length == input length; short results are padded with empty vectors and logged |

---

## 6. OCR Pipeline

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| O1 | `ocr_service.py` | 70–73 | Result parsing scans stdout for `"OCR_RESULT_JSON:"` prefix. If PaddleOCR prints any initialisation output to stdout before the result line, parsing silently returns no text. | Medium | Open |
| O2 | `ocr_service.py` | 67 | Subprocess stderr is truncated to 300 chars. Full stack traces from PaddleOCR failures are discarded, making diagnosis very difficult. | Low | Open |
| O3 | `ocr_service.py` | 29, 79–80 | Same as P3 above (global `_ocr_disabled` flag). Listed separately as it affects the OCR layer directly. | High | **Fixed** — see P3 |

---

## 7. LLM Client

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| L1 | `llm_client.py` | 35, 47 | Retry backoff has no jitter (`wait = 2 ** (attempt-1)` is deterministic). Under concurrent meeting processing, all retries fire at exactly the same moment, amplifying load spikes on Ollama. | Medium | **Fixed** — wait is now `base ** (attempt-1) × (0.7 + 0.6 × rand)`, giving ±30 % jitter |
| L2 | `llm_client.py` | 40 | `e.response.status_code` accessed before the `if e.response is not None` guard. If a network adapter wraps a connection error as `HTTPError` with `response=None`, this raises `AttributeError` inside the except block, masking the real error. | Medium | **Fixed** — `resp = e.response` extracted first; all attribute accesses guarded behind `if resp is not None` |

---

## 8. Data Model / Schemas

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| D1 | `models.py` | 57–99 | All four JSON properties (`participants`, `topics`, `unresolved`, `entities`) silently return `[]` on any parse error. A row written with corrupt JSON (e.g. partial write during crash) returns empty lists with no log or API signal. | Medium | Open |
| D2 | `models.py` | 141 | `ActionItem.status` is a free-text `String(50)` with no DB-level check constraint. Direct DB writes can store arbitrary strings that break the `?status=open` filter. | Low | Open |
| D3 | `models.py` | 90–99 | `entities` items have no shape validation. If the LLM returns `{"name": "Alice"}` without a `type` key, any code accessing `ent["type"]` will `KeyError`. | Medium | Open |

---

## 9. API Layer

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| A1 | `meetings.py` | 49–54 | File content is not validated, only extension. A `.mp4` file that is actually a zip archive passes the check; FFmpeg fails with a cryptic error surfaced as a generic 500. | Low | Open |
| A2 | `meetings.py` | — | Internal `error_message` (CUDA traces, file paths, model names) is stored verbatim and returned to clients via `GET /meetings/{id}/status`. Leaks implementation details. | Low | Open |
| A3 | `rag_service.py` | — | `top_k` is passed to Qdrant vector search but not consistently enforced on SQL keyword search or structured hits. A `top_k=3` request can return 10 sources. | Low | Open |
| A4 | `meetings.py` | 88–96 | `BackgroundTasks.add_task` starts a new thread per upload with no concurrency limit. 20 simultaneous uploads start 20 threads all loading Whisper + diarization + CLIP, likely causing OOM. | Medium | **Fixed** — `_pipeline_semaphore` (size 2) in `processing_pipeline.py` caps concurrent ML jobs; additional uploads queue safely |

---

## 10. Configuration

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| C1 | `config.py` | 38 | `LLM_PROVIDER` is a free-text string with no startup validation. An invalid value passes Pydantic validation; the app starts and crashes only on the first LLM call with a confusing message. | Low | Open |
| C2 | `config.py` | 128–134 | `resolve_whisper_compute_type()` referenced the module-level `settings` object which is defined **below** it — `NameError` if called during import. | Low | **Fixed** — now calls `get_settings()` instead |

---

## 11. Chat Parser

| # | File | Lines | Issue | Severity | Status |
|---|---|---|---|---|---|
| CP1 | `chat_parser.py` | 22/75 | `.csv` extension allowed by the upload endpoint but `parse_chat_file` had no CSV parser — fell through to line-based parsing, treating headers/rows as speaker messages and producing garbage. | Medium | **Fixed** — `_try_csv()` auto-detects timestamp/sender/text columns; falls back to line parser if columns not recognised |
| CP2 | `chat_parser.py` | 75 | `_try_slack_json` returned `None` when no messages parsed, but function annotation said `list[dict]`. Silent type violation. | Low | **Fixed** — annotation corrected to `list[dict] \| None`; caller behaviour unchanged |

---

## 12. Test Coverage Gaps

| # | File | Issue | Status |
|---|---|---|---|
| T1 | `test_logic_fixes.py` | Evidence gating not tested for multiple weak hits (e.g., two results at score 0.71) or spurious keyword hits. | Open |
| T2 | `test_logic_fixes.py` | No tests for OCR timeout, subprocess crash, malformed output, or the consecutive-timeout counter. | Open |

---

## Fix Priority Order (remaining open issues)

1. **K4** — Silent empty dict when LLM JSON doesn't match schema (knowledge loss)
2. **D1** — JSON columns silently return `[]` on parse error (data corruption invisible)
3. **D3** — `entities` items have no shape validation (`KeyError` on missing `type`)
4. **C1** — `LLM_PROVIDER` has no startup validation
5. **O1** — OCR stdout parsing breaks if PaddleOCR logs to stdout
6. **A1** — File content not validated, only extension
7. **A2** — Internal error details leaked in API responses
8. **A3** — `top_k` not consistently enforced across all retrieval paths
9. **T1 / T2** — Test coverage gaps
