
"""
Verdict Engine for Fake Media Detector (Phase 4).

Synthesizes multi-vector forensic signals (Metadata, ELA, C2PA Provenance,
Perceptual Duplicate Hashing, and Deep Learning Vision Classification)
into a unified, transparent, and explainable verdict.

Pillars of the Verdict Engine:
1. Dynamic Weight Renormalization: If a check is offline or errored, its weight
   is redistributed proportionally across active checks without skewing the score.
2. Cryptographic Overrides: Definitive cryptographic evidence (e.g., C2PA assertions
   explicitly declaring 'trainedAlgorithmicMedia' or broken signatures) supersedes
   heuristic and statistical estimates.
3. Epistemic Humility & Honesty: Missing EXIF or absent C2PA manifests are treated
   strictly as neutral signals, acknowledging that social platforms routinely strip metadata.
"""

from typing import Any, Dict, List, Optional
from app.config import (
    C2PA_AUTHENTIC_SCORE_REDUCTION,
    VERDICT_THRESHOLD_AI,
    VERDICT_THRESHOLD_AUTHENTIC,
    VERDICT_THRESHOLD_MANIPULATED,
    VERDICT_WEIGHTS,
)


DISPLAY_LABELS: Dict[str, str] = {
    "likely_ai_generated": "Likely AI-generated",
    "possibly_manipulated": "Possibly Manipulated",
    "likely_authentic": "Likely Authentic",
    "inconclusive": "Inconclusive",
}


