"""Benchmark: sequential vs concurrent Whisper+pyannote on CPU.

Determines whether overlapping transcription and diarization actually helps on
this machine or whether they oversubscribe the cores and hurt each other.

Run from backend/:  ../.venv/Scripts/python.exe scripts/bench_concurrency.py [audio]
"""
from __future__ import annotations

import sys
import time
from concurrent.futures import ThreadPoolExecutor

from app.services import audio_processor, diarizer, gpu


def main(audio: str) -> None:
    # Prime GPU cuDNN before faster-whisper/CTranslate2 import (see app.services.gpu).
    gpu.prime_cuda()
    # Warm both models first so we measure compute, not load time.
    print("Warming models...", flush=True)
    audio_processor.warmup()
    diarizer.warmup()

    # Sequential
    t0 = time.perf_counter()
    segs, dur = audio_processor.transcribe(audio)
    t_trans = time.perf_counter() - t0
    t1 = time.perf_counter()
    sp = diarizer.diarize(audio)
    t_diar = time.perf_counter() - t1
    seq_total = t_trans + t_diar
    print(f"\nSEQUENTIAL: transcribe={t_trans:.1f}s  diarize={t_diar:.1f}s  total={seq_total:.1f}s",
          flush=True)

    # Concurrent (current pipeline behaviour)
    t2 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=1) as pool:
        fut = pool.submit(diarizer.diarize, audio)
        audio_processor.transcribe(audio)
        fut.result()
    conc_total = time.perf_counter() - t2
    print(f"CONCURRENT: total={conc_total:.1f}s", flush=True)

    print(f"\nAudio length: {dur:.0f}s | speakers={len(sp)}", flush=True)
    faster = "concurrent" if conc_total < seq_total else "sequential"
    print(f"WINNER: {faster}  (seq={seq_total:.1f}s vs conc={conc_total:.1f}s, "
          f"delta={abs(seq_total-conc_total):.1f}s)", flush=True)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../e2e_samples/_bench_120s.wav"
    main(path)
