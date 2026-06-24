"""GPU initialisation helpers.

CTranslate2 (pulled in by faster-whisper) and PyTorch both load native cuDNN
libraries. If CTranslate2 is imported first it binds an incompatible cuDNN into
the process, which then makes torch's own GPU cuDNN calls crash with
``Could not load symbol cudnnGetLibConfig`` (STATUS_STACK_BUFFER_OVERRUN).

Initialising torch's GPU cuDNN *first* loads the correct cuDNN 9 DLL, so the
later CTranslate2 import resolves against it cleanly. ``prime_cuda`` must run
before the first faster-whisper import (i.e. before Whisper warmup/transcribe).
"""
from __future__ import annotations

import logging

from app.config import cuda_available

logger = logging.getLogger(__name__)

_primed = False


def prime_cuda() -> bool:
    """Force-initialise torch's GPU cuDNN before CTranslate2 is imported.

    Runs a tiny cuDNN convolution to fully load the library. Best-effort and
    idempotent; returns True if CUDA was primed, False otherwise.
    """
    global _primed
    if _primed or not cuda_available():
        return _primed
    try:
        import torch

        x = torch.randn(1, 3, 16, 16, device="cuda")
        conv = torch.nn.Conv2d(3, 4, 3).cuda()
        with torch.no_grad():
            conv(x)
        torch.cuda.synchronize()
        _primed = True
        logger.info(
            "CUDA primed (cuDNN %s) — GPU acceleration enabled before CTranslate2 load.",
            torch.backends.cudnn.version(),
        )
    except Exception as e:  # pragma: no cover - best effort
        logger.warning("CUDA priming failed (%s); continuing on CPU where needed.", e)
    return _primed
