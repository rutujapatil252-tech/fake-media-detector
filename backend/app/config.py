# Configuration constants for Fake Media Detector (Phases 1, 2, 3, and 4)
# Centralizing these settings allows easy tuning of analysis parameters,
# file limits, AI models, weights, and CORS policies without modifying core logic.

import os
from pathlib import Path

# Base paths
BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = BACKEND_DIR / "data"
DEFAULT_HASH_DB_PATH: Path = DATA_DIR / "hashes.db"
EVAL_RESULTS_PATH: Path = DATA_DIR / "eval_results.csv"

# Allowed upload file extensions and MIME types
ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}

ALLOWED_MIME_TYPES: set[str] = {
    "image/jpeg",
    "image/jpg",
    "image/pjpeg",
    "image/png",
    "image/x-png",
    "image/webp",
    "application/octet-stream",
}

# Maximum upload size: 10 MB in bytes
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024

# Allowed CORS origins for frontend web apps (React, Vite, Next.js, etc.)
CORS_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://localhost:5174",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "*",
]

# ELA (Error Level Analysis) parameters:
ELA_JPEG_QUALITY: int = 90
ELA_AMPLIFY_SCALE: int = 15
ELA_MAX_DIMENSION: int = 1024
ELA_SUSPICIOUS_PIXEL_THRESHOLD: float = 25.0

# Keywords for detecting image editing software in metadata
EDITING_SOFTWARE_KEYWORDS: list[str] = [
    "photoshop",
    "gimp",
    "lightroom",
    "canva",
    "affinity",
    "pixelmator",
    "paint.net",
    "coreldraw",
    "snapseed",
    "vsco",
]

# Keywords indicating generative AI tools or AI synthesis pipelines
AI_TOOL_KEYWORDS: list[str] = [
    "midjourney",
    "dall-e",
    "dalle",
    "stable diffusion",
    "stablediffusion",
    "novelai",
    "comfyui",
    "firefly",
    "bing image creator",
    "leonardo.ai",
    "flux",
    "civitai",
]

# ---------------------------------------------------------------------------
# Phase 2: Perceptual Hashing & Duplicate Detection Settings
# ---------------------------------------------------------------------------
HASH_MAX_DISTANCE: int = 10
DUPLICATE_TOP_MATCHES_LIMIT: int = 5
NEAR_DUPLICATE_SIMILARITY_THRESHOLD: float = 80.0
DUPLICATE_NEUTRAL_RISK: float = 0.5
DUPLICATE_MATCH_RISK: float = 0.8

# ---------------------------------------------------------------------------
# Phase 2: C2PA Content Credentials Settings
# ---------------------------------------------------------------------------
C2PA_NEUTRAL_RISK: float = 0.5
C2PA_AUTHENTIC_RISK: float = 0.1
C2PA_AI_GENERATED_RISK: float = 0.95
C2PA_INVALID_MANIFEST_RISK: float = 0.9

# ---------------------------------------------------------------------------
# Phase 3: Pretrained Hugging Face AI-Generated Image Detector Settings
# ---------------------------------------------------------------------------
AI_MODEL_NAME: str = "Organika/sdxl-detector"
AI_CANDIDATE_MODELS: list[str] = [
    "Organika/sdxl-detector",
    "umm-maybe/AI-image-detector",
    "dima806/ai_vs_real_image_detection",
]
AI_PROBABILITY_HIGH_THRESHOLD: float = 0.7
AI_PROBABILITY_LOW_THRESHOLD: float = 0.4

# ---------------------------------------------------------------------------
# Phase 4: Verdict Engine Settings
# ---------------------------------------------------------------------------
# Weighted average weights for available forensic checks (sum = 1.0)
# ai_detector carries the highest weight as a direct vision classifier.
VERDICT_WEIGHTS: dict[str, float] = {
    "ai_detector": 0.45,
    "ela": 0.15,
    "metadata": 0.15,
    "c2pa": 0.15,
    "duplicate": 0.10,
}

# Label thresholds applied to overall_score:
# >= 0.65: likely_ai_generated
# 0.45 to 0.65: possibly_manipulated
# < 0.30: likely_authentic
# otherwise (0.30 <= score < 0.45): inconclusive
VERDICT_THRESHOLD_AI: float = 0.65
VERDICT_THRESHOLD_MANIPULATED: float = 0.45
VERDICT_THRESHOLD_AUTHENTIC: float = 0.30

# Moderation score reduction applied when valid authentic C2PA credentials exist
C2PA_AUTHENTIC_SCORE_REDUCTION: float = 0.20
