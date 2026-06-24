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
import sys


def main() -> None:
    in_path = sys.argv[1]
    with open(in_path, "r", encoding="utf-8") as f:
        paths = json.load(f)

    from paddleocr import PaddleOCR

    ocr = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)

    out: dict[str, str] = {}
    for p in paths:
        try:
            result = ocr.ocr(p, cls=True)
            if result and result[0]:
                texts = [line[1][0] for line in result[0] if line[1][1] > 0.6]
                out[p] = " ".join(texts).strip()
            else:
                out[p] = ""
        except Exception:
            out[p] = ""

    sys.stdout.write("OCR_RESULT_JSON:" + json.dumps(out) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
