#!/usr/bin/env python3
"""
Seed References Script for Fake Media Detector.

Scans an input directory of images and registers each one into the
perceptual hash database (SQLite) using its filename as the reference label.

Usage:
    python scripts/seed_references.py /path/to/image/folder
    python scripts/seed_references.py /path/to/image/folder --db /path/to/custom/hashes.db
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure the backend directory is on sys.path so app modules import cleanly
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.checks.duplicate import add_reference
from app.config import ALLOWED_EXTENSIONS, DEFAULT_HASH_DB_PATH


def seed_folder(folder_path: Path, db_path: Path = DEFAULT_HASH_DB_PATH) -> int:
    """
    Scans the given folder and indexes all supported images into the perceptual hash database.

    Args:
        folder_path: Directory containing images to index.
        db_path: Target SQLite database path.

    Returns:
        int: Number of reference images successfully indexed.
    """
    if not folder_path.exists() or not folder_path.is_dir():
        print(f"Error: Folder '{folder_path}' does not exist or is not a directory.", file=sys.stderr)
        return 0

    print(f"Scanning '{folder_path}' for reference images...")
    print(f"Target Database: '{db_path}'")

    indexed_count = 0
    skipped_count = 0

    # Sort files for deterministic processing
    entries = sorted(os.listdir(folder_path))

    for filename in entries:
        file_path = folder_path / filename
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            continue

        try:
            with open(file_path, "rb") as f:
                image_bytes = f.read()

            if not image_bytes:
                print(f"  [SKIPPED] {filename}: Empty file.")
                skipped_count += 1
                continue

            # Use the base filename (without path) as the human-readable label
            label = file_path.stem
            stored_id = add_reference(image_bytes, label, db_path=db_path)
            print(f"  [INDEXED] ID #{stored_id}: '{label}' ({filename})")
            indexed_count += 1

        except Exception as exc:
            print(f"  [ERROR] {filename}: Failed to index ({exc})", file=sys.stderr)
            skipped_count += 1

    print("\n--- Summary ---")
    print(f"Successfully indexed: {indexed_count} image(s)")
    if skipped_count > 0:
        print(f"Skipped/Errors: {skipped_count} file(s)")

    return indexed_count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index a folder of reference images into the Fake Media Detector perceptual hash database."
    )
    parser.add_argument(
        "folder",
        type=Path,
        help="Path to the directory containing images to index (.jpg, .jpeg, .png, .webp).",
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_HASH_DB_PATH,
        help=f"Optional path to the SQLite database (default: {DEFAULT_HASH_DB_PATH}).",
    )

    args = parser.parse_args()
    seed_folder(args.folder, args.db)


if __name__ == "__main__":
    main()
