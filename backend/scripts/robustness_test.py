#!/usr/bin/env python3
"""
Robustness Test Script for Fake Media Detector.

Tests how forensic checks and the verdict engine respond to common real-world
image degradations (compression, resizing, screenshotting, format conversion, cropping).

Directly invokes the forensic check modules and verdict engine in memory
(no HTTP server required).

Output:
- Console table showing variant, ai_probability, ela_score, overall_score, verdict_label.
- CSV saved to backend/data/robustness_results.csv.
- Summary of AI probability delta under each degradation.

Usage:
    python scripts/robustness_test.py path/to/image.jpg
    python scripts/robustness_test.py path/to/image_folder/
"""

import argparse
import csv
import io
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from PIL import Image, ImageFilter
from app.checks import run_all_checks
from app.verdict import compute_verdict
from app.config import DATA_DIR, ALLOWED_EXTENSIONS

DEFAULT_CSV_OUTPUT = DATA_DIR / "robustness_results.csv"


def generate_variants(image_bytes: bytes) -> List[Tuple[str, bytes]]:
    """
    Creates in-memory degraded variants of an input image byte stream:
    1. original: unmodified input bytes
    2. resized_50: scaled down to 50% width and height (Bilinear)
    3. resized_25: scaled down to 25% width and height (Bilinear)
    4. jpeg_q70: recompressed as JPEG with quality 70
    5. jpeg_q30: aggressively recompressed as JPEG with quality 30
    6. png_format: converted to lossless PNG format
    7. screenshot: slight Gaussian blur (radius 1) + resaved (simulates mobile screenshot/rescaling)
    8. center_crop: center cropped to 75% dimensions and saved
    """
    variants: List[Tuple[str, bytes]] = [("original", image_bytes)]

    with Image.open(io.BytesIO(image_bytes)) as pil_img:
        # Normalize to RGB for consistent manipulation
        base_img = pil_img.convert("RGB")
        w, h = base_img.size

        # 1. Resized to 50%
        w50, h50 = max(1, int(w * 0.5)), max(1, int(h * 0.5))
        img_50 = base_img.resize((w50, h50), Image.Resampling.BILINEAR)
        buf_50 = io.BytesIO()
        img_50.save(buf_50, format="JPEG", quality=90)
        variants.append(("resized_50", buf_50.getvalue()))

        # 2. Resized to 25%
        w25, h25 = max(1, int(w * 0.25)), max(1, int(h * 0.25))
        img_25 = base_img.resize((w25, h25), Image.Resampling.BILINEAR)
        buf_25 = io.BytesIO()
        img_25.save(buf_25, format="JPEG", quality=85)
        variants.append(("resized_25", buf_25.getvalue()))

        # 3. JPEG Quality 70
        buf_q70 = io.BytesIO()
        base_img.save(buf_q70, format="JPEG", quality=70)
        variants.append(("jpeg_q70", buf_q70.getvalue()))

        # 4. JPEG Quality 30 (heavy compression)
        buf_q30 = io.BytesIO()
        base_img.save(buf_q30, format="JPEG", quality=30)
        variants.append(("jpeg_q30", buf_q30.getvalue()))

        # 5. PNG conversion
        buf_png = io.BytesIO()
        base_img.save(buf_png, format="PNG")
        variants.append(("png_format", buf_png.getvalue()))

        # 6. Screenshot-like: slight blur + resave
        img_shot = base_img.filter(ImageFilter.GaussianBlur(radius=1.0))
        buf_shot = io.BytesIO()
        img_shot.save(buf_shot, format="JPEG", quality=80)
        variants.append(("screenshot", buf_shot.getvalue()))

        # 7. Center Crop (75% central box)
        crop_w, crop_h = int(w * 0.75), int(h * 0.75)
        left = (w - crop_w) // 2
        top = (h - crop_h) // 2
        img_cropped = base_img.crop((left, top, left + crop_w, top + crop_h))
        buf_crop = io.BytesIO()
        img_cropped.save(buf_crop, format="JPEG", quality=90)
        variants.append(("center_crop", buf_crop.getvalue()))

    return variants


def evaluate_image(image_path: Path) -> List[Dict[str, str]]:
    """Runs all variants of an image through the forensic checks and verdict engine."""
    with open(image_path, "rb") as f:
        orig_bytes = f.read()

    variants = generate_variants(orig_bytes)
    results = []

    print(f"\nEvaluating: {image_path.name}")
    print(f"{'Variant':<16} | {'AI Prob':<9} | {'ELA Score':<10} | {'Overall':<9} | {'Verdict Label':<22}")
    print("-" * 75)

    orig_ai_prob = None

    for variant_name, var_bytes in variants:
        checks = run_all_checks(var_bytes)
        verdict = compute_verdict(checks)

        # Extract values
        ai_prob = checks.get("ai_detector", {}).get("ai_probability")
        ela_score = checks.get("ela", {}).get("risk_score")
        overall = verdict.get("overall_score", 0.0)
        label = verdict.get("label", "unknown")

        if variant_name == "original":
            orig_ai_prob = ai_prob

        ai_str = f"{ai_prob:.3f}" if ai_prob is not None else "N/A"
        ela_str = f"{ela_score:.3f}" if ela_score is not None else "N/A"
        overall_str = f"{overall:.3f}"

        print(f"{variant_name:<16} | {ai_str:<9} | {ela_str:<10} | {overall_str:<9} | {label:<22}")

        results.append({
            "image": image_path.name,
            "variant": variant_name,
            "ai_probability": ai_str,
            "ela_score": ela_str,
            "overall_score": overall_str,
            "verdict_label": label,
            "confidence": verdict.get("confidence", "unknown"),
        })

    # Summary of delta relative to original
    if orig_ai_prob is not None:
        print("\nAI Probability Shift Analysis (Relative to Original):")
        for row in results[1:]:
            try:
                curr_prob = float(row["ai_probability"])
                delta = curr_prob - orig_ai_prob
                direction = "+" if delta >= 0 else ""
                print(f"  • {row['variant']:<14}: {row['ai_probability']} ({direction}{delta:.3f})")
            except ValueError:
                print(f"  • {row['variant']:<14}: N/A")

    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate detector robustness against image degradations.")
    parser.add_argument("target", type=str, help="Path to an image file or directory of images.")
    parser.add_argument("--output", type=str, default=str(DEFAULT_CSV_OUTPUT), help="Output CSV path.")
    args = parser.parse_args()

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"Error: Target path '{target_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    image_files: List[Path] = []
    if target_path.is_file():
        image_files = [target_path]
    elif target_path.is_dir():
        for p in sorted(target_path.iterdir()):
            if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
                image_files.append(p)

    if not image_files:
        print(f"No valid image files found in '{target_path}'.", file=sys.stderr)
        sys.exit(1)

    all_rows: List[Dict[str, str]] = []
    for img_path in image_files:
        rows = evaluate_image(img_path)
        all_rows.extend(rows)

    # Save to CSV
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = ["image", "variant", "ai_probability", "ela_score", "overall_score", "verdict_label", "confidence"]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n[Done] Saved robustness evaluation to: {output_path}")


if __name__ == "__main__":
    main()
