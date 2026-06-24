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

_ocr_disabled = False


def warmup() -> None:
    """No-op: OCR is loaded lazily inside its subprocess (kept for API symmetry)."""
    return


def extract_text_batch(image_paths: list[str]) -> dict[str, str]:
    """Run OCR on many images in a single isolated paddle subprocess.

    Returns a mapping of image_path -> extracted text. On any failure, returns
    empty strings for all paths (OCR degrades gracefully).
    """
    global _ocr_disabled
    empty = {p: "" for p in image_paths}
    if not settings.enable_ocr or _ocr_disabled or not image_paths:
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
                return {p: data.get(p, "") for p in image_paths}

        logger.warning("OCR subprocess produced no result line.")
        return empty

    except subprocess.TimeoutExpired:
        logger.warning("OCR subprocess timed out; disabling OCR for this run.")
        _ocr_disabled = True
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
