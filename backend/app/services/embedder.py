"""Text and image embeddings with graceful degradation."""
from __future__ import annotations

import logging
import warnings
from threading import Lock

from app.config import settings, resolve_device

logger = logging.getLogger(__name__)

_text_model = None
_text_model_failed = False
_text_lock = Lock()

_clip_model = None
_clip_processor = None
_clip_device = "cpu"
_clip_failed = False
_clip_lock = Lock()


def _get_text_model():
    """Lazy-load the sentence-transformers model used for transcript search."""
    global _text_model, _text_model_failed
    if _text_model_failed:
        return None
    with _text_lock:
        if _text_model is None:
            try:
                device = resolve_device(settings.embedding_device)
                logger.info(
                    "Loading text embedding model: %s (device=%s)",
                    settings.text_embedding_model, device,
                )
                from sentence_transformers import SentenceTransformer
                _text_model = SentenceTransformer(
                    settings.text_embedding_model, device=device
                )
                logger.info("Text embedding model loaded.")
            except Exception as e:
                logger.warning("Could not load text embedding model: %s. Semantic search disabled.", e)
                _text_model_failed = True
                _text_model = None
    return _text_model


def _get_clip():
    """Lazy-load CLIP model and processor used for visual search."""
    global _clip_model, _clip_processor, _clip_failed, _clip_device
    if _clip_failed:
        return None, None
    with _clip_lock:
        if _clip_model is None or _clip_processor is None:
            try:
                _clip_device = resolve_device(settings.embedding_device)
                logger.info("Loading CLIP model: %s (device=%s)",
                            settings.clip_model, _clip_device)
                from transformers import CLIPModel, CLIPProcessor
                _clip_model = CLIPModel.from_pretrained(settings.clip_model)
                if _clip_device == "cuda":
                    try:
                        _clip_model = _clip_model.to("cuda")
                    except Exception as e:
                        logger.warning("Could not move CLIP to GPU (%s); using CPU.", e)
                        _clip_device = "cpu"
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message=".*clean_up_tokenization_spaces.*",
                        category=FutureWarning,
                    )
                    _clip_processor = CLIPProcessor.from_pretrained(settings.clip_model)
                _clip_model.eval()
                logger.info("CLIP model loaded.")
            except Exception as e:
                logger.warning("Could not load CLIP model: %s. Visual search disabled.", e)
                _clip_failed = True
                _clip_model = None
                _clip_processor = None
    return _clip_model, _clip_processor


def warmup() -> None:
    """Eagerly load the text embedding model so the first request is fast."""
    try:
        _get_text_model()
    except Exception as e:  # pragma: no cover - warmup is best-effort
        logger.warning("Text embedder warmup failed: %s", e)


def warmup_clip() -> None:
    """Eagerly load CLIP so the first video frame doesn't pay for it."""
    if not settings.enable_frame_extraction:
        return
    try:
        _get_clip()
    except Exception as e:  # pragma: no cover - warmup is best-effort
        logger.warning("CLIP warmup failed: %s", e)


def embed_text(text: str) -> list[float]:
    """Embed one text string for semantic search."""
    model = _get_text_model()
    if model is None or not text.strip():
        return []
    try:
        return model.encode(text, normalize_embeddings=True).tolist()
    except Exception as e:
        logger.warning("Text embedding failed: %s", e)
        return []


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of text strings.

    Always returns a list of the same length as ``texts``.  Failed batches
    return empty vectors for each item in that batch rather than truncating the
    result list (which would cause silent silent dropped indexing via zip()).
    """
    model = _get_text_model()
    if model is None or not texts:
        return [[] for _ in texts]
    try:
        result = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
        ).tolist()
        # Guarantee output length matches input length even on partial encode
        if len(result) != len(texts):
            logger.warning(
                "embed_texts: got %d vectors for %d texts; padding with empty vectors.",
                len(result), len(texts),
            )
            result.extend([] for _ in range(len(texts) - len(result)))
        return result
    except Exception as e:
        logger.warning("Batch text embedding failed: %s", e)
        return [[] for _ in texts]


def embed_image(image_path: str) -> list[float]:
    """Embed one image using CLIP image features."""
    return embed_images([image_path])[0]


def embed_images(image_paths: list[str], batch_size: int = 16) -> list[list[float]]:
    """Embed many images using CLIP, batched through the model.

    Numerically identical to calling ``embed_image`` per file, but runs one
    forward pass per ``batch_size`` images instead of one per image — a large
    speedup on videos with many frames. Returns ``[]`` for any image that
    cannot be opened, preserving input order.
    """
    if not image_paths:
        return []
    model, processor = _get_clip()
    if model is None or processor is None:
        return [[] for _ in image_paths]

    import torch
    from PIL import Image

    results: list[list[float]] = [[] for _ in image_paths]
    for start in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[start:start + batch_size]
        images: list = []
        valid_idx: list[int] = []
        for offset, path in enumerate(batch_paths):
            try:
                images.append(Image.open(path).convert("RGB"))
                valid_idx.append(start + offset)
            except Exception as e:
                logger.warning("Could not open image %s: %s", path, e)
        if not images:
            continue
        try:
            inputs = processor(images=images, return_tensors="pt")
            if _clip_device == "cuda":
                inputs = {k: v.to("cuda") for k, v in inputs.items()}
            with torch.no_grad():
                features = model.get_image_features(**inputs)
                # E1 fix: guard against zero-norm vectors (blank/near-blank frames)
                # before dividing.  A zero-norm produces NaN which corrupts Qdrant
                # cosine similarity for ALL subsequent visual searches globally.
                norms = features.norm(dim=-1, keepdim=True)
                norms = norms.clamp(min=1e-8)   # replace 0 with tiny value → unit vec
                features = features / norms
            features = features.cpu()
            for local_i, global_i in enumerate(valid_idx):
                vec = features[local_i].tolist()
                # Sanity-check: drop any vector that still contains NaN/Inf
                if any(v != v or abs(v) == float("inf") for v in vec):
                    logger.warning("Skipping NaN/Inf CLIP vector for image index %d", global_i)
                else:
                    results[global_i] = vec
        except Exception as e:
            logger.warning("Batch image embedding failed (%d imgs): %s", len(images), e)
        finally:
            for img in images:
                img.close()
    return results


def embed_text_for_image_search(text: str) -> list[float]:
    """Embed text in CLIP space for text-to-image frame search."""
    model, processor = _get_clip()
    if model is None or processor is None or not text.strip():
        return []
    try:
        import torch

        inputs = processor(text=[text], return_tensors="pt", padding=True)
        if _clip_device == "cuda":
            inputs = {k: v.to("cuda") for k, v in inputs.items()}
        with torch.no_grad():
            features = model.get_text_features(**inputs)
            norms = features.norm(dim=-1, keepdim=True).clamp(min=1e-8)
            features = features / norms
        return features[0].cpu().tolist()
    except Exception as e:
        logger.warning("CLIP text embedding failed: %s", e)
        return []
