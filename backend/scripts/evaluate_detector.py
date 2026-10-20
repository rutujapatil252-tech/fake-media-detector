#!/usr/bin/env python3
"""
Model Evaluation Script for Fake Media Detector AI Classifier (Phase 3).

Evaluates the pretrained AI detector across labeled datasets of real and AI-generated images.
Calculates standard classification performance metrics:
- Accuracy
- Precision
- Recall
- F1 Score
- Confusion Matrix

Outputs a tabular summary in the terminal and persists sample predictions to a CSV file.

Usage:
    python scripts/evaluate_detector.py --real_dir path/to/real --ai_dir path/to/ai [--threshold 0.5]
"""

import argparse
import csv
import os
from pathlib import Path
import sys
from typing import List, Tuple

# Ensure backend root is on sys.path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.checks.ai_detector import analyze_ai_generated
from app.config import ALLOWED_EXTENSIONS, EVAL_RESULTS_PATH


def collect_images_from_dir(directory: Path) -> List[Path]:
    """Retrieves all supported image filepaths from a target directory."""
    if not directory.exists() or not directory.is_dir():
        return []

    image_paths: List[Path] = []
    for entry in sorted(os.listdir(directory)):
        p = directory / entry
        if p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS:
            image_paths.append(p)
    return image_paths


def evaluate_dataset(
    real_dir: Path,
    ai_dir: Path,
    threshold: float = 0.5,
    output_csv: Path = EVAL_RESULTS_PATH,
) -> None:
    """
    Runs inference on all images in real_dir and ai_dir, computes metrics, and writes CSV report.
    """
    real_images = collect_images_from_dir(real_dir)
    ai_images = collect_images_from_dir(ai_dir)

    # Validate input paths and image counts
    if not real_dir.exists():
        print(f"Error: Real images directory '{real_dir}' does not exist.", file=sys.stderr)
        return
    if not ai_dir.exists():
        print(f"Error: AI images directory '{ai_dir}' does not exist.", file=sys.stderr)
        return

    if not real_images and not ai_images:
        print("Error: Both real and AI directories are empty or contain no supported image formats (.jpg, .png, .webp).", file=sys.stderr)
        return

    print(f"--- Evaluating AI Image Detector ---")
    print(f"Real Images Folder: '{real_dir}' ({len(real_images)} files)")
    print(f"AI Images Folder:   '{ai_dir}' ({len(ai_images)} files)")
    print(f"Decision Threshold: {threshold}")
    print(f"Output CSV Path:    '{output_csv}'\n")

    # True labels: 0 for Real, 1 for AI
    y_true: List[int] = []
    y_pred: List[int] = []
    y_scores: List[float] = []
    csv_rows: List[Tuple[str, str, float, str]] = []

    # Process Real images (ground truth = 0 / "real")
    for img_path in real_images:
        try:
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            res = analyze_ai_generated(img_bytes)
            prob = float(res.get("ai_probability", 0.5))
            pred = 1 if prob >= threshold else 0
            pred_label = "ai" if pred == 1 else "real"

            y_true.append(0)
            y_pred.append(pred)
            y_scores.append(prob)
            csv_rows.append((img_path.name, "real", prob, pred_label))
            print(f"  [REAL] {img_path.name:30} -> Prob: {prob:.4f} | Pred: {pred_label}")
        except Exception as exc:
            print(f"  [ERROR] {img_path.name}: {exc}", file=sys.stderr)

    # Process AI images (ground truth = 1 / "ai")
    for img_path in ai_images:
        try:
            with open(img_path, "rb") as f:
                img_bytes = f.read()
            res = analyze_ai_generated(img_bytes)
            prob = float(res.get("ai_probability", 0.5))
            pred = 1 if prob >= threshold else 0
            pred_label = "ai" if pred == 1 else "real"

            y_true.append(1)
            y_pred.append(pred)
            y_scores.append(prob)
            csv_rows.append((img_path.name, "ai", prob, pred_label))
            print(f"  [AI]   {img_path.name:30} -> Prob: {prob:.4f} | Pred: {pred_label}")
        except Exception as exc:
            print(f"  [ERROR] {img_path.name}: {exc}", file=sys.stderr)

    # Calculate metrics with scikit-learn
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

    total_samples = len(y_true)
    if total_samples == 0:
        print("No valid samples were processed.")
        return

    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])

    # Confusion matrix structure:
    # [ [True Negative (Real as Real), False Positive (Real as AI)]
    #   [False Negative (AI as Real), True Positive (AI as AI)] ]
    tn, fp, fn, tp = cm.ravel() if cm.size == 4 else (0, 0, 0, 0)

    print("\n" + "=" * 50)
    print("           EVALUATION RESULTS SUMMARY")
    print("=" * 50)
    print(f"Total Evaluated: {total_samples}")
    print(f"Accuracy:        {acc * 100:.2f}%")
    print(f"Precision:       {prec * 100:.2f}% (How many flagged AI images were truly AI)")
    print(f"Recall:          {rec * 100:.2f}% (How many AI images were successfully caught)")
    print(f"F1 Score:        {f1:.4f}")
    print("\nConfusion Matrix:")
    print(f"  True Negatives  (Real labeled Real): {tn}")
    print(f"  False Positives (Real labeled AI):   {fp}  <-- Critical for false accusations")
    print(f"  False Negatives (AI labeled Real):   {fn}")
    print(f"  True Positives  (AI labeled AI):     {tp}")
    print("=" * 50)

    # Save to CSV
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "true_label", "ai_probability", "predicted_label"])
        writer.writerows(csv_rows)

    print(f"\nDetailed predictions saved to: '{output_csv}'")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the AI detector against labeled real and synthetic image directories."
    )
    parser.add_argument(
        "--real_dir",
        type=Path,
        required=True,
        help="Path to folder containing authentic real photographs.",
    )
    parser.add_argument(
        "--ai_dir",
        type=Path,
        required=True,
        help="Path to folder containing synthetic AI-generated images.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Decision probability threshold for classifying an image as AI (default: 0.5).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EVAL_RESULTS_PATH,
        help=f"Target CSV output path (default: {EVAL_RESULTS_PATH}).",
    )

    args = parser.parse_args()
    evaluate_dataset(args.real_dir, args.ai_dir, args.threshold, args.output)


if __name__ == "__main__":
    main()
