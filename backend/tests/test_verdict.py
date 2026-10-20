"""
Unit Tests for Fake Media Detector Phase 4 Verdict Engine.

Verifies:
- Cryptographic C2PA AI override (label=likely_ai_generated, confidence=high)
- Authentic camera C2PA score reduction
- All checks clean produces likely_authentic
- All checks suspicious produces likely_ai_generated
- Mixed conflicting signals produce low confidence
- Unavailable ai_detector triggers weight renormalization and safe inconclusive handling
- Math constraints: overall_score always strictly bounded in [0.0, 1.0]
- Evidence items format and status categorization
"""

import pytest
from app.verdict import compute_verdict


def test_verdict_c2pa_ai_override():
    """Verify that a C2PA manifest with ai_generated_flag=True forces likely_ai_generated with high confidence."""
    checks = {
        "c2pa": {
            "has_manifest": True,
            "is_valid": True,
            "issuer": "Adobe Trust",
            "ai_generated_flag": True,
            "risk_score": 0.95,
        },
        # Even if other checks look clean:
        "ai_detector": {"available": True, "ai_probability": 0.10, "risk_score": 0.10},
        "metadata": {"has_exif": True, "red_flags": [], "risk_score": 0.10},
        "ela": {"risk_score": 0.05, "suspicious_region_ratio": 0.0},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert verdict["label"] == "likely_ai_generated"
    assert verdict["display_label"] == "Likely AI-generated"
    assert verdict["confidence"] == "high"
    assert verdict["overall_score"] >= 0.95
    assert any("C2PA" in r and "generative AI" in r for r in verdict["reasons"])


def test_verdict_all_checks_clean():
    """Verify that when all checks report clean, authentic indicators, label is likely_authentic."""
    checks = {
        "ai_detector": {"available": True, "ai_probability": 0.05, "label": "likely_real", "risk_score": 0.05},
        "c2pa": {"has_manifest": True, "is_valid": True, "issuer": "Canon Camera PKI", "ai_generated_flag": False, "risk_score": 0.10},
        "metadata": {"has_exif": True, "fields": {"make": "Canon", "model": "EOS R5"}, "red_flags": [], "risk_score": 0.10},
        "ela": {"risk_score": 0.05, "suspicious_region_ratio": 0.0},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert verdict["label"] == "likely_authentic"
    assert verdict["display_label"] == "Likely Authentic"
    assert verdict["overall_score"] < 0.30
    assert 0.0 <= verdict["overall_score"] <= 1.0


def test_verdict_all_checks_suspicious():
    """Verify that when all checks indicate manipulation/synthesis, label is likely_ai_generated."""
    checks = {
        "ai_detector": {"available": True, "ai_probability": 0.92, "label": "likely_ai", "risk_score": 0.92},
        "c2pa": {"has_manifest": False, "risk_score": 0.50},
        "metadata": {"has_exif": True, "red_flags": ["Software: Adobe Photoshop"], "risk_score": 0.80},
        "ela": {"risk_score": 0.75, "suspicious_region_ratio": 0.12},
        "duplicate": {"is_near_duplicate": True, "best_match_similarity": 95.0, "risk_score": 0.80},
    }

    verdict = compute_verdict(checks)
    assert verdict["label"] == "likely_ai_generated"
    assert verdict["overall_score"] >= 0.65
    assert 0.0 <= verdict["overall_score"] <= 1.0


def test_verdict_mixed_signals_low_confidence():
    """Verify that when active checks disagree strongly, confidence is low."""
    checks = {
        # AI detector says highly suspicious
        "ai_detector": {"available": True, "ai_probability": 0.90, "label": "likely_ai", "risk_score": 0.90},
        # Metadata and ELA report very clean camera photo
        "metadata": {"has_exif": True, "fields": {"make": "Sony", "model": "A7 IV"}, "red_flags": [], "risk_score": 0.05},
        "ela": {"risk_score": 0.05, "suspicious_region_ratio": 0.0},
        "c2pa": {"has_manifest": False, "risk_score": 0.50},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert verdict["confidence"] == "low"
    assert any("mixed signals" in r.lower() for r in verdict["reasons"])


def test_verdict_unavailable_ai_detector_and_weight_renormalization():
    """Verify that an unavailable ai_detector is excluded and weights renormalize without crash."""
    checks = {
        "ai_detector": {"available": False, "error": "Model offline"},
        "metadata": {"has_exif": True, "fields": {"make": "Nikon"}, "red_flags": [], "risk_score": 0.10},
        "ela": {"risk_score": 0.10, "suspicious_region_ratio": 0.0},
        "c2pa": {"has_manifest": False, "risk_score": 0.50},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert 0.0 <= verdict["overall_score"] <= 1.0

    # Evidence item for ai_detector should be marked unavailable
    ai_ev = next(ev for ev in verdict["evidence"] if ev["check"] == "ai_detector")
    assert ai_ev["status"] == "unavailable"
    assert ai_ev["score"] is None

    # Inconclusive when primary detector unavailable and signals neutral
    assert verdict["label"] in ["likely_authentic", "inconclusive"]


def test_verdict_scores_strictly_bounded():
    """Verify boundary conditions: scores never fall below 0.0 or exceed 1.0."""
    # Extreme lower bound
    lowest_checks = {
        "ai_detector": {"available": True, "ai_probability": 0.0, "risk_score": 0.0},
        "c2pa": {"has_manifest": True, "is_valid": True, "ai_generated_flag": False, "risk_score": 0.0},
        "metadata": {"has_exif": True, "red_flags": [], "risk_score": 0.0},
        "ela": {"risk_score": 0.0, "suspicious_region_ratio": 0.0},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.0},
    }
    res_low = compute_verdict(lowest_checks)
    assert res_low["overall_score"] == 0.0

    # Extreme upper bound
    highest_checks = {
        "ai_detector": {"available": True, "ai_probability": 1.0, "risk_score": 1.0},
        "c2pa": {"has_manifest": True, "is_valid": False, "ai_generated_flag": True, "risk_score": 1.0},
        "metadata": {"has_exif": False, "red_flags": ["Software: Midjourney"], "risk_score": 1.0},
        "ela": {"risk_score": 1.0, "suspicious_region_ratio": 0.8},
        "duplicate": {"is_near_duplicate": True, "risk_score": 1.0},
    }
    res_high = compute_verdict(highest_checks)
    assert res_high["overall_score"] == 1.0


def test_verdict_c2pa_tampered_manifest_pushes_suspicious():
    """Verify that an invalid C2PA signature pushes suspicion score upward."""
    checks = {
        "c2pa": {
            "has_manifest": True,
            "is_valid": False,
            "ai_generated_flag": False,
            "risk_score": 0.90,
            "validation_errors": ["Signature mismatch"],
        },
        "ai_detector": {"available": True, "ai_probability": 0.20, "risk_score": 0.20},
        "metadata": {"has_exif": False, "risk_score": 0.35},
        "ela": {"risk_score": 0.10, "suspicious_region_ratio": 0.0},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert verdict["overall_score"] >= 0.70
    assert any("tampering" in r.lower() or "validation failed" in r.lower() for r in verdict["reasons"])


def test_verdict_visual_ai_watermark_override():
    """Verify that detecting a visual AI watermark forces likely_ai_generated with high confidence."""
    checks = {
        "c2pa": {"has_manifest": False, "risk_score": 0.50},
        "ai_detector": {"available": True, "ai_probability": 0.05, "risk_score": 0.05},
        "metadata": {
            "has_exif": False,
            "fields": {"visual_watermark": "Meta AI (Generative AI Badge)"},
            "red_flags": ["Visual AI watermark badge detected: 'Meta AI'"],
            "risk_score": 0.95,
        },
        "ela": {"risk_score": 0.05, "suspicious_region_ratio": 0.0},
        "duplicate": {"is_near_duplicate": False, "risk_score": 0.50},
    }

    verdict = compute_verdict(checks)
    assert verdict["label"] == "likely_ai_generated"
    assert verdict["confidence"] == "high"
    assert verdict["overall_score"] >= 0.95
    assert any("visual ai watermark badge" in r.lower() for r in verdict["reasons"])

