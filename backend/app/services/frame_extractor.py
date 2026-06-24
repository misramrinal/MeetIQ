"""Video frame extraction.

Primary path uses FFmpeg's ``fps`` filter to decode the video in a single pass
and emit only the frames we keep — far cheaper than decoding every frame with
OpenCV. Falls back to an OpenCV ``grab()``-based reader if FFmpeg is missing or
fails, which still avoids the per-frame full decode + colour conversion of a
plain ``read()`` loop.
"""
from __future__ import annotations

import glob
import logging
import os
import subprocess

from app.config import settings

logger = logging.getLogger(__name__)

AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}


def extract_frames(
    video_path: str,
    output_dir: str,
    interval_seconds: int | None = None,
) -> list[dict]:
    """
    Extract frames from a video at regular intervals.

    Args:
        video_path: Path to the input video file.
        output_dir: Directory where frame JPEGs will be saved.
        interval_seconds: Seconds between extracted frames (default from settings).

    Returns:
        List of {"timestamp": float, "path": str} for each extracted frame.
        Returns an empty list if the file is audio-only or cannot be opened.
    """
    ext = os.path.splitext(video_path)[1].lower()
    if ext in AUDIO_EXTENSIONS:
        logger.info("Skipping frame extraction for audio-only file: %s", video_path)
        return []

    interval = interval_seconds or settings.frame_interval_seconds
    os.makedirs(output_dir, exist_ok=True)

    frames = _extract_frames_ffmpeg(video_path, output_dir, interval)
    if frames is not None:
        logger.info("Extracted %d frames (ffmpeg) to %s", len(frames), output_dir)
        return frames

    # FFmpeg unavailable or failed — fall back to OpenCV.
    return _extract_frames_opencv(video_path, output_dir, interval)


def _extract_frames_ffmpeg(
    video_path: str, output_dir: str, interval: int
) -> list[dict] | None:
    """Single-pass extraction with FFmpeg.

    Returns the frame list on success, or ``None`` if FFmpeg could not be used
    (so the caller can fall back). An empty list means "ran fine, no frames"
    (e.g. audio-only), which is a valid result and is NOT a fallback trigger.
    """
    pattern = os.path.join(output_dir, "frame_%06d.jpg")
    cmd = [
        "ffmpeg", "-nostdin", "-loglevel", "error",
        "-i", video_path,
        "-vf", f"fps=1/{interval}",
        "-q:v", "2",
        "-y", pattern,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        logger.info("ffmpeg not found on PATH; falling back to OpenCV frame extraction.")
        return None
    except Exception as e:
        logger.warning("ffmpeg frame extraction errored (%s); falling back to OpenCV.", e)
        return None

    if result.returncode != 0:
        logger.warning(
            "ffmpeg frame extraction failed (rc=%d): %s; falling back to OpenCV.",
            result.returncode, (result.stderr or "")[-300:],
        )
        return None

    produced = sorted(glob.glob(os.path.join(output_dir, "frame_*.jpg")))
    # ffmpeg's fps filter emits the first frame at ~t=0, then one every
    # `interval` seconds, so the i-th file (0-based) is at i*interval.
    return [
        {"timestamp": float(i * interval), "path": path}
        for i, path in enumerate(produced)
    ]


def _extract_frames_opencv(
    video_path: str, output_dir: str, interval: int
) -> list[dict]:
    """Fallback reader using OpenCV. Uses grab()+retrieve() so skipped frames
    are not fully decoded/converted, only the kept ones are written."""
    import cv2

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning("Could not open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames <= 0:
        logger.info("No video frames found in %s (probably audio-only)", video_path)
        cap.release()
        return []

    step = max(1, int(fps * interval))
    logger.info("Extracting frames (OpenCV): fps=%.1f, total=%d, every %ds (step=%d)",
                fps, total_frames, interval, step)

    frames: list[dict] = []
    frame_idx = 0
    while True:
        grabbed = cap.grab()
        if not grabbed:
            break
        if frame_idx % step == 0:
            ret, frame = cap.retrieve()
            if not ret:
                break
            timestamp = frame_idx / fps
            path = os.path.join(output_dir, f"frame_{int(timestamp):06d}.jpg")
            cv2.imwrite(path, frame)
            frames.append({"timestamp": timestamp, "path": path})
        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames (OpenCV) to %s", len(frames), output_dir)
    return frames
