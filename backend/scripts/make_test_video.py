"""Generate a short synthetic meeting video for end-to-end testing.

Creates text slides (so OCR has known, verifiable content) and muxes them with
the existing sample audio into an MP4 using ffmpeg.

Usage (from backend dir):
    ../.venv/Scripts/python.exe scripts/make_test_video.py
"""
from __future__ import annotations

import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

OUT_DIR = os.path.join("..", "e2e_samples")
AUDIO = os.path.join(OUT_DIR, "sample_meeting.wav")
VIDEO = os.path.join(OUT_DIR, "sample_meeting.mp4")

W, H = 1280, 720

# (title, body lines, duration_seconds) — timed loosely to the 4 audio segments.
SLIDES = [
    ("Database Decision", ["Decision: Use PostgreSQL", "as the primary database"], 4.8),
    ("Migration Plan", ["Owner: Bob", "Task: Prepare migration scripts"], 4.08),
    ("Deployment", ["Owner: Priya", "Task: Deploy staging environment"], 4.08),
    ("Open Question", ["Unresolved:", "Connection pooling strategy"], 3.6),
]


def _font(size: int):
    for path in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\arial.ttf"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def make_slide(idx: int, title: str, body: list[str]) -> str:
    img = Image.new("RGB", (W, H), (245, 245, 248))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, W, 120], fill=(30, 60, 120))
    draw.text((60, 35), title, font=_font(56), fill=(255, 255, 255))
    y = 240
    for line in body:
        draw.text((80, y), line, font=_font(48), fill=(20, 20, 20))
        y += 90
    path = os.path.join(OUT_DIR, f"_slide_{idx}.png")
    img.save(path)
    return path


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    if not os.path.exists(AUDIO):
        sys.exit(f"Audio not found: {AUDIO}")

    slide_paths = [make_slide(i, t, b) for i, (t, b, _) in enumerate(SLIDES)]

    concat_path = os.path.join(OUT_DIR, "_concat.txt")
    with open(concat_path, "w") as f:
        for path, (_, _, dur) in zip(slide_paths, SLIDES):
            name = os.path.basename(path)
            f.write(f"file '{name}'\n")
            f.write(f"duration {dur}\n")
        f.write(f"file '{os.path.basename(slide_paths[-1])}'\n")  # required by concat demuxer

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_path,
        "-i", AUDIO,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", "10",
        "-c:a", "aac", "-shortest",
        VIDEO,
    ]
    print("Running:", " ".join(cmd), flush=True)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-1500:])
        sys.exit("ffmpeg failed")

    # Cleanup intermediates
    for p in slide_paths + [concat_path]:
        try:
            os.remove(p)
        except OSError:
            pass

    size = os.path.getsize(VIDEO)
    print(f"Created {VIDEO} ({size} bytes)", flush=True)


if __name__ == "__main__":
    main()
