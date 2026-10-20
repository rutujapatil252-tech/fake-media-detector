"""
Comprehensive test suite for Fake Media Detector (Phase 1).

Tests generate small, synthetic test images entirely in memory (no external files required),
verifying:
- Returned dictionary keys and schema compliance
- Numerical metric bounds (risk scores, ratios, errors)
- Error Level Analysis (ELA) behavior and dimension scaling
- Metadata extraction and red flag detection
- FastAPI API endpoints (/health, /analyze) and error handling
"""

import io
from PIL import Image, ImageDraw
import piexif
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.checks.metadata import analyze_metadata
from app.checks.ela import analyze_ela
from app.config import MAX_FILE_SIZE_BYTES


# Initialize FastAPI TestClient
client = TestClient(app)


def create_test_image(
    format_type: str = "JPEG",
    width: int = 100,
    height: int = 100,
    color: tuple = (120, 150, 180),
    add_shapes: bool = True,
    software_tag: str | None = None,
    make_model: tuple | None = None,
) -> bytes:
    """
    Utility function to create test images entirely in memory.
    Supports injecting EXIF tags (such as software and camera make/model).
    """
    img = Image.new("RGB", (width, height), color=color)
    if add_shapes:
        draw = ImageDraw.Draw(img)
        draw.rectangle([10, 10, width // 2, height // 2], fill=(255, 50, 50))
        draw.ellipse([width // 2, height // 2, width - 10, height - 10], fill=(50, 255, 50))

    buf = io.BytesIO()

    # Build optional EXIF data using piexif if tags requested for JPEG
    exif_bytes = None
    if format_type.upper() == "JPEG" and (software_tag or make_model):
        zeroth_ifd = {}
        if software_tag:
            zeroth_ifd[piexif.ImageIFD.Software] = software_tag.encode("utf-8")
        if make_model:
            zeroth_ifd[piexif.ImageIFD.Make] = make_model[0].encode("utf-8")
            zeroth_ifd[piexif.ImageIFD.Model] = make_model[1].encode("utf-8")
        exif_dict = {"0th": zeroth_ifd, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        exif_bytes = piexif.dump(exif_dict)

    if exif_bytes:
        img.save(buf, format=format_type, quality=95, exif=exif_bytes)
    else:
        img.save(buf, format=format_type, quality=95)

    return buf.getvalue()


# ============================================================================
# METADATA CHECK TESTS
# ============================================================================

def test_metadata_check_keys_and_score_range():
    """Verify analyze_metadata returns all mandatory keys and score within [0.0, 1.0]."""
    img_bytes = create_test_image("JPEG")
    res = analyze_metadata(img_bytes)

    assert "has_exif" in res
    assert "fields" in res
    assert "red_flags" in res
    assert "risk_score" in res

    assert isinstance(res["has_exif"], bool)
    assert isinstance(res["fields"], dict)
    assert isinstance(res["red_flags"], list)
    assert isinstance(res["risk_score"], float)
    assert 0.0 <= res["risk_score"] <= 1.0


def test_metadata_detects_clean_camera_photo():
    """Verify camera photos with legitimate make/model get low risk score."""
    img_bytes = create_test_image("JPEG", make_model=("Canon", "EOS R5"))
    res = analyze_metadata(img_bytes)

    assert res["has_exif"] is True
    assert res["fields"].get("make") == "Canon"
    assert res["fields"].get("model") == "EOS R5"
    assert res["risk_score"] <= 0.20


def test_metadata_detects_editing_software_red_flag():
    """Verify metadata check flags Adobe Photoshop in software tag."""
    img_bytes = create_test_image("JPEG", software_tag="Adobe Photoshop 2024 (Windows)")
    res = analyze_metadata(img_bytes)

    assert res["has_exif"] is True
    assert any("editing software detected" in rf.lower() for rf in res["red_flags"])
    assert res["risk_score"] >= 0.50


def test_metadata_detects_ai_tool_red_flag():
    """Verify metadata check flags Midjourney in software tag."""
    img_bytes = create_test_image("JPEG", software_tag="Midjourney v6.0")
    res = analyze_metadata(img_bytes)

    assert res["has_exif"] is True
    assert any("ai generation signature detected" in rf.lower() for rf in res["red_flags"])
    assert res["risk_score"] >= 0.80


def test_metadata_no_exif_flag():
    """Verify missing EXIF adds the expected weak-signal advisory flag."""
    # PNG created without EXIF
    img_bytes = create_test_image("PNG")
    res = analyze_metadata(img_bytes)

    assert res["has_exif"] is False
    assert any("no exif metadata found" in rf.lower() for rf in res["red_flags"])
    assert 0.0 <= res["risk_score"] <= 1.0


# ============================================================================
# ERROR LEVEL ANALYSIS (ELA) TESTS
# ============================================================================

def test_ela_check_keys_and_score_range():
    """Verify analyze_ela returns all required keys and metrics within valid bounds."""
    img_bytes = create_test_image("JPEG", width=120, height=120)
    res = analyze_ela(img_bytes)

    assert "heatmap_base64" in res
    assert "mean_error" in res
    assert "max_error" in res
    assert "suspicious_region_ratio" in res
    assert "risk_score" in res

    assert isinstance(res["heatmap_base64"], str)
    assert len(res["heatmap_base64"]) > 50
    assert isinstance(res["mean_error"], float)
    assert isinstance(res["max_error"], float)
    assert isinstance(res["suspicious_region_ratio"], float)
    assert isinstance(res["risk_score"], float)

    assert res["mean_error"] >= 0.0
    assert res["max_error"] >= res["mean_error"]
    assert 0.0 <= res["suspicious_region_ratio"] <= 1.0
    assert 0.0 <= res["risk_score"] <= 1.0


def test_ela_resizes_oversized_images():
    """Verify large images exceeding 1024px are downscaled and successfully analyzed."""
    large_img_bytes = create_test_image("JPEG", width=1400, height=1100)
    res = analyze_ela(large_img_bytes)

    assert res["risk_score"] >= 0.0
    assert len(res["heatmap_base64"]) > 0


# ============================================================================
# API ENDPOINT TESTS (/health and /analyze)
# ============================================================================

def test_health_endpoint():
    """Test GET /health returns 200 and {'status': 'ok'}."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_valid_jpeg():
    """Test POST /analyze with valid JPEG file returns expected JSON structure."""
    img_bytes = create_test_image("JPEG")
    files = {"file": ("sample.jpg", img_bytes, "image/jpeg")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "sample.jpg"
    assert "checks" in data
    assert "metadata" in data["checks"]
    assert "ela" in data["checks"]

    meta = data["checks"]["metadata"]
    ela = data["checks"]["ela"]
    assert "risk_score" in meta
    assert "risk_score" in ela
    assert "heatmap_base64" in ela


def test_analyze_endpoint_valid_png():
    """Test POST /analyze with valid PNG file."""
    img_bytes = create_test_image("PNG")
    files = {"file": ("graphic.png", img_bytes, "image/png")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 200
    assert response.json()["filename"] == "graphic.png"


def test_analyze_endpoint_invalid_extension():
    """Test POST /analyze rejects unsupported extensions with 400 Bad Request."""
    files = {"file": ("document.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 400
    assert "unsupported file extension" in response.json()["detail"].lower()


def test_analyze_endpoint_invalid_mime():
    """Test POST /analyze rejects disallowed MIME types with 400 Bad Request."""
    img_bytes = create_test_image("JPEG")
    files = {"file": ("test.jpg", img_bytes, "text/plain")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 400
    assert "unsupported media type" in response.json()["detail"].lower()


def test_analyze_endpoint_empty_file():
    """Test POST /analyze rejects 0-byte uploads with 400 Bad Request."""
    files = {"file": ("empty.jpg", b"", "image/jpeg")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_analyze_endpoint_corrupted_image():
    """Test POST /analyze rejects non-image byte content with 400 Bad Request."""
    files = {"file": ("corrupt.jpg", b"not a real image payload", "image/jpeg")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 400
    assert "not a valid or readable image" in response.json()["detail"].lower()


def test_analyze_endpoint_oversized_file():
    """Test POST /analyze rejects files exceeding MAX_FILE_SIZE_BYTES."""
    oversized_data = b"X" * (MAX_FILE_SIZE_BYTES + 1024)
    files = {"file": ("huge.jpg", oversized_data, "image/jpeg")}
    response = client.post("/analyze", files=files)

    assert response.status_code == 400
    assert "exceeds maximum limit" in response.json()["detail"].lower()