def _evaluate_evidence_item(check_name: str, check_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Constructs a standardized evidence record with status ('suspicious', 'neutral', 'clean', 'unavailable'),
    score, and a concise human-readable summary.
    """
    if not check_data:
        return {
            "check": check_name,
            "status": "unavailable",
            "score": None,
            "summary": f"{check_name} check did not execute.",
        }

    # Handle explicit unavailability or errors
    if check_data.get("available") is False or check_data.get("error"):
        err_msg = check_data.get("error", "Check unavailable")
        return {
            "check": check_name,
            "status": "unavailable",
            "score": None,
            "summary": f"Unavailable: {err_msg}",
        }

    score = float(check_data.get("risk_score", 0.5))

    if check_name == "ai_detector":
        ai_prob = float(check_data.get("ai_probability", score))
        label = check_data.get("label", "uncertain")
        if ai_prob >= 0.70:
            return {
                "check": "ai_detector",
                "status": "suspicious",
                "score": ai_prob,
                "summary": f"Deep learning vision model detected strong generative AI artifacts ({ai_prob * 100:.1f}% probability).",
            }
        elif ai_prob < 0.40:
            return {
                "check": "ai_detector",
                "status": "clean",
                "score": ai_prob,
                "summary": f"Deep learning vision model found natural pixel textures ({ai_prob * 100:.1f}% AI probability).",
            }
        else:
            return {
                "check": "ai_detector",
                "status": "neutral",
                "score": ai_prob,
                "summary": f"Vision model probability ({ai_prob * 100:.1f}%) is in the indeterminate boundary.",
            }

    elif check_name == "c2pa":
        has_manifest = check_data.get("has_manifest", False)
        if not has_manifest:
            return {
                "check": "c2pa",
                "status": "neutral",
                "score": score,
                "summary": "No C2PA Content Credentials manifest found (platforms strip container metadata).",
            }

        ai_flag = check_data.get("ai_generated_flag", False)
        is_valid = check_data.get("is_valid")
        issuer = check_data.get("issuer")

        if ai_flag:
            return {
                "check": "c2pa",
                "status": "suspicious",
                "score": score,
                "summary": "Manifest cryptographically certifies that generative AI created or edited this asset.",
            }
        elif is_valid is False:
            return {
                "check": "c2pa",
                "status": "suspicious",
                "score": score,
                "summary": "Manifest signature verification failed or indicates tampered credentials.",
            }
        elif is_valid is True:
            return {
                "check": "c2pa",
                "status": "clean",
                "score": score,
                "summary": f"Verified authentic cryptographic signature from issuer: {issuer or 'Authorized Authority'}.",
            }
        else:
            return {
                "check": "c2pa",
                "status": "neutral",
                "score": score,
                "summary": "C2PA manifest structure parsed without explicit generative AI assertions.",
            }

    elif check_name == "metadata":
        red_flags = check_data.get("red_flags", [])
        has_exif = check_data.get("has_exif", False)
        fields = check_data.get("fields", {})

        # Visual watermark badge check
        visual_watermark = fields.get("visual_watermark")
        if visual_watermark:
            return {
                "check": "metadata",
                "status": "suspicious",
                "score": score,
                "summary": f"Visual AI watermark detected: {visual_watermark}.",
            }

        # Software or AI tool red flags
        software_flags = [rf for rf in red_flags if "software" in rf.lower() or "ai" in rf.lower()]
        if software_flags:
            return {
                "check": "metadata",
                "status": "suspicious",
                "score": score,
                "summary": f"Editing/AI software signature detected in container tags ({'; '.join(software_flags)}).",
            }
        elif has_exif and (fields.get("make") or fields.get("model")):
            make_model = f"{fields.get('make', '')} {fields.get('model', '')}".strip()
            return {
                "check": "metadata",
                "status": "clean",
                "score": score,
                "summary": f"Authentic camera hardware metadata present ({make_model}).",
            }
        else:
            return {
                "check": "metadata",
                "status": "neutral",
                "score": score,
                "summary": "No camera EXIF metadata present (common for web and messaging app uploads).",
            }

    elif check_name == "ela":
        susp_ratio = float(check_data.get("suspicious_region_ratio", 0.0))
        if score >= 0.40 or susp_ratio > 0.03:
            return {
                "check": "ela",
                "status": "suspicious",
                "score": score,
                "summary": f"Compression error level analysis revealed localized splicing anomalies ({susp_ratio * 100:.1f}% suspicious pixels).",
            }
        elif score <= 0.15:
            return {
                "check": "ela",
                "status": "clean",
                "score": score,
                "summary": "Uniform compression error variance across the entire image surface.",
            }
        else:
            return {
                "check": "ela",
                "status": "neutral",
                "score": score,
                "summary": "Moderate compression artifacts consistent with standard multi-pass JPEG encoding.",
            }

    elif check_name == "duplicate":
        is_near_dup = check_data.get("is_near_duplicate", False)
        matches = check_data.get("matches", [])
        best_sim = check_data.get("best_match_similarity", 0.0)

        if is_near_dup and matches:
            label = matches[0].get("label", "Unknown reference")
            return {
                "check": "duplicate",
                "status": "suspicious",
                "score": score,
                "summary": f"Perceptual near-duplicate found in reference database ('{label}' with {best_sim:.1f}% similarity).",
            }
        else:
            return {
                "check": "duplicate",
                "status": "neutral",
                "score": score,
                "summary": "No near-duplicate matches identified in the indexed reference database.",
            }

    # Default fallback
    return {
        "check": check_name,
        "status": "neutral",
        "score": score,
        "summary": f"Reported risk score: {score:.2f}.",
    }


def compute_verdict(checks: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes a synthesized verdict across all available forensic checks.

    Args:
        checks: Dictionary of check outputs produced by /analyze
                (e.g., {"metadata": {...}, "ela": {...}, "c2pa": {...}, "duplicate": {...}, "ai_detector": {...}})

    Returns:
        dict: Standardized verdict dictionary with:
              label, display_label, overall_score, confidence, reasons, evidence.
    """
    evidence: List[Dict[str, Any]] = []
    reasons: List[str] = []

    # 1. Evaluate evidence status for each recognized check in standard order
    check_order = ["ai_detector", "c2pa", "metadata", "ela", "duplicate"]
    for chk in check_order:
        chk_data = checks.get(chk)
        evidence.append(_evaluate_evidence_item(chk, chk_data))

    # 2. Dynamic Weight Renormalization
    # Only include active, functional checks with non-null scores
    active_weights: Dict[str, float] = {}
    for ev in evidence:
        chk = ev["check"]
        if ev["status"] != "unavailable" and ev["score"] is not None:
            active_weights[chk] = VERDICT_WEIGHTS.get(chk, 0.10)

    total_weight = sum(active_weights.values())

    if total_weight > 0:
        raw_weighted_score = sum(
            checks[chk]["risk_score"] * (w / total_weight)
            for chk, w in active_weights.items()
        )
    else:
        raw_weighted_score = 0.5

    overall_score = raw_weighted_score

    # 3. Check for Cryptographic and Provenance Overrides
    # 3. Check for Cryptographic, Watermark, and Provenance Overrides
    c2pa_data = checks.get("c2pa", {})
    c2pa_has_manifest = c2pa_data.get("has_manifest", False)
    c2pa_ai_flag = c2pa_data.get("ai_generated_flag", False)
    c2pa_is_valid = c2pa_data.get("is_valid")

    c2pa_ai_override = False
    if c2pa_has_manifest and c2pa_ai_flag:
        c2pa_ai_override = True
        overall_score = max(overall_score, 0.95)
        reasons.append(
            "Cryptographic Content Credentials (C2PA) explicitly certify that this image was synthesized by generative AI."
        )

    elif c2pa_has_manifest and c2pa_is_valid is True and not c2pa_ai_flag:
        # Camera or editing tool manifest verified authentic: reduce overall score
        overall_score = max(0.0, overall_score - C2PA_AUTHENTIC_SCORE_REDUCTION)
        issuer_str = f" from {c2pa_data.get('issuer')}" if c2pa_data.get("issuer") else ""
        reasons.append(
            f"Cryptographic C2PA provenance confirms verified authentic capture/editing credentials{issuer_str}."
        )

    elif c2pa_has_manifest and c2pa_is_valid is False:
        # Broken or altered C2PA signature
        overall_score = max(overall_score, 0.75)
        reasons.append(
            "C2PA manifest signature failed cryptographic validation, indicating potential tampering."
        )

    # Visual AI watermark badge override (e.g. Meta AI watermark)
    meta_data = checks.get("metadata", {})
    meta_fields = meta_data.get("fields", {})
    visual_watermark = meta_fields.get("visual_watermark")
    has_watermark_flag = any("visual ai watermark" in rf.lower() for rf in meta_data.get("red_flags", []))
    visual_ai_override = False
    if visual_watermark or has_watermark_flag:
        visual_ai_override = True
        overall_score = max(overall_score, 0.95)
        badge_name = visual_watermark or "Generative AI Badge"
        reasons.append(
            f"Visual AI watermark badge ({badge_name}) identified on image surface, confirming generative AI origin."
        )

    # Duplicate check reason
    dup_data = checks.get("duplicate", {})
    if dup_data.get("is_near_duplicate"):
        matches = dup_data.get("matches", [])
        best_label = matches[0].get("label", "known reference") if matches else "known reference"
        best_sim = dup_data.get("best_match_similarity", 100.0)
        reasons.append(
            f"Image matches known reference '{best_label}' with {best_sim:.1f}% perceptual similarity, suggesting recycled media."
        )

    # AI Detector reason
    ai_data = checks.get("ai_detector", {})
    if ai_data.get("available") and ai_data.get("ai_probability") is not None:
        ai_prob = float(ai_data["ai_probability"])
        if ai_prob >= 0.70:
            reasons.append(
                f"Deep learning vision classifier detected high-confidence AI generation artifacts ({ai_prob * 100:.1f}% probability)."
            )
        elif ai_prob <= 0.25:
            reasons.append(
                f"Deep learning vision classifier detected natural pixel patterns consistent with authentic photography ({ai_prob * 100:.1f}% AI probability)."
            )

    # Metadata reasons & honesty rule
    red_flags = meta_data.get("red_flags", [])
    has_exif = meta_data.get("has_exif", False)
    software_flags = [rf for rf in red_flags if "software" in rf.lower() or ("ai" in rf.lower() and "visual" not in rf.lower())]

    if software_flags:
        reasons.append(f"Image container metadata contains editing software fingerprints: {'; '.join(software_flags)}.")
    elif not has_exif and not visual_ai_override:
        reasons.append(
            "EXIF camera metadata is absent; this is common on social media and is treated as a neutral indicator."
        )

    # ELA reason
    ela_data = checks.get("ela", {})
    if ela_data.get("risk_score", 0.0) >= 0.40:
        reasons.append(
            "Error Level Analysis (ELA) detected compression inconsistencies, which can indicate digital splicing or high-contrast graphics."
        )

    # Bound overall_score strictly to [0.0, 1.0]
    overall_score = max(0.0, min(1.0, round(overall_score, 4)))

    # 4. Categorical Label Determination
    ai_detector_available = ai_data.get("available", True)

    if c2pa_ai_override or visual_ai_override:
        label = "likely_ai_generated"
    elif overall_score >= VERDICT_THRESHOLD_AI:
        label = "likely_ai_generated"
    elif overall_score >= VERDICT_THRESHOLD_MANIPULATED:
        label = "possibly_manipulated"
    elif overall_score < VERDICT_THRESHOLD_AUTHENTIC:
        label = "likely_authentic"
    else:
        label = "inconclusive"

    # Special handling: if ai_detector is unavailable and no strong signals exist
    if not ai_detector_available and label in ["likely_ai_generated", "inconclusive"]:
        strong_signals = (
            c2pa_ai_override
            or visual_ai_override
            or bool(software_flags)
            or (dup_data.get("is_near_duplicate", False))
            or (ela_data.get("risk_score", 0.0) >= 0.6)
        )
        if not strong_signals:
            label = "inconclusive"
            if not any("AI detector was unavailable" in r for r in reasons):
                reasons.append("The primary AI detector was unavailable, and other forensic signals were neutral or inconclusive.")

    display_label = DISPLAY_LABELS.get(label, "Inconclusive")

    # 5. Confidence Calculation
    if c2pa_ai_override or visual_ai_override:
        confidence = "high"
    elif len(active_weights) <= 2:
        confidence = "low"
    else:
        # Measure agreement between active check scores
        active_scores = [checks[c]["risk_score"] for c in active_weights]
        score_spread = max(active_scores) - min(active_scores) if active_scores else 0.0

        if score_spread > 0.60:
            confidence = "low"
            reasons.append("Available forensic checks returned mixed signals with high variance across detection vectors.")
        elif score_spread < 0.30 or (overall_score >= 0.80 or overall_score <= 0.20):
            confidence = "high"
        else:
            confidence = "medium"

    # Ensure at least one informative reason is present
    if not reasons:
        reasons.append(
            f"Overall suspicion score of {overall_score:.2f} based on weighted synthesis of active forensic signals."
        )

    return {
        "label": label,
        "display_label": display_label,
        "overall_score": overall_score,
        "confidence": confidence,
        "reasons": reasons,
        "evidence": evidence,
    }
