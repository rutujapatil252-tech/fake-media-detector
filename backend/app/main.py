"""
Main FastAPI Application for Fake Media Detector (Phases 1, 2, 3, and 4).

Endpoints:
- GET /health: Simple liveness and health status check.
- POST /analyze: Accepts image file upload, performs security and format validation,
  and runs all registered forensic checks (Metadata EXIF, ELA, C2PA Provenance,
  Perceptual Duplicate Hash, and Pretrained Deep Learning AI Detector),
  then generates a synthesized multi-vector verdict.
- POST /reference/add: Adds a reference image with a label into the perceptual hash database.
- GET /reference/list: Retrieves stored reference images and their IDs/timestamps.
"""

from contextlib import asynccontextmanager
import io
import os
import time
from typing import Any, Dict
from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image

from app.checks import run_all_checks
from app.checks.ai_detector import warmup_ai_detector
from app.checks.duplicate import add_reference, list_references
from app.config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_MIME_TYPES,
    CORS_ORIGINS,
    MAX_FILE_SIZE_BYTES,
)
from app.schemas import (
    AnalysisResponse,
    HealthResponse,
    ReferenceAddResponse,
    ReferenceListResponse,
)
from app.verdict import compute_verdict


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Warms up (preloads) the Hugging Face vision model pipeline during startup
    so the first client inference request incurs zero cold-start latency.
    """
    try:
        print("[Startup] Initializing and warming up AI detector model...")
        warmup_ai_detector()
    except Exception as exc:
        print(f"[Startup] AI detector preload warning: {exc}")
    yield
    print("[Shutdown] Fake Media Detector service stopping.")


# Initialize FastAPI application with descriptive OpenAPI metadata and lifespan handler
app = FastAPI(
    title="Fake Media Detector API",
    description="Backend service providing forensic analysis to detect manipulated, recycled, and AI-generated media.",
    version="4.0.0",
    lifespan=lifespan,
)

# Configure Cross-Origin Resource Sharing (CORS) to allow frontend clients
# (such as React, Vue, Vite, or Next.js dev servers) to interact with this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _validate_and_read_image(file: UploadFile) -> tuple[str, bytes]:
    """
    Validates uploaded file security constraints:
    - Allowed extension allowlist (.jpg, .jpeg, .png, .webp)
    - Declared MIME type header validation
    - Non-empty payload and size limit (<= 10MB)
    - Binary decodability verification via Pillow

    Returns:
        tuple[str, bytes]: Sanitized filename and raw image bytes.
    """
    filename = file.filename or "unknown"
    _, ext = os.path.splitext(filename.lower())

    # 1. Validate file extension
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension '{ext}'. Allowed extensions are: "
                f"{', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    # 2. Validate MIME type header reported by client
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported media type '{file.content_type}'. Allowed types are: "
                f"{', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )

    # 3. Read image contents and validate file size
    image_bytes = await file.read()
    file_size = len(image_bytes)

    if file_size == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes).",
        )

    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum limit "
                f"of {MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
            ),
        )

    # 4. Deep format verification: ensure the bytes actually represent a valid image
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            img.verify()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Uploaded file content is not a valid or readable image: {str(exc)}",
        )

    return filename, image_bytes


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["System"],
)
async def health() -> Dict[str, str]:
    """
    Returns service health status.
    Useful for uptime monitors, Docker container health probes, and CI/CD validation.
    """
    return {"status": "ok"}


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    summary="Analyze image for tampering, AI artifacts, provenance, and duplication",
    tags=["Forensics"],
)
async def analyze_image(
    file: UploadFile = File(..., description="Uploaded image file (JPEG, PNG, WebP up to 10MB)"),
) -> Dict[str, Any]:
    """
    Accepts an uploaded image file, validates its format and size, and runs all available forensic checks.

    Executes:
    1. EXIF Metadata analysis (camera details, editing signatures, timestamps)
    2. Error Level Analysis (ELA compression variance & heatmap)
    3. C2PA Content Credentials provenance verification
    4. Perceptual hashing duplicate detection against known references
    5. Pretrained deep-learning AI-generated image classification
    6. Multi-vector verdict synthesis engine

    Returns:
    - JSON containing filename, check results, synthesized verdict, and processing time in ms.
    """
    start_time = time.perf_counter()
    filename, image_bytes = await _validate_and_read_image(file)

    # Extract pixel dimensions and format
    img_dims = None
    img_fmt = None
    try:
        with Image.open(io.BytesIO(image_bytes)) as pil_img:
            img_dims = {"width": pil_img.width, "height": pil_img.height}
            img_fmt = pil_img.format or "JPEG"
    except Exception:
        pass

    # Run all registered forensic checks (metadata, ela, c2pa, duplicate, ai_detector)
    check_results = run_all_checks(image_bytes)

    # Synthesize verdict from check results
    verdict_result = compute_verdict(check_results)

    processing_time_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    return {
        "filename": filename,
        "image_dimensions": img_dims,
        "image_format": img_fmt,
        "checks": check_results,
        "verdict": verdict_result,
        "processing_time_ms": processing_time_ms,
    }


@app.post(
    "/reference/add",
    response_model=ReferenceAddResponse,
    summary="Add a known reference image to the perceptual hash database",
    tags=["References"],
)
async def add_reference_image(
    file: UploadFile = File(..., description="Reference image file"),
    label: str = Form(..., description="Descriptive label for the reference image"),
) -> Dict[str, Any]:
    """
    Uploads an authentic or known reference image and indexes its perceptual hashes (pHash, aHash, dHash, wHash)
    in the reference database for duplicate detection.
    """
    clean_label = label.strip()
    if not clean_label:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The 'label' form field cannot be empty.",
        )

    _, image_bytes = await _validate_and_read_image(file)
    stored_id = add_reference(image_bytes, clean_label)

    return {
        "id": stored_id,
        "label": clean_label,
        "status": "added",
    }


@app.get(
    "/reference/list",
    response_model=ReferenceListResponse,
    summary="List all indexed reference images",
    tags=["References"],
)
async def list_reference_images() -> Dict[str, Any]:
    """
    Returns a list of all stored reference images with their database IDs, labels, and indexing timestamps.
    Raw image payloads are omitted to maintain lightweight responses.
    """
    records = list_references()
    return {
        "references": records,
        "count": len(records),
    }
