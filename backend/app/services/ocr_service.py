"""OCR using PaddleOCR, run in an isolated subprocess.

PaddlePaddle cannot safely share a process with PyTorch on this stack: loading
paddle after torch deadlocks under uvicorn, and loading it first breaks
torch/ctranslate2 native DLL loading ("WinError 127 ... shm.dll"). To avoid the
conflict entirely, all OCR runs in a short-lived subprocess that imports only
paddle. The subprocess processes every frame of a meeting in one invocation, so
paddle initializes just once per meeting.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_WORKER = Path(__file__).resolve().parents[2] / "scripts" / "ocr_worker.py"
# Generous ceiling: paddle init (~3s) + per-image OCR (~1s). Scales with frames.
_BASE_TIMEOUT_S = 120
_PER_IMAGE_TIMEOUT_S = 5

# Disable OCR only after this many consecutive timeouts, not on the first one.
# A single slow meeting (many frames, slow CPU) should not kill OCR for the
# entire process lifetime.  A success resets the counter.
_MAX_CONSECUTIVE_TIMEOUTS = 3
_consecutive_timeouts = 0


def warmup() -> None:
    """No-op: OCR is loaded lazily inside its subprocess (kept for API symmetry)."""
    return


def extract_text_batch(image_paths: list[str]) -> dict[str, str]:
    """Run OCR on many images in a single isolated paddle subprocess.

    Returns a mapping of image_path -> extracted text. On any failure, returns
    empty strings for all paths (OCR degrades gracefully).

    After _MAX_CONSECUTIVE_TIMEOUTS consecutive timeouts the subprocess is
    considered unreliable and OCR is skipped until a successful run resets the
    counter.  This avoids permanently disabling OCR process-wide after a single
    slow meeting (the original bug).
    """
    global _consecutive_timeouts
    empty = {p: "" for p in image_paths}
    if not settings.enable_ocr or not image_paths:
        return empty
    if _consecutive_timeouts >= _MAX_CONSECUTIVE_TIMEOUTS:
        logger.warning(
            "OCR skipped: %d consecutive timeouts. Will retry on next meeting.",
            _consecutive_timeouts,
        )
        return empty
    if not _WORKER.exists():
        logger.warning("OCR worker not found at %s; skipping OCR.", _WORKER)
        return empty

    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(image_paths, tmp)
            tmp_path = tmp.name

        timeout = _BASE_TIMEOUT_S + _PER_IMAGE_TIMEOUT_S * len(image_paths)
        proc = subprocess.run(
            [sys.executable, str(_WORKER), tmp_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            logger.warning("OCR subprocess exited %d: %s", proc.returncode, proc.stderr[-300:])
            return empty

        for line in proc.stdout.splitlines():
            if line.startswith("OCR_RESULT_JSON:"):
                data = json.loads(line[len("OCR_RESULT_JSON:"):])
                # The worker normalises keys to forward slashes; do the same on
                # the lookup side so backslash paths from os.path.join still hit.
                _consecutive_timeouts = 0
                return {p: data.get(p.replace("\\", "/"), "") for p in image_paths}

        logger.warning("OCR subprocess produced no result line.")
        return empty

    except subprocess.TimeoutExpired:
        _consecutive_timeouts += 1
        remaining = _MAX_CONSECUTIVE_TIMEOUTS - _consecutive_timeouts
        if remaining > 0:
            logger.warning(
                "OCR subprocess timed out (%d/%d consecutive). "
                "%d more before OCR is suspended for this session.",
                _consecutive_timeouts, _MAX_CONSECUTIVE_TIMEOUTS, remaining,
            )
        else:
            logger.warning(
                "OCR subprocess timed out %d times consecutively; "
                "suspending OCR until a successful run resets the counter.",
                _consecutive_timeouts,
            )
        return empty
    except Exception as e:
        logger.warning("OCR subprocess failed: %s", e)
        return empty
    finally:
        if tmp_path:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def extract_text(image_path: str) -> str:
    """Run OCR on a single image (convenience wrapper around the batch path)."""
    return extract_text_batch([image_path]).get(image_path, "")
