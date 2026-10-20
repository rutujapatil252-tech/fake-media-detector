"""
Deep Learning AI-Generated Image Detector Check (Phase 3).

Leverages a fine-tuned vision transformer (ViT) or convolutional architecture
hosted on Hugging Face to classify whether an image exhibits the characteristic
frequency, latent, or perceptual artifacts of synthetic AI image generators
(e.g., Stable Diffusion, Midjourney, DALL-E).

Forensic Methodological Context & Limitations:
1. Statistical Estimate: The neural network produces a probability estimate based on
   its training distribution. It is not an absolute cryptographic proof.
2. Generator Generalization Gap: Detectors trained on older models (e.g., SD 1.5, SDXL)
   often experience accuracy degradation when evaluated on newer unseen architectures
   (such as Flux, Midjourney v6, or Ideogram).
3. Post-Processing Robustness: Social media compression, downscaling, screenshotting,
   and heavy noise can obscure the subtle high-frequency artifacts the model relies on.
"""

import io
import logging
from typing import Any, Dict, List, Optional
from PIL import Image

from app.config import (
    AI_CANDIDATE_MODELS,
    AI_MODEL_NAME,
    AI_PROBABILITY_HIGH_THRESHOLD,
    AI_PROBABILITY_LOW_THRESHOLD,
)

logger = logging.getLogger("fake_media_detector.ai_detector")

# Global singleton cache for the loaded classification pipeline
_AI_CLASSIFIER_PIPELINE: Optional[Any] = None
_ACTIVE_MODEL_NAME: Optional[str] = None
_LOAD_ERROR: Optional[str] = None

# Known label mapping aliases
# Labels indicating artificial / synthetic generation
AI_LABEL_KEYWORDS = {
    "artificial",
    "ai",
    "fake",
    "synthetic",
    "generated",
    "sdxl",
    "deepfake",
}

# Labels indicating authentic / human-created photographs
REAL_LABEL_KEYWORDS = {
    "human",
    "real",
    "authentic",
    "natural",
    "original",
}


def map_predictions_to_ai_probability(predictions: List[Dict[str, Any]]) -> float:
    """
    Translates heterogeneous classification labels into a unified 'ai_probability' metric (0.0 to 1.0).

    Handles multiple model naming conventions:
    - 'artificial' vs 'human' (e.g., Organika/sdxl-detector)
    - 'AI' vs 'Real' (e.g., umm-maybe/AI-image-detector)
    - 'fake' vs 'real' (e.g., dima806/ai_vs_real_image_detection)

    Args:
        predictions: List of dicts returned by Hugging Face pipeline, e.g.
                     [{'label': 'human', 'score': 0.93}, {'label': 'artificial', 'score': 0.07}]

    Returns:
        float: Probability from 0.0 (confidently human/real) to 1.0 (confidently AI-generated).
    """
    if not predictions:
        return 0.5

    # 1. Direct match for an AI-associated class
    for item in predictions:
        lbl = str(item.get("label", "")).lower().strip()
        if lbl in AI_LABEL_KEYWORDS:
            return round(float(item["score"]), 4)

    # 2. Check for human/real class and calculate complement
    for item in predictions:
        lbl = str(item.get("label", "")).lower().strip()
        if lbl in REAL_LABEL_KEYWORDS:
            return round(1.0 - float(item["score"]), 4)

    # 3. Substring heuristic fallback for unconventional labels
    for item in predictions:
        lbl = str(item.get("label", "")).lower().strip()
        if any(kw in lbl for kw in ["artif", "ai", "synth", "fake", "gen"]):
            return round(float(item["score"]), 4)

    # 4. Fallback: assume first item is non-AI if labeled 'real' or similar
    top = predictions[0]
    top_label = str(top.get("label", "")).lower().strip()
    if any(kw in top_label for kw in ["human", "real", "orig"]):
        return round(1.0 - float(top["score"]), 4)

    return round(float(top["score"]), 4)


def assign_categorical_label(ai_probability: float) -> str:
    """
    Classifies the numeric AI probability into high-level interpretative bands:
    - >= 0.7: 'likely_ai'
    - 0.4 to 0.7: 'uncertain'
    - < 0.4: 'likely_real'
    """
    if ai_probability >= AI_PROBABILITY_HIGH_THRESHOLD:
        return "likely_ai"
    elif ai_probability >= AI_PROBABILITY_LOW_THRESHOLD:
        return "uncertain"
    else:
        return "likely_real"


