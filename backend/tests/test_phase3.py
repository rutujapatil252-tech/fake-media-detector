"""
Unit and Integration Tests for Fake Media Detector Phase 3 (AI-Generated Image Detector).

Covers:
- Label mapping helper across different model architectures (artificial/human, AI/Real, fake/real)
- Decision threshold categorization (likely_ai, uncertain, likely_real)
- Graceful offline / model load failure handling (available=False without raising)
- Pipeline mock testing for fast execution without network downloads
- Optional live model integration test (enabled when RUN_MODEL_TESTS=1)
- API endpoint integration: POST /analyze returns all five checks
"""

import io
import os
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.checks.ai_detector import (
    analyze_ai_generated,
    assign_categorical_label,
    map_predictions_to_ai_probability,
)
from app.config import (
    AI_PROBABILITY_HIGH_THRESHOLD,
    AI_PROBABILITY_LOW_THRESHOLD,
)

client = TestClient(app)


def make_test_image(format_type: str = "JPEG", size: tuple = (100, 100)) -> bytes:
    """Helper to generate minimal in-memory test image bytes."""
    img = Image.new("RGB", size, color=(150, 180, 210))
    buf = io.BytesIO()
    img.save(buf, format=format_type)
    return buf.getvalue()


# ============================================================================
# LABEL MAPPING TESTS
# ============================================================================

def test_label_mapping_artificial_human():
    """Verify mapping for Organika/sdxl-detector style labels ('artificial', 'human')."""
    preds_ai = [{"label": "artificial", "score": 0.88}, {"label": "human", "score": 0.12}]
    assert map_predictions_to_ai_probability(preds_ai) == 0.88

    preds_real = [{"label": "human", "score": 0.95}, {"label": "artificial", "score": 0.05}]
    assert map_predictions_to_ai_probability(preds_real) == 0.05


def test_label_mapping_ai_real():
    """Verify mapping for umm-maybe/AI-image-detector style labels ('AI', 'Real')."""
    preds_ai = [{"label": "AI", "score": 0.74}, {"label": "Real", "score": 0.26}]
    assert map_predictions_to_ai_probability(preds_ai) == 0.74

    preds_real = [{"label": "Real", "score": 0.82}, {"label": "AI", "score": 0.18}]
    assert map_predictions_to_ai_probability(preds_real) == 0.18


def test_label_mapping_fake_real():
    """Verify mapping for dima806/ai_vs_real_image_detection style labels ('fake', 'real')."""
    preds_ai = [{"label": "fake", "score": 0.91}, {"label": "real", "score": 0.09}]
    assert map_predictions_to_ai_probability(preds_ai) == 0.91

    preds_real = [{"label": "real", "score": 0.99}, {"label": "fake", "score": 0.01}]
    assert map_predictions_to_ai_probability(preds_real) == 0.01


def test_label_mapping_empty_and_fallback():
    """Verify safe fallback for empty or unrecognized labels."""
    assert map_predictions_to_ai_probability([]) == 0.5


# ============================================================================
# THRESHOLD CATEGORIZATION TESTS
# ============================================================================

def test_categorical_label_assignment():
    """Verify decision thresholds produce 'likely_ai', 'uncertain', and 'likely_real'."""
    # High score >= 0.7
    assert assign_categorical_label(0.70) == "likely_ai"
    assert assign_categorical_label(0.95) == "likely_ai"

    # Mid score 0.4 <= score < 0.7
    assert assign_categorical_label(0.50) == "uncertain"
    assert assign_categorical_label(0.69) == "uncertain"
    assert assign_categorical_label(0.40) == "uncertain"

    # Low score < 0.4
    assert assign_categorical_label(0.39) == "likely_real"
    assert assign_categorical_label(0.05) == "likely_real"


# ============================================================================
# MOCKED PIPELINE INFERENCE TESTS (FAST & ISOLATED)
# ============================================================================

def test_analyze_ai_generated_mocked_likely_ai():
    """Verify analyze_ai_generated returns correct structure when model flags AI image."""
    mock_clf = MagicMock(return_value=[
        {"label": "artificial", "score": 0.85},
        {"label": "human", "score": 0.15},
    ])

    with patch("app.checks.ai_detector.get_ai_classifier", return_value=(mock_clf, "mock-model", None)):
        img_bytes = make_test_image()
        result = analyze_ai_generated(img_bytes)

        assert result["available"] is True
        assert result["model_name"] == "mock-model"
        assert result["ai_probability"] == 0.85
        assert result["label"] == "likely_ai"
        assert result["risk_score"] == 0.85
        assert result["error"] is None
        assert "note" in result


def test_analyze_ai_generated_mocked_likely_real():
    """Verify analyze_ai_generated returns correct structure for human-created image."""
    mock_clf = MagicMock(return_value=[
        {"label": "human", "score": 0.92},
        {"label": "artificial", "score": 0.08},
    ])

    with patch("app.checks.ai_detector.get_ai_classifier", return_value=(mock_clf, "mock-model", None)):
        img_bytes = make_test_image()
        result = analyze_ai_generated(img_bytes)

        assert result["available"] is True
        assert result["ai_probability"] == 0.08
        assert result["label"] == "likely_real"
        assert result["risk_score"] == 0.08


def test_analyze_ai_generated_handles_load_failure_gracefully():
    """Verify that failure to load model sets available=False without crashing /analyze."""
    with patch(
        "app.checks.ai_detector.get_ai_classifier",
        return_value=(None, "Organika/sdxl-detector", "Network unreachable or offline"),
    ):
        img_bytes = make_test_image()
        result = analyze_ai_generated(img_bytes)

        assert result["available"] is False
        assert result["ai_probability"] == 0.5
        assert result["label"] == "uncertain"
        assert result["risk_score"] == 0.5
        assert "Network unreachable" in result["error"]


def test_api_analyze_contains_all_five_checks():
    """Verify POST /analyze returns metadata, ela, c2pa, duplicate, and ai_detector."""
    img_bytes = make_test_image("PNG")
    files = {"file": ("query.png", img_bytes, "image/png")}

    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()

    assert "checks" in data
    checks = data["checks"]

    # All five checks present
    assert "metadata" in checks
    assert "ela" in checks
    assert "c2pa" in checks
    assert "duplicate" in checks
    assert "ai_detector" in checks

    ai_check = checks["ai_detector"]
    assert "ai_probability" in ai_check
    assert "label" in ai_check
    assert "risk_score" in ai_check
    assert 0.0 <= ai_check["risk_score"] <= 1.0


# ============================================================================
# OPTIONAL LIVE MODEL INTEGRATION TEST
# ============================================================================

@pytest.mark.skipif(
    os.environ.get("RUN_MODEL_TESTS") != "1",
    reason="Live model test skipped unless RUN_MODEL_TESTS=1 is set",
)
def test_real_model_inference_live():
    """Optional live integration test executing real model weights on an in-memory image."""
    img_bytes = make_test_image("JPEG")
    res = analyze_ai_generated(img_bytes)

    assert res["available"] is True
    assert isinstance(res["ai_probability"], float)
    assert 0.0 <= res["ai_probability"] <= 1.0
    assert res["label"] in ["likely_ai", "uncertain", "likely_real"]
