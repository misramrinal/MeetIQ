"""Ad-hoc profiler: time each stage of the processing pipeline on a sample file.

Run from the backend dir:  ../.venv/Scripts/python.exe scripts/profile_pipeline.py <audio_path>
"""
from __future__ import annotations

import sys
import time
from contextlib import contextmanager

from app.services import audio_processor, diarizer, embedder, knowledge_extractor


@contextmanager
def timed(label: str):
    t0 = time.perf_counter()
    print(f"  -> {label} ...", flush=True)
    yield
    dt = time.perf_counter() - t0
    print(f"  [{dt:8.2f}s] {label}", flush=True)


def main(audio_in: str) -> None:
    out_wav = audio_in  # sample is already 16kHz mono WAV; skip ffmpeg

    print("=== COLD START (includes model loading) ===", flush=True)
    t_total = time.perf_counter()

    with timed("transcribe (whisper, incl. model load)"):
        segments, dur = audio_processor.transcribe(out_wav)
    print(f"        ({len(segments)} segments, {dur:.1f}s audio)", flush=True)

    with timed("diarize (pyannote, incl. model load)"):
        speakers = diarizer.diarize(out_wav)
    print(f"        ({len(speakers)} speaker turns)", flush=True)

    with timed("align_speakers"):
        aligned = diarizer.align_speakers(segments, speakers)

    with timed("embed_texts (sentence-transformers, incl. model load)"):
        texts = [s["text"] for s in aligned]
        vecs = embedder.embed_texts(texts)
    print(f"        ({len(vecs)} vectors)", flush=True)

    with timed("extract_knowledge (LLM)"):
        kn = knowledge_extractor.extract_knowledge([
            {"speaker": s.get("speaker"), "start_time": s["start"],
             "end_time": s["end"], "text": s["text"]}
            for s in aligned
        ])
    print(f"        (decisions={len(kn.get('decisions', []))}, "
          f"actions={len(kn.get('action_items', []))})", flush=True)

    print(f"\nTOTAL: {time.perf_counter() - t_total:.2f}s", flush=True)

    # Second pass: warm (models already loaded) to isolate per-request compute
    print("\n=== WARM (models already loaded) ===", flush=True)
    t_warm = time.perf_counter()
    with timed("transcribe"):
        audio_processor.transcribe(out_wav)
    with timed("diarize"):
        diarizer.diarize(out_wav)
    with timed("embed_texts"):
        embedder.embed_texts(texts)
    with timed("extract_knowledge (LLM)"):
        knowledge_extractor.extract_knowledge([
            {"speaker": s.get("speaker"), "start_time": s["start"],
             "end_time": s["end"], "text": s["text"]}
            for s in aligned
        ])
    print(f"\nWARM TOTAL: {time.perf_counter() - t_warm:.2f}s", flush=True)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../e2e_samples/sample_meeting.wav"
    main(path)
