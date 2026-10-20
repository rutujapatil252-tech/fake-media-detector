"""
Metadata Analysis Module for Fake Media Detector.

Analyzes EXIF (Exchangeable Image File Format) and embedded container headers
in uploaded images to identify camera fingerprints, editing software traces,
timestamp inconsistencies, and AI generation signatures.

LIMITATION NOTE:
Missing EXIF data is a WEAK signal, not definitive proof of tampering or AI generation.
Most major social media platforms (Twitter/X, Facebook, Instagram, WhatsApp) strip
EXIF metadata automatically upon upload for user privacy and bandwidth reduction.
Therefore, lack of EXIF indicates elevated uncertainty rather than guaranteed forgery.
"""

import io
from pathlib import Path
from typing import Any, Dict, List, Optional
import cv2
import exifread
import numpy as np
from PIL import Image

from app.config import (
    AI_TOOL_KEYWORDS,
    DATA_DIR,
    EDITING_SOFTWARE_KEYWORDS,
)


def _normalize_string(val: Any) -> str:
    """Safely converts tag values to lowercase stripped strings for matching."""
    if val is None:
        return ""
    return str(val).strip().lower()


def _extract_gps_presence(tags: Dict[str, Any]) -> bool:
    """
    Checks if GPS coordinates or GPS metadata tags are present in EXIF.
    Smartphones and modern cameras often include GPS unless disabled by privacy settings.
    """
    for key in tags.keys():
        if "GPS" in key:
            return True
    return False


def _check_text_for_keywords(text: str, keywords: List[str]) -> Optional[str]:
    """Returns the matching keyword if any keyword appears in the given text."""
    lower_text = text.lower()
    for kw in keywords:
        if kw in lower_text:
            return kw
    return None


