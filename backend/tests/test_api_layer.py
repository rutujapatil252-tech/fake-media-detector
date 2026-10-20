"""
API Layer Unit and Integration Tests for Fake Media Detector.

Tests FastAPI endpoints (/health, /analyze, /reference/add, /reference/list)
using starlette/fastapi TestClient with mocked AI detector for ultra-fast,
deterministic CI execution.
"""

import io
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app
from app.config import MAX_FILE_SIZE_BYTES

client = TestClient(app)

# Standard mock return for the heavy AI vision classifier
MOCK_AI_CHECK_RESULT = {
    "ai_probability": 0.05,
    "risk_score": 0.05,
    "summary": "Deep learning vision classifier detected natural pixel patterns (5.0% AI probability).",
    "model_name": "Organika/sdxl-detector",
    "classification": "human_created",
    "raw_scores": {"artificial": 0.05, "human": 0.95},
}


def _create_jpeg_bytes(width=100, height=100, color=(100, 150, 200)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _create_png_bytes(width=100, height=100, color=(200, 100, 50)) -> bytes:
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def test_api_health_endpoint():
    """GET /health returns 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_analyze_invalid_extension_returns_400():
    """POST /analyze rejects unsupported file extensions with 400 Bad Request."""
    response = client.post(
        "/analyze",
        files={"file": ("malicious.exe", b"MZ\x90\x00\x03\x00\x00\x00", "application/octet-stream")},
    )
    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"]


def test_api_analyze_invalid_mime_type_returns_400():
    """POST /analyze rejects unsupported MIME types with 400 Bad Request."""
    response = client.post(
        "/analyze",
        files={"file": ("document.jpg", b"fake-content", "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported media type" in response.json()["detail"]


def test_api_analyze_empty_file_returns_400():
    """POST /analyze rejects 0-byte uploads with 400 Bad Request."""
    response = client.post(
        "/analyze",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_api_analyze_oversized_file_returns_400():
    """POST /analyze rejects files exceeding the 10 MB limit with 400 Bad Request."""
    oversized_bytes = b"0" * (MAX_FILE_SIZE_BYTES + 1024)
    response = client.post(
        "/analyze",
        files={"file": ("huge.jpg", oversized_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "exceeds maximum limit" in response.json()["detail"].lower()


def test_api_analyze_corrupted_image_returns_400():
    """POST /analyze rejects un-decodable random bytes with 400 Bad Request."""
    corrupted_bytes = b"JFIF\x00\x01\x01" + b"\xff\xd8\xff" * 50
    response = client.post(
        "/analyze",
        files={"file": ("corrupted.jpg", corrupted_bytes, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "not a valid or readable image" in response.json()["detail"]


@patch("app.checks.ai_detector.analyze_ai_generated", return_value=MOCK_AI_CHECK_RESULT)
def test_api_analyze_valid_jpeg_returns_full_schema(mock_ai):
    """POST /analyze with valid JPEG returns complete contract: checks, verdict, and processing_time_ms."""
    jpeg_bytes = _create_jpeg_bytes()
    response = client.post(
        "/analyze",
        files={"file": ("photo.jpg", jpeg_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    data = response.json()

    # File header
    assert data["filename"] == "photo.jpg"

    # All 5 forensic checks present
    checks = data["checks"]
    assert "metadata" in checks
    assert "ela" in checks
    assert "c2pa" in checks
    assert "duplicate" in checks
    assert "ai_detector" in checks

    # Phase 4 Verdict object
    verdict = data["verdict"]
    assert verdict["label"] in [
        "likely_ai_generated",
        "possibly_manipulated",
        "likely_authentic",
        "inconclusive",
    ]
    assert isinstance(verdict["display_label"], str)
    assert 0.0 <= verdict["overall_score"] <= 1.0
    assert verdict["confidence"] in ["high", "medium", "low"]
    assert isinstance(verdict["reasons"], list)
    assert isinstance(verdict["evidence"], list)
    assert len(verdict["evidence"]) == 5

    # Timing
    assert "processing_time_ms" in data
    assert isinstance(data["processing_time_ms"], (int, float))
    assert data["processing_time_ms"] > 0


@patch("app.checks.ai_detector.analyze_ai_generated", return_value=MOCK_AI_CHECK_RESULT)
def test_api_analyze_valid_png_returns_full_schema(mock_ai):
    """POST /analyze handles valid PNG uploads smoothly."""
    png_bytes = _create_png_bytes()
    response = client.post(
        "/analyze",
        files={"file": ("diagram.png", png_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "diagram.png"
    assert "verdict" in data
    assert "checks" in data
    assert "processing_time_ms" in data


def test_api_reference_add_and_list():
    """POST /reference/add and GET /reference/list work end-to-end."""
    img_bytes = _create_jpeg_bytes(color=(120, 40, 80))
    add_res = client.post(
        "/reference/add",
        data={"label": "PyTest Reference Asset"},
        files={"file": ("ref.jpg", img_bytes, "image/jpeg")},
    )
    assert add_res.status_code == 200
    add_data = add_res.json()
    assert add_data["status"] in ["added", "success"]
    assert "id" in add_data

    list_res = client.get("/reference/list")
    assert list_res.status_code == 200
    list_data = list_res.json()
    assert "references" in list_data
    assert list_data["count"] >= 1
    assert any(r["label"] == "PyTest Reference Asset" for r in list_data["references"])
