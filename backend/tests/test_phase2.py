"""
Unit and Integration Tests for Fake Media Detector Phase 2.

Covers:
- C2PA provenance check (no crash on plain images, proper keys, fallback behavior, score bounds)
- Perceptual hash generation (pHash, aHash, dHash, wHash)
- SQLite database isolation using temporary directories
- Exact duplicate detection
- Near-duplicate detection under resizing and recompression
- Non-duplicate rejection with completely different imagery
- API endpoints: POST /reference/add, GET /reference/list, POST /analyze containing all 4 checks
"""

import io
from pathlib import Path
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.checks.c2pa_check import analyze_c2pa, _detect_ai_declaration
from app.checks.duplicate import (
    add_reference,
    analyze_duplicate,
    compute_hashes,
    find_matches,
    list_references,
)
from app.config import (
    C2PA_NEUTRAL_RISK,
    DUPLICATE_MATCH_RISK,
    DUPLICATE_NEUTRAL_RISK,
)

client = TestClient(app)


def make_pattern_image(
    primary_color: tuple = (200, 40, 40),
    secondary_color: tuple = (40, 200, 40),
    size: tuple[int, int] = (120, 120),
    pattern: str = "cross",
    format_type: str = "JPEG",
    quality: int = 95,
) -> bytes:
    """Helper to generate deterministic in-memory images with distinct visual patterns."""
    img = Image.new("RGB", size, color=primary_color)
    draw = ImageDraw.Draw(img)
    w, h = size

    if pattern == "cross":
        draw.line([(0, 0), (w, h)], fill=secondary_color, width=10)
        draw.line([(0, h), (w, 0)], fill=secondary_color, width=10)
    elif pattern == "circles":
        for r in range(10, min(w, h) // 2, 15):
            draw.ellipse([w // 2 - r, h // 2 - r, w // 2 + r, h // 2 + r], outline=secondary_color, width=4)
    elif pattern == "bars":
        for x in range(0, w, 20):
            draw.rectangle([x, 0, x + 10, h], fill=secondary_color)

    buf = io.BytesIO()
    img.save(buf, format=format_type, quality=quality)
    return buf.getvalue()


# ============================================================================
# C2PA PROVENANCE CHECK TESTS
# ============================================================================

def test_c2pa_plain_image_no_manifest_does_not_crash():
    """Verify that a plain image without C2PA metadata returns has_manifest=False cleanly."""
    img_bytes = make_pattern_image()
    res = analyze_c2pa(img_bytes)

    assert isinstance(res, dict)
    assert res["has_manifest"] is False
    assert res["is_valid"] is None
    assert res["issuer"] is None
    assert res["claim_generator"] is None
    assert isinstance(res["actions"], list)
    assert res["ai_generated_flag"] is False
    assert isinstance(res["validation_errors"], list)
    assert 0.0 <= res["risk_score"] <= 1.0
    # Missing manifest is neutral (0.5), not evidence of tampering
    assert res["risk_score"] == C2PA_NEUTRAL_RISK
    assert res["note"] is not None


def test_c2pa_invalid_bytes_handled_gracefully():
    """Verify that malformed or non-image bytes return an error without crashing the service."""
    garbage_bytes = b"not a valid image or manifest binary stream"
    res = analyze_c2pa(garbage_bytes)

    assert isinstance(res, dict)
    assert res["has_manifest"] is False
    assert 0.0 <= res["risk_score"] <= 1.0


def test_c2pa_ai_declaration_detection_logic():
    """Verify detection of Generative AI assertions in C2PA manifests."""
    # Test digitalSourceType in actions
    active_manifest_with_ai = {
        "claim_generator": "Adobe Photoshop 2025",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia",
                        }
                    ]
                },
            }
        ],
    }
    assert _detect_ai_declaration({}, active_manifest_with_ai) is True

    # Test claim_generator containing AI tool name
    active_manifest_midjourney = {
        "claim_generator": "Midjourney v6.0",
        "assertions": [],
    }
    assert _detect_ai_declaration({}, active_manifest_midjourney) is True

    # Test clean human edit manifest
    active_manifest_camera = {
        "claim_generator": "Nikon Z9 Firmware 4.0",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "digitalSourceType": "http://cv.iptc.org/newscodes/digitalsourcetype/digitalCapture",
                        }
                    ]
                },
            }
        ],
    }
    assert _detect_ai_declaration({}, active_manifest_camera) is False


# ============================================================================
# PERCEPTUAL HASHING & DUPLICATE DETECTION TESTS
# ============================================================================

def test_compute_hashes_returns_all_four_algorithms():
    """Verify that compute_hashes produces pHash, aHash, dHash, and wHash hex strings."""
    img_bytes = make_pattern_image()
    hashes = compute_hashes(img_bytes)

    assert "phash" in hashes
    assert "ahash" in hashes
    assert "dhash" in hashes
    assert "whash" in hashes

    for algo, val in hashes.items():
        assert isinstance(val, str)
        assert len(val) > 0


