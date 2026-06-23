"""Video frame extraction using OpenCV."""
from __future__ import annotations

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


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
    import cv2

    interval = interval_seconds or settings.frame_interval_seconds
    os.makedirs(output_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.warning("Could not open video: %s", video_path)
        return []

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if total_frames == 0:
        logger.info("No video frames found in %s (probably audio-only)", video_path)
        cap.release()
        return []

    step = max(1, int(fps * interval))
    logger.info("Extracting frames: fps=%.1f, total=%d, every %ds (step=%d)",
                fps, total_frames, interval, step)

    frames: list[dict] = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step == 0:
            timestamp = frame_idx / fps
            path = os.path.join(output_dir, f"frame_{int(timestamp):06d}.jpg")
            cv2.imwrite(path, frame)
            frames.append({"timestamp": timestamp, "path": path})
        frame_idx += 1

    cap.release()
    logger.info("Extracted %d frames to %s", len(frames), output_dir)
    return frames
