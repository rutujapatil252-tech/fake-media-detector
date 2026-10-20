#!/usr/bin/env python3
"""
End-to-End Smoke Test Script for Fake Media Detector.

Performs live automated verification against a running FastAPI backend:
1. GET /health: Server liveness verification
2. POST /analyze: Multi-vector analysis with synthetic camera JPEG
3. POST /reference/add: Register reference media into perceptual hash database
4. GET /reference/list: Query indexed references
5. POST /analyze (duplicate verification): Re-analyze same media to confirm duplicate check triggers

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --url http://127.0.0.1:8000
"""

import argparse
import io
import json
import sys
import urllib.request
import urllib.error
from typing import Tuple
from PIL import Image
import piexif

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
INFO = "\033[94m[INFO]\033[0m"


def create_sample_jpeg(color: Tuple[int, int, int] = (60, 120, 200), exif: bool = True) -> bytes:
    """Generates an in-memory JPEG test image with optional camera EXIF metadata."""
    img = Image.new("RGB", (256, 256), color=color)
    buf = io.BytesIO()

    exif_bytes = None
    if exif:
        zeroth = {
            piexif.ImageIFD.Make: b"Canon",
            piexif.ImageIFD.Model: b"Canon EOS R5",
            piexif.ImageIFD.Software: b"Canon Firmware 1.5",
        }
        exif_dict = {"0th": zeroth}
        exif_bytes = piexif.dump(exif_dict)

    if exif_bytes:
        img.save(buf, format="JPEG", quality=95, exif=exif_bytes)
    else:
        img.save(buf, format="JPEG", quality=95)

    return buf.getvalue()


