"""
Perceptual Hashing & Duplicate Detection Check for Fake Media Detector.

Perceptual hashing (pHash, aHash, dHash, wHash) maps visual structures of an image
into compact binary fingerprints. Unlike cryptographic hash functions (such as SHA-256),
where changing even a single pixel completely randomizes the output digest (the avalanche effect),
perceptual hashes produce nearly identical hash values for images with identical or similar visual content,
even after recompression, resizing, color shifts, or minor cropping.

Why this matters for Fake Media Detection:
In media forensics and online misinformation analysis, a major vector of deception is "recycled media"
(also known as cheapfakes or out-of-context images) — where authentic historic photos from a past war,
disaster, or protest are re-posted with misleading captions claiming they depict breaking news today.
Detecting near-duplicates against a database of verified reference imagery exposes this reuse.
Conversely, finding no duplicate match is neutral (neither proving nor disproving authenticity),
since genuine original photos will naturally not be present in the reference database.
"""

import contextlib
import io
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional
import imagehash
from PIL import Image

from app.config import (
    DEFAULT_HASH_DB_PATH,
    DUPLICATE_MATCH_RISK,
    DUPLICATE_NEUTRAL_RISK,
    DUPLICATE_TOP_MATCHES_LIMIT,
    HASH_MAX_DISTANCE,
    NEAR_DUPLICATE_SIMILARITY_THRESHOLD,
)


def get_db_path(db_path: Optional[Path | str] = None) -> Path:
    """
    Resolves the SQLite database path and ensures the containing directory exists.

    Args:
        db_path: Optional custom path (used extensively during unit tests).

    Returns:
        Path: Resolved filesystem path to the database.
    """
    path = Path(db_path) if db_path is not None else DEFAULT_HASH_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