def load_model_pipeline(preferred_model: str = AI_MODEL_NAME) -> tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    Attempts to load the preferred image-classification pipeline from Hugging Face.
    If the preferred model fails, tries candidate models sequentially.

    Returns:
        tuple[pipeline, model_name, error_message]
    """
    try:
        from transformers import pipeline
    except ImportError as e:
        return None, None, f"transformers library not available: {str(e)}"

    candidate_queue = [preferred_model]
    for c in AI_CANDIDATE_MODELS:
        if c not in candidate_queue:
            candidate_queue.append(c)

    last_error = None
    for model_name in candidate_queue:
        try:
            logger.info("Attempting to load AI detector model: %s", model_name)
            clf = pipeline("image-classification", model=model_name)
            logger.info("Successfully loaded AI detector model: %s", model_name)
            return clf, model_name, None
        except Exception as exc:
            last_error = f"Failed to load {model_name}: {str(exc)}"
            logger.warning("Could not load %s (%s). Trying next candidate...", model_name, exc)

    return None, None, last_error


def get_ai_classifier() -> tuple[Optional[Any], Optional[str], Optional[str]]:
    """
    Global singleton accessor for the AI classifier.
    Loads lazily on the first request and caches in memory across requests.
    """
    global _AI_CLASSIFIER_PIPELINE, _ACTIVE_MODEL_NAME, _LOAD_ERROR

    if _AI_CLASSIFIER_PIPELINE is not None:
        return _AI_CLASSIFIER_PIPELINE, _ACTIVE_MODEL_NAME, None

    if _LOAD_ERROR is not None:
        # Previously attempted and failed
        return None, _ACTIVE_MODEL_NAME, _LOAD_ERROR

    pipeline_obj, model_name, err = load_model_pipeline()
    if pipeline_obj is not None:
        _AI_CLASSIFIER_PIPELINE = pipeline_obj
        _ACTIVE_MODEL_NAME = model_name
        _LOAD_ERROR = None
    else:
        _AI_CLASSIFIER_PIPELINE = None
        _ACTIVE_MODEL_NAME = preferred_model = AI_MODEL_NAME
        _LOAD_ERROR = err

    return _AI_CLASSIFIER_PIPELINE, _ACTIVE_MODEL_NAME, _LOAD_ERROR


def warmup_ai_detector() -> bool:
    """
    Preloads and warms up the AI model pipeline during application startup
    (e.g., via FastAPI lifespan handler) so the first HTTP request experiences zero cold-start delay.

    Returns:
        bool: True if model loaded successfully, False otherwise.
    """
    clf, model_name, err = get_ai_classifier()
    if clf is not None:
        print(f"[AI Detector] Preloaded model successfully: '{model_name}'")
        return True
    else:
        print(f"[AI Detector] Warning: Preloading failed: {err}")
        return False


def _autocrop_letterbox(pil_img: Image.Image) -> Image.Image:
    """
    Detects and crops solid black/near-black letterbox padding (common in mobile screenshots)
    so empty borders do not distort the aspect ratio or dilute patch embeddings.
    """
    try:
        gray = pil_img.convert("L")
        mask = gray.point(lambda p: 255 if p > 25 else 0)
        bbox = mask.getbbox()
        if bbox:
            w, h = pil_img.size
            bw, bh = bbox[2] - bbox[0], bbox[3] - bbox[1]
            if (bw * bh) < (w * h * 0.90) and bw > 64 and bh > 64:
                return pil_img.crop(bbox)
    except Exception:
        pass
    return pil_img


def analyze_ai_generated(image_bytes: bytes) -> Dict[str, Any]:
    """
    Forensic deep-learning check to estimate probability of AI generation.

    Decodes image bytes, ensures uniform RGB color space (handling RGBA, grayscale, palette),
    runs classification, and formats results with probability and categorical banding.

    Args:
        image_bytes: Raw binary image bytes.

    Returns:
        dict: Conforming to AIDetectorCheckResult schema.
    """
    clf, model_name, err = get_ai_classifier()
    resolved_model_name = model_name or AI_MODEL_NAME

    if clf is None:
        return {
            "model_name": resolved_model_name,
            "ai_probability": 0.5,
            "label": "uncertain",
            "risk_score": 0.5,
            "available": False,
            "error": err or "AI detection model not loaded.",
            "note": (
                "Deep learning AI detector is currently unavailable (model failed to load or "
                "offline environment). Returning neutral risk score (0.5)."
            ),
        }

    try:
        # 1. Decode image bytes and convert to RGB
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            # Handle RGBA, Palette, Greyscale, or CMYK uniformly
            rgb_img = pil_img.convert("RGB")
            # Auto-crop black letterbox margins if present (e.g. mobile screenshots)
            content_img = _autocrop_letterbox(rgb_img)

            # 2. Run inference
            predictions = clf(content_img)

        # 3. Map predictions to normalized probability
        ai_prob = map_predictions_to_ai_probability(predictions)
        category_label = assign_categorical_label(ai_prob)

        return {
            "model_name": resolved_model_name,
            "ai_probability": ai_prob,
            "label": category_label,
            "risk_score": ai_prob,
            "available": True,
            "error": None,
            "note": (
                "Statistical probability estimate from a deep learning classifier. "
                "May not generalize to newer or unseen generation architectures."
            ),
        }

    except Exception as exc:
        logger.exception("Inference error in analyze_ai_generated")
        return {
            "model_name": resolved_model_name,
            "ai_probability": 0.5,
            "label": "uncertain",
            "risk_score": 0.5,
            "available": False,
            "error": str(exc),
            "note": f"Inference execution failed: {str(exc)}",
        }