def send_multipart(url: str, fields: dict, files: dict) -> Tuple[int, dict]:
    """Helper to send a multipart/form-data request using standard library."""
    boundary = "----WebKitFormBoundarySmokeTest7MA4"
    body = bytearray()

    # Form fields
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())

    # File fields
    for name, (filename, file_bytes, mime_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.extend(f"Content-Type: {mime_type}\r\n\r\n".encode())
        body.extend(file_bytes)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            data = json.loads(res.read().decode())
            return res.status, data
    except urllib.error.HTTPError as err:
        try:
            data = json.loads(err.read().decode())
        except Exception:
            data = {"error": str(err)}
        return err.code, data


def send_get(url: str) -> Tuple[int, dict]:
    """Helper to send a GET request using standard library."""
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            data = json.loads(res.read().decode())
            return res.status, data
    except urllib.error.HTTPError as err:
        try:
            data = json.loads(err.read().decode())
        except Exception:
            data = {"error": str(err)}
        return err.code, data


def run_smoke_tests(base_url: str):
    base_url = base_url.rstrip("/")
    print(f"\n==================================================")
    print(f"  Fake Media Detector — Live Smoke Test Suite")
    print(f"  Target: {base_url}")
    print(f"==================================================\n")

    passed_count = 0
    total_count = 5

    # -------------------------------------------------------------------------
    # Test 1: Health Liveness
    # -------------------------------------------------------------------------
    print("1. Checking GET /health liveness...")
    try:
        status_code, data = send_get(f"{base_url}/health")
        if status_code == 200 and data.get("status") == "ok":
            print(f"   {PASS} Server is healthy: {data}")
            passed_count += 1
        else:
            print(f"   {FAIL} Unexpected response (Status {status_code}): {data}")
    except Exception as exc:
        print(f"   {FAIL} Connection failed: {exc}")
        print("\nEnsure the backend server is running: uvicorn app.main:app --port 8000")
        sys.exit(1)

    # -------------------------------------------------------------------------
    # Test 2: Multi-Vector Analysis on Fresh Media
    # -------------------------------------------------------------------------
    print("\n2. Testing POST /analyze with clean camera JPEG...")
    test_img = create_sample_jpeg(color=(80, 150, 220), exif=True)
    status_code, data = send_multipart(
        f"{base_url}/analyze",
        fields={},
        files={"file": ("camera_test.jpg", test_img, "image/jpeg")},
    )

    if status_code == 200:
        has_checks = "checks" in data and len(data["checks"]) == 5
        has_verdict = "verdict" in data and "label" in data["verdict"]
        has_timing = "processing_time_ms" in data
        if has_checks and has_verdict and has_timing:
            verdict = data["verdict"]
            print(f"   {PASS} Analysis succeeded in {data['processing_time_ms']} ms")
            print(f"        Label: {verdict['label']} ({verdict['display_label']})")
            print(f"        Score: {verdict['overall_score']} | Confidence: {verdict['confidence']}")
            passed_count += 1
        else:
            print(f"   {FAIL} Incomplete schema returned: {list(data.keys())}")
    else:
        print(f"   {FAIL} /analyze returned status {status_code}: {data}")

    # -------------------------------------------------------------------------
    # Test 3: Reference Database Registration
    # -------------------------------------------------------------------------
    print("\n3. Testing POST /reference/add to index known reference media...")
    ref_img = create_sample_jpeg(color=(220, 90, 40), exif=False)
    ref_label = "Smoke Test Reference 01"
    status_code, data = send_multipart(
        f"{base_url}/reference/add",
        fields={"label": ref_label},
        files={"file": ("reference_source.jpg", ref_img, "image/jpeg")},
    )

    if status_code == 200 and data.get("status") in ["success", "added"]:
        entry = data.get("entry", data)
        print(f"   {PASS} Successfully indexed reference media (ID {entry.get('id')}): '{entry.get('label')}'")
        passed_count += 1
    else:
        print(f"   {FAIL} /reference/add failed ({status_code}): {data}")

    # -------------------------------------------------------------------------
    # Test 4: Reference Database Query
    # -------------------------------------------------------------------------
    print("\n4. Testing GET /reference/list to query indexed references...")
    status_code, data = send_get(f"{base_url}/reference/list")
    if status_code == 200 and "references" in data:
        refs = data["references"]
        count = data.get("count", len(refs))
        print(f"   {PASS} Reference registry query successful ({count} stored references)")
        passed_count += 1
    else:
        print(f"   {FAIL} /reference/list failed ({status_code}): {data}")

    # -------------------------------------------------------------------------
    # Test 5: Duplicate Detection Verification
    # -------------------------------------------------------------------------
    print("\n5. Testing Duplicate Detection (re-analyzing reference image)...")
    status_code, data = send_multipart(
        f"{base_url}/analyze",
        fields={},
        files={"file": ("recycled_reference.jpg", ref_img, "image/jpeg")},
    )

    if status_code == 200:
        dup_check = data.get("checks", {}).get("duplicate", {})
        is_dup = dup_check.get("is_near_duplicate") or dup_check.get("is_duplicate")
        matches = dup_check.get("matches", [])
        matched = matches[0]["label"] if matches else dup_check.get("matched_reference")
        sim_pct = dup_check.get("best_match_similarity", dup_check.get("similarity_pct", 0.0))

        matched_labels = [m.get("label") for m in matches]
        if is_dup is True and (matched == ref_label or ref_label in matched_labels):
            print(f"   {PASS} Duplicate check correctly identified recycled media!")
            print(f"        Matched Label: '{matched}' ({sim_pct:.1f}% similarity)")
            passed_count += 1
        else:
            print(f"   {FAIL} Duplicate was not detected: is_duplicate={is_dup}, match={matched}")
    else:
        print(f"   {FAIL} /analyze returned status {status_code}: {data}")

    # -------------------------------------------------------------------------
    # Final Summary
    # -------------------------------------------------------------------------
    print(f"\n==================================================")
    print(f"  Smoke Test Results: {passed_count}/{total_count} PASSED")
    print(f"==================================================")

    if passed_count == total_count:
        print("  \033[92mAll live system interfaces functioning flawlessly.\033[0m\n")
        return 0
    else:
        print("  \033[91mSome live smoke tests failed.\033[0m\n")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Live smoke tests for Fake Media Detector.")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base backend URL (default: http://127.0.0.1:8000)")
    args = parser.parse_args()
    sys.exit(run_smoke_tests(args.url))
