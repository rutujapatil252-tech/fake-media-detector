"""
Error Level Analysis (ELA) Module for Fake Media Detector.

What is Error Level Analysis (ELA)?
-----------------------------------
JPEG is a lossy compression format. Every time an image is compressed as a JPEG,
high-frequency image details are approximated in 8x8 pixel blocks based on a quantization
table. Over multiple saves at the same quality level, the error (difference between saves)
decreases and reaches an equilibrium.

ELA intentionally re-saves an image at a known quality level (typically 90) and computes
the absolute difference between the incoming image and the re-saved version.
In an untouched original JPEG, all regions have reached a similar compression equilibrium,
so the error level across the entire image is relatively uniform (with expected slight rises
around high-contrast edges).

If an image is spliced (e.g., an object from an uncompressed or differently compressed source
is inserted into a JPEG background), the spliced region will exhibit a substantially different
error rate compared to the surrounding background.

LIMITATIONS OF ELA:
-------------------
1. Works best on JPEG images: Uncompressed formats (PNG, BMP) or lossless WebP have never undergone
   prior lossy quantization; re-saving them as JPEG creates uniform high error throughout the entire
   canvas, which may lead to false positives if interpreted naively.
2. High-contrast edges naturally exhibit higher error than flat smooth areas (sky, walls), which can
   be mistaken for manipulation by inexperienced observers.
3. Rescaling or heavy recompression (e.g. uploading to social media) can wash out original compression
   discrepancies, yielding false negatives.
"""

import base64
import io
from typing import Any, Dict
import cv2
import numpy as np
from PIL import Image

from app.config import (
    ELA_AMPLIFY_SCALE,
    ELA_JPEG_QUALITY,
    ELA_MAX_DIMENSION,
    ELA_SUSPICIOUS_PIXEL_THRESHOLD,
)


def analyze_ela(image_bytes: bytes) -> Dict[str, Any]:
    """
    Performs Error Level Analysis (ELA) on the provided image bytes.

    Steps:
    1. Loads the image and normalizes it to RGB.
    2. Resizes large images so processing remains fast and memory-efficient.
    3. Re-compresses the image as JPEG at quality 90 in memory.
    4. Computes per-pixel difference between the input and the re-compressed version.
    5. Calculates statistical metrics (mean error, max error, suspicious pixel ratio).
    6. Generates an amplified color heatmap encoded as a Base64 PNG string.
    7. Evaluates a normalized manipulation risk score (0.0 to 1.0).

    Args:
        image_bytes: Raw binary content of the uploaded image.

    Returns:
        dict containing:
            - heatmap_base64 (str): Base64-encoded PNG image displaying the amplified ELA heatmap.
            - mean_error (float): Average per-pixel error magnitude.
            - max_error (float): Peak observed pixel error magnitude.
            - suspicious_region_ratio (float): Ratio of pixels exceeding the anomaly threshold.
            - risk_score (float): Manipulation likelihood between 0.0 and 1.0.
    """
    # 1. Open original image using Pillow and convert to standard 24-bit RGB
    # Converting to RGB guarantees uniform channel dimensionality for math operations
    original_pil = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    # 2. Downscale image if larger than ELA_MAX_DIMENSION (1024px)
    # This prevents denial-of-service from massive multi-megapixel files and speeds up analysis
    orig_w, orig_h = original_pil.size
    max_side = max(orig_w, orig_h)
    if max_side > ELA_MAX_DIMENSION:
        scale_factor = ELA_MAX_DIMENSION / float(max_side)
        new_size = (int(orig_w * scale_factor), int(orig_h * scale_factor))
        original_pil = original_pil.resize(new_size, Image.Resampling.LANCZOS)

    # 3. Re-save in memory as JPEG at quality 90
    # Re-saving at a fixed quality forces lossy compression discrepancies to surface
    jpeg_buffer = io.BytesIO()
    original_pil.save(jpeg_buffer, format="JPEG", quality=ELA_JPEG_QUALITY)
    jpeg_buffer.seek(0)
    resaved_pil = Image.open(jpeg_buffer).convert("RGB")

    # 4. Compute numerical differences using NumPy
    orig_np = np.array(original_pil, dtype=np.float32)
    resaved_np = np.array(resaved_pil, dtype=np.float32)

    # Absolute difference per channel
    abs_diff = np.abs(orig_np - resaved_np)

    # Average difference across the 3 color channels (R, G, B) to obtain per-pixel error
    pixel_error = np.mean(abs_diff, axis=2)

    mean_error = float(np.mean(pixel_error))
    max_error = float(np.max(pixel_error))

    # 5. Calculate suspicious region ratio
    # Fraction of pixels whose error exceeds the anomaly threshold
    suspicious_pixels = int(np.sum(pixel_error > ELA_SUSPICIOUS_PIXEL_THRESHOLD))
    total_pixels = pixel_error.size
    suspicious_region_ratio = float(suspicious_pixels / total_pixels) if total_pixels > 0 else 0.0

    # 6. Generate amplified color heatmap for human visualization
    # Pixel errors are typically small (0-15), so we multiply by ELA_AMPLIFY_SCALE to make them visible
    amplified_gray = np.clip(pixel_error * ELA_AMPLIFY_SCALE, 0, 255).astype(np.uint8)

    # Apply JET colormap: blue = lowest error, red/yellow = highest error regions
    heatmap_bgr = cv2.applyColorMap(amplified_gray, cv2.COLORMAP_JET)
    heatmap_rgb = cv2.cvtColor(heatmap_bgr, cv2.COLOR_BGR2RGB)

    heatmap_pil = Image.fromarray(heatmap_rgb)
    out_buffer = io.BytesIO()
    heatmap_pil.save(out_buffer, format="PNG")
    heatmap_base64 = base64.b64encode(out_buffer.getvalue()).decode("utf-8")

    # 7. Compute Risk Score (0.0 to 1.0)
    # WHY this formula:
    # An authentic JPEG that has already settled into compression equilibrium exhibits
    # low mean error (usually < 2.5) and near 0 suspicious regions.
    # When an uncompressed element is spliced into a JPEG, only a portion of the image
    # lights up with high error (localized anomaly), resulting in moderate suspicious_region_ratio.
    # High standard deviation / variance in pixel error indicates non-uniform compression history.
    error_std = float(np.std(pixel_error))

    risk_score = 0.0

    if suspicious_region_ratio > 0.02 and suspicious_region_ratio < 0.45:
        # Localized anomaly: A specific segment has higher compression discrepancy than the rest
        # This is a classic hallmark of digital splicing / cut-and-paste manipulation
        risk_score += 0.45 + (suspicious_region_ratio * 0.8)
    elif suspicious_region_ratio >= 0.45:
        # Broad high error: Often occurs when a lossless PNG or AI image is first compressed to JPEG
        risk_score += 0.40
    else:
        # Very low suspicious ratio: Mostly uniform compression
        risk_score += min(0.20, mean_error * 0.05)

    # Add penalty for high standard deviation (disparate compression levels across regions)
    if error_std > 8.0:
        risk_score += 0.20
    elif error_std > 4.0:
        risk_score += 0.10

    # Clamp risk score to [0.0, 1.0] and round to 3 decimals
    risk_score = max(0.0, min(1.0, round(risk_score, 3)))

    return {
        "heatmap_base64": heatmap_base64,
        "mean_error": round(mean_error, 3),
        "max_error": round(max_error, 3),
        "suspicious_region_ratio": round(suspicious_region_ratio, 4),
        "risk_score": risk_score,
    }
