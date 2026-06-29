"""Standalone PaddleOCR worker, run as an isolated subprocess.

PaddlePaddle and PyTorch conflict over native OpenMP/CRT DLLs in a single
process (deadlocks or "WinError 127 shm.dll" on Windows). Running OCR in its
own process keeps paddle fully isolated from the torch-based models used by the
API server.

Protocol:
    argv[1] = path to a JSON file containing a list of image paths.
    stdout  = a single line "OCR_RESULT_JSON:<json>" mapping path -> text.
"""
import json
import os
import pathlib
import sys


def _find_model(base_dir: pathlib.Path, *candidates: str) -> str | None:
    """Return the first existing model directory among candidates."""
    for name in candidates:
        p = base_dir / name / name
        if (p / "inference.pdmodel").exists():
            return str(p)
    return None


def main() -> None:
    in_path = sys.argv[1]
    with open(in_path, "r", encoding="utf-8") as f:
        paths = json.load(f)

    # ── Locate pre-downloaded models ─────────────────────────────────────
    # PaddleOCR stores models in ~/.paddleocr/whl/{det,rec,cls}/<lang>/<name>/<name>/
    paddle_home = pathlib.Path.home() / ".paddleocr" / "whl"
    det_dir = paddle_home / "det" / "en"
    rec_dir = paddle_home / "rec" / "en"
    cls_dir = paddle_home / "cls"

    det_model = _find_model(det_dir, "en_PP-OCRv3_det_infer")
    rec_model = _find_model(rec_dir, "en_PP-OCRv4_rec_infer", "en_PP-OCRv3_rec_infer")
    cls_model = _find_model(cls_dir, "ch_ppocr_mobile_v2.0_cls_infer")

    # Build kwargs — only pass explicit paths when the models are present.
    # If a path is missing, PaddleOCR will try to download (which may fail on
    # corporate networks, but is better than crashing outright).
    kwargs: dict = {
        "use_angle_cls": True,
        "lang": "en",
        "show_log": False,
    }
    if det_model:
        kwargs["det_model_dir"] = det_model
    if rec_model:
        kwargs["rec_model_dir"] = rec_model
    if cls_model:
        kwargs["cls_model_dir"] = cls_model

    from paddleocr import PaddleOCR
    ocr = PaddleOCR(**kwargs)

    out: dict[str, str] = {}
    for p in paths:
        try:
            result = ocr.ocr(p, cls=True)
            if result and result[0]:
                texts = [line[1][0] for line in result[0] if line[1][1] > 0.5]
                out[p] = " ".join(texts).strip()
            else:
                out[p] = ""
        except Exception:
            out[p] = ""

    # Normalise all keys to forward slashes so the caller's path lookup succeeds
    # regardless of which slash style os.path.join used on the host OS.
    out_normalised = {k.replace("\\", "/"): v for k, v in out.items()}

    sys.stdout.write("OCR_RESULT_JSON:" + json.dumps(out_normalised) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