@contextlib.contextmanager
def get_db_connection(db_path: Optional[Path | str] = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding an open SQLite connection and ensuring it is
    properly closed upon exit to prevent Windows file-lock issues.
    """
    path = get_db_path(db_path)
    conn = sqlite3.connect(path)
    try:
        yield conn
    finally:
        conn.close()


def init_db(db_path: Optional[Path | str] = None) -> None:
    """
    Initializes the SQLite schema for storing reference image perceptual hashes.
    Safe to call repeatedly (idempotent).
    """
    with get_db_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS reference_hashes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                phash TEXT NOT NULL,
                ahash TEXT NOT NULL,
                dhash TEXT NOT NULL,
                whash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


def compute_hashes(image_bytes: bytes) -> Dict[str, str]:
    """
    Computes four complementary perceptual hash algorithms:
    - pHash (DCT-based): Analyzes discrete cosine transform frequencies; resilient to scaling/edits.
    - aHash (Average): Evaluates pixel values against average luminance; fast structural signature.
    - dHash (Difference): Tracks horizontal pixel gradients; sensitive to structural shifts.
    - wHash (Wavelet): Uses Discrete Wavelet Transform (Haar); high stability in frequency domain.

    Args:
        image_bytes: Binary data of the image.

    Returns:
        dict: Hexadecimal representations of the four hashes.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        # Convert to RGB to handle alpha channels and greyscale uniformly
        rgb_img = img.convert("RGB")
        return {
            "phash": str(imagehash.phash(rgb_img)),
            "ahash": str(imagehash.average_hash(rgb_img)),
            "dhash": str(imagehash.dhash(rgb_img)),
            "whash": str(imagehash.whash(rgb_img)),
        }


def add_reference(
    image_bytes: bytes,
    label: str,
    db_path: Optional[Path | str] = None,
) -> int:
    """
    Computes perceptual hashes for an image and records them in the reference database.

    Args:
        image_bytes: Binary data of the reference image.
        label: Descriptive label or title (e.g., "2020 Beirut explosion original").
        db_path: Optional database path override.

    Returns:
        int: The auto-generated database ID of the inserted record.
    """
    init_db(db_path)
    hashes = compute_hashes(image_bytes)

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reference_hashes (label, phash, ahash, dhash, whash)
            VALUES (?, ?, ?, ?, ?)
            """,
            (label, hashes["phash"], hashes["ahash"], hashes["dhash"], hashes["whash"]),
        )
        conn.commit()
        return int(cursor.lastrowid)


def list_references(db_path: Optional[Path | str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves a list of all stored reference images (metadata only, no raw bytes).

    Args:
        db_path: Optional database path override.

    Returns:
        list[dict]: List of reference records with id, label, and created_at.
    """
    init_db(db_path)

    with get_db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, label, phash, ahash, dhash, whash, created_at FROM reference_hashes ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "label": row["label"],
                "phash": row["phash"],
                "ahash": row["ahash"],
                "dhash": row["dhash"],
                "whash": row["whash"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]


def find_matches(
    image_bytes: bytes,
    max_distance: int = HASH_MAX_DISTANCE,
    db_path: Optional[Path | str] = None,
) -> List[Dict[str, Any]]:
    """
    Searches the reference database for images matching the input within a Hamming distance threshold.

    Hamming distance measures the number of bit positions in which two hashes differ.
    For 64-bit perceptual hashes, a distance of 0 indicates an identical perceptual fingerprint,
    while distances <= 10 indicate strong visual similarity despite compression or resolution changes.

    Args:
        image_bytes: Image bytes to search.
        max_distance: Maximum allowable Hamming distance on pHash to qualify as a candidate.
        db_path: Optional database path override.

    Returns:
        list[dict]: List of matches sorted from highest similarity to lowest.
    """
    init_db(db_path)
    query_hashes = compute_hashes(image_bytes)
    q_p = imagehash.hex_to_hash(query_hashes["phash"])
    q_a = imagehash.hex_to_hash(query_hashes["ahash"])
    q_d = imagehash.hex_to_hash(query_hashes["dhash"])
    q_w = imagehash.hex_to_hash(query_hashes["whash"])

    matches: List[Dict[str, Any]] = []

    with get_db_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT id, label, phash, ahash, dhash, whash FROM reference_hashes")
        rows = cursor.fetchall()

        for row in rows:
            dist_p = int(q_p - imagehash.hex_to_hash(row["phash"]))
            dist_a = int(q_a - imagehash.hex_to_hash(row["ahash"]))
            dist_d = int(q_d - imagehash.hex_to_hash(row["dhash"]))
            dist_w = int(q_w - imagehash.hex_to_hash(row["whash"]))

            # Primary match gate: pHash distance or minimum distance across algorithms within threshold
            min_dist = min(dist_p, dist_d, dist_w)
            if dist_p <= max_distance or min_dist <= max_distance:
                # Multi-algorithm average Hamming distance across all 4 hashes
                avg_dist = (dist_p + dist_a + dist_d + dist_w) / 4.0
                # Normalized similarity percentage over 64 bits (100% = 0 distance)
                similarity = round(max(0.0, (1.0 - (avg_dist / 64.0)) * 100.0), 2)

                matches.append({
                    "id": row["id"],
                    "label": row["label"],
                    "hamming_distances": {
                        "phash": dist_p,
                        "ahash": dist_a,
                        "dhash": dist_d,
                        "whash": dist_w,
                    },
                    "similarity_percent": similarity,
                })

    # Sort matches closest first (highest similarity percentage first, lowest pHash distance)
    matches.sort(
        key=lambda m: (-m["similarity_percent"], m["hamming_distances"]["phash"])
    )
    return matches


def analyze_duplicate(
    image_bytes: bytes,
    db_path: Optional[Path | str] = None,
) -> Dict[str, Any]:
    """
    Forensic duplicate analysis check for /analyze endpoint pipeline.

    Evaluates whether an uploaded image is a recycled copy of a known reference image.
    Returns the top 5 closest matches, overall similarity, and an assigned risk score.

    Args:
        image_bytes: Binary data of the uploaded image.
        db_path: Optional database path override.

    Returns:
        dict: Duplicate check result conforming to DuplicateCheckResult schema.
    """
    try:
        all_matches = find_matches(
            image_bytes,
            max_distance=HASH_MAX_DISTANCE,
            db_path=db_path,
        )
        top_matches = all_matches[:DUPLICATE_TOP_MATCHES_LIMIT]
        best_similarity = top_matches[0]["similarity_percent"] if top_matches else 0.0

        is_near_dup = (
            len(top_matches) > 0
            and (
                top_matches[0]["hamming_distances"]["phash"] <= HASH_MAX_DISTANCE
                or best_similarity >= NEAR_DUPLICATE_SIMILARITY_THRESHOLD
            )
        )

        if is_near_dup:
            # Reusing known reference imagery under potentially altered narratives carries high risk
            risk_score = DUPLICATE_MATCH_RISK
            best_label = top_matches[0]["label"]
            note = (
                f"Near-duplicate match found ('{best_label}' with {best_similarity}% similarity). "
                "Recycled imagery is a common indicator of misleading claims or repurposed media."
            )
        else:
            # Neutral score: no match in the database does not prove an image is authentic
            risk_score = DUPLICATE_NEUTRAL_RISK
            note = (
                "No near-duplicate match identified in the reference database. "
                "Absence of a match is neutral and does not confirm image authenticity."
            )

        return {
            "matches": top_matches,
            "best_match_similarity": best_similarity,
            "is_near_duplicate": is_near_dup,
            "risk_score": risk_score,
            "note": note,
        }
    except Exception as exc:
        return {
            "matches": [],
            "best_match_similarity": 0.0,
            "is_near_duplicate": False,
            "risk_score": DUPLICATE_NEUTRAL_RISK,
            "note": f"Duplicate analysis encountered an error: {str(exc)}",
        }