def test_duplicate_exact_match(tmp_path: Path):
    """Verify that indexing an image and querying the exact same image flags is_near_duplicate=True."""
    db_file = tmp_path / "test_hashes.db"
    img_bytes = make_pattern_image(pattern="cross")

    ref_id = add_reference(img_bytes, label="Reference Cross", db_path=db_file)
    assert ref_id > 0

    res = analyze_duplicate(img_bytes, db_path=db_file)
    assert res["is_near_duplicate"] is True
    assert res["best_match_similarity"] == 100.0
    assert res["risk_score"] == DUPLICATE_MATCH_RISK
    assert len(res["matches"]) == 1
    assert res["matches"][0]["label"] == "Reference Cross"
    assert res["matches"][0]["hamming_distances"]["phash"] == 0


def test_duplicate_resized_and_recompressed_match(tmp_path: Path):
    """Verify perceptual hashing detects near-duplicates across resizing and JPEG recompression."""
    db_file = tmp_path / "test_hashes.db"

    # Reference original (120x120 JPEG quality 95)
    orig_bytes = make_pattern_image(size=(120, 120), pattern="cross", quality=95)
    add_reference(orig_bytes, label="Original Target", db_path=db_file)

    # Slightly resized copy (80x80) with heavier recompression (quality 50)
    resized_recompressed = make_pattern_image(size=(80, 80), pattern="cross", quality=50)

    res = analyze_duplicate(resized_recompressed, db_path=db_file)
    assert res["is_near_duplicate"] is True
    assert res["best_match_similarity"] >= 85.0
    assert res["risk_score"] == DUPLICATE_MATCH_RISK
    assert res["matches"][0]["label"] == "Original Target"


def test_duplicate_completely_different_image_no_match(tmp_path: Path):
    """Verify that a completely different visual image is rejected as a duplicate."""
    db_file = tmp_path / "test_hashes.db"

    # Add reference image (red/green cross)
    ref_bytes = make_pattern_image(primary_color=(255, 0, 0), secondary_color=(0, 255, 0), pattern="cross")
    add_reference(ref_bytes, label="Red Cross", db_path=db_file)

    # Query with a completely different image (blue bars on black background)
    diff_bytes = make_pattern_image(primary_color=(0, 0, 0), secondary_color=(0, 100, 255), pattern="bars")

    res = analyze_duplicate(diff_bytes, db_path=db_file)
    assert res["is_near_duplicate"] is False
    assert res["risk_score"] == DUPLICATE_NEUTRAL_RISK
    assert len(res["matches"]) == 0
    assert res["best_match_similarity"] == 0.0


def test_list_references(tmp_path: Path):
    """Verify list_references returns indexed records without image payloads."""
    db_file = tmp_path / "test_hashes.db"
    img1 = make_pattern_image(pattern="cross")
    img2 = make_pattern_image(pattern="circles")

    add_reference(img1, label="Cross", db_path=db_file)
    add_reference(img2, label="Circles", db_path=db_file)

    records = list_references(db_path=db_file)
    assert len(records) == 2
    assert records[0]["label"] == "Cross"
    assert records[1]["label"] == "Circles"
    assert "created_at" in records[0]


# ============================================================================
# API ENDPOINT TESTS (Phase 2)
# ============================================================================

def test_api_reference_add_and_list():
    """Verify POST /reference/add and GET /reference/list endpoints."""
    img_bytes = make_pattern_image(pattern="circles")

    # POST /reference/add
    response = client.post(
        "/reference/add",
        data={"label": "Integration Test Reference"},
        files={"file": ("ref.jpg", img_bytes, "image/jpeg")},
    )
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "added"
    assert res_data["label"] == "Integration Test Reference"
    assert isinstance(res_data["id"], int)

    # GET /reference/list
    list_resp = client.get("/reference/list")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert "references" in list_data
    assert list_data["count"] >= 1
    assert any(r["label"] == "Integration Test Reference" for r in list_data["references"])


def test_api_analyze_contains_all_four_checks():
    """Verify POST /analyze returns metadata, ela, c2pa, and duplicate checks."""
    img_bytes = make_pattern_image(pattern="bars")
    files = {"file": ("test_composite.jpg", img_bytes, "image/jpeg")}

    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()

    assert "filename" in data
    assert "checks" in data
    checks = data["checks"]

    # All 4 checks present
    assert "metadata" in checks
    assert "ela" in checks
    assert "c2pa" in checks
    assert "duplicate" in checks

    # Verify risk_scores exist and are bounded [0.0, 1.0]
    for check_name in ["metadata", "ela", "c2pa", "duplicate"]:
        score = checks[check_name]["risk_score"]
        assert isinstance(score, (int, float))
        assert 0.0 <= score <= 1.0