def _scan_visual_watermarks(image_bytes: bytes) -> Optional[str]:
    """
    Scans the perimeter/corners of an image for known visual AI generation badges
    (e.g., Meta AI watermark) using normalized multi-scale template matching.
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Template for Meta AI corner badge
        template_path = DATA_DIR / "watermarks" / "meta_ai_badge.png"
        if not template_path.exists():
            return None

        template = cv2.imread(str(template_path))
        if template is None:
            return None

        th, tw, _ = template.shape
        ih, iw, _ = img.shape

        # Search in the bottom 25% of the image (or lower perimeter)
        bottom_strip = img[int(ih * 0.70):, :]
        if bottom_strip.shape[0] < th or bottom_strip.shape[1] < tw:
            return None

        # Check multi-scale templates (0.75x to 1.5x)
        for scale in [0.75, 1.0, 1.25, 1.5]:
            rw, rh = int(tw * scale), int(th * scale)
            if rw >= bottom_strip.shape[1] or rh >= bottom_strip.shape[0] or rw < 10 or rh < 10:
                continue
            scaled = cv2.resize(template, (rw, rh))
            res = cv2.matchTemplate(bottom_strip, scaled, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            if max_val >= 0.72:
                return "Meta AI"
    except Exception:
        pass
    return None


def analyze_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    Extracts and evaluates metadata from an image byte stream.

    Args:
        image_bytes: Raw binary content of the image.

    Returns:
        dict containing:
            - has_exif (bool): Whether any EXIF markers were present.
            - fields (dict): Key extracted metadata (Make, Model, Software, Dates, GPS).
            - red_flags (list[str]): Detected suspicious flags or warnings.
            - risk_score (float): Calculated risk score between 0.0 and 1.0.

    Docstring Note:
        Missing EXIF data is a weak signal, not proof, since social media
        and messaging apps routinely strip EXIF for privacy preservation.
    """
    red_flags: List[str] = []
    fields: Dict[str, Any] = {}
    has_exif = False

    # 1. Parse EXIF using exifread
    try:
        # details=False speeds up tag parsing by skipping complex maker-note parsing
        tags = exifread.process_file(io.BytesIO(image_bytes), details=False)
        if tags:
            has_exif = True
    except Exception as exc:
        tags = {}
        red_flags.append(f"EXIF parsing error: {str(exc)}")

    # 2. Also inspect container info via Pillow (especially useful for PNG text chunks and WebP)
    pillow_info: Dict[str, Any] = {}
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            pillow_info = {str(k): str(v) for k, v in pil_img.info.items()}
            # Check Pillow's getexif if exifread found nothing
            if not has_exif and hasattr(pil_img, "getexif"):
                exif_data = pil_img.getexif()
                if exif_data and len(exif_data) > 0:
                    has_exif = True
    except Exception:
        # Image opening failure will be caught or handled during format validation
        pass

    # 3. Extract standard EXIF fields if available
    camera_make = tags.get("Image Make") or tags.get("Make")
    camera_model = tags.get("Image Model") or tags.get("Model")
    software_tag = tags.get("Image Software") or tags.get("Software")
    date_time = tags.get("Image DateTime")
    date_original = tags.get("EXIF DateTimeOriginal")
    date_digitized = tags.get("EXIF DateTimeDigitized")
    has_gps = _extract_gps_presence(tags)

    if camera_make:
        fields["make"] = str(camera_make).strip()
    if camera_model:
        fields["model"] = str(camera_model).strip()
    if software_tag:
        fields["software"] = str(software_tag).strip()
    if date_time:
        fields["date_modified"] = str(date_time).strip()
    if date_original:
        fields["date_original"] = str(date_original).strip()
    if date_digitized:
        fields["date_digitized"] = str(date_digitized).strip()
    fields["has_gps"] = has_gps

    # Collect any embedded prompts or text chunks from PNG/WebP (common in AI tools like ComfyUI / A1111)
    for info_key, info_val in pillow_info.items():
        if info_key.lower() in {"parameters", "prompt", "workflow", "comment", "description"}:
            fields[f"embedded_{info_key.lower()}"] = info_val[:300] + ("..." if len(info_val) > 300 else "")

    # 4. Analyze Red Flags and Risk Score
    risk_score = 0.0

    if not has_exif:
        # Missing EXIF is a weak indicator because social media platforms strip it for privacy.
        # We assign a moderate baseline uncertainty score (0.35).
        red_flags.append(
            "No EXIF metadata found (common when images are uploaded to social media platforms or generated synthetically)"
        )
        risk_score += 0.35
    else:
        # Camera identity checks: authentic camera photos almost always have Make and Model
        if not camera_make and not camera_model:
            red_flags.append("EXIF is present but lacks camera Make and Model tags")
            risk_score += 0.15

        # Check for editing software in Software tag
        if software_tag:
            soft_str = str(software_tag)
            matched_editor = _check_text_for_keywords(soft_str, EDITING_SOFTWARE_KEYWORDS)
            if matched_editor:
                red_flags.append(f"Image editing software detected in metadata: '{soft_str}'")
                risk_score += 0.50

            matched_ai = _check_text_for_keywords(soft_str, AI_TOOL_KEYWORDS)
            if matched_ai:
                red_flags.append(f"AI generation signature detected in software tag: '{matched_ai}'")
                risk_score += 0.85

        # Check for timestamp discrepancy (e.g. modified date differs from original shot date)
        if date_original and date_time:
            str_orig = str(date_original).strip()
            str_mod = str(date_time).strip()
            if str_orig != str_mod:
                red_flags.append(
                    f"Timestamp discrepancy detected: Original ({str_orig}) differs from Modified ({str_mod})"
                )
                risk_score += 0.25

    # Check embedded container chunks for AI generator signatures (e.g. Stable Diffusion parameters)
    all_raw_text = " ".join([str(v) for v in pillow_info.values()] + [str(v) for v in fields.values()])
    matched_ai_in_text = _check_text_for_keywords(all_raw_text, AI_TOOL_KEYWORDS)
    if matched_ai_in_text and not any("AI generation signature" in rf for rf in red_flags):
        red_flags.append(f"AI generation signature detected in container metadata: '{matched_ai_in_text}'")
        risk_score += 0.85

    # Check for visual AI watermark badges (e.g. Meta AI flower icon / badge)
    visual_watermark = _scan_visual_watermarks(image_bytes)
    if visual_watermark:
        fields["visual_watermark"] = f"{visual_watermark} (Generative AI Badge)"
        red_flags.append(f"Visual AI watermark badge detected: '{visual_watermark}'")
        risk_score = max(risk_score, 0.95)

    # If the image has legitimate camera EXIF with GPS and no editing artifacts, reward lower risk
    if has_exif and camera_make and camera_model and not any("editing" in rf or "AI" in rf for rf in red_flags):
        risk_score = min(risk_score, 0.10)

    # Clamp risk score to [0.0, 1.0] and round for readability
    risk_score = max(0.0, min(1.0, round(risk_score, 3)))

    return {
        "has_exif": has_exif,
        "fields": fields,
        "red_flags": red_flags,
        "risk_score": risk_score,
    }
