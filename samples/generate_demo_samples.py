#!/usr/bin/env python3
"""
Generates synthetic demo images for Fake Media Detector presentations:
1. authentic_camera_photo.jpg: Camera EXIF metadata, simulated CMOS sensor noise
2. spliced_tampered_photo.jpg: Composite patch causing ELA compression errors + Photoshop tag
3. reference_media_original.jpg: Base image to index into duplicate database
4. reference_media_recycled.jpg: Resized and recompressed copy for duplicate matching
"""

import os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import piexif

SAMPLES_DIR = Path(__file__).resolve().parent


def generate_samples():
    SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
    width, height = 800, 600

    print("Generating synthetic demo assets in samples/ ...")

    # -------------------------------------------------------------
    # 1. Authentic Camera Photograph with Canon EOS R5 EXIF
    # -------------------------------------------------------------
    x = np.linspace(0, 1, width)
    y = np.linspace(0, 1, height)
    xx, yy = np.meshgrid(x, y)
    r = np.clip((120 + 80 * (1 - yy) + np.random.normal(0, 3, (height, width))), 0, 255).astype(np.uint8)
    g = np.clip((150 + 60 * (1 - yy) + 40 * yy + np.random.normal(0, 3, (height, width))), 0, 255).astype(np.uint8)
    b = np.clip((190 + 50 * (1 - yy) - 30 * yy + np.random.normal(0, 3, (height, width))), 0, 255).astype(np.uint8)
    img_real = Image.fromarray(np.dstack([r, g, b]))

    zeroth_ifd = {
        piexif.ImageIFD.Make: b"Canon",
        piexif.ImageIFD.Model: b"Canon EOS R5",
        piexif.ImageIFD.DateTime: b"2024:05:18 14:22:10",
        piexif.ImageIFD.Software: b"Canon Digital Camera Firmware 1.4",
    }
    exif_ifd = {
        piexif.ExifIFD.ExposureTime: (1, 250),
        piexif.ExifIFD.FNumber: (28, 10),
        piexif.ExifIFD.ISOSpeedRatings: 100,
        piexif.ExifIFD.LensModel: b"RF24-70mm F2.8 L IS USM",
    }
    exif_bytes = piexif.dump({"0th": zeroth_ifd, "Exif": exif_ifd})
    real_out = SAMPLES_DIR / "authentic_camera_photo.jpg"
    img_real.save(real_out, format="JPEG", quality=95, exif=exif_bytes)
    print(f"  [OK] Created: {real_out.name} (with Canon EXIF headers)")

    # -------------------------------------------------------------
    # 2. Spliced / Tampered Photo (causes ELA anomaly)
    # -------------------------------------------------------------
    img_tampered = img_real.copy()
    draw = ImageDraw.Draw(img_tampered)
    # Insert a high-contrast spliced box that will light up under ELA
    draw.rectangle([250, 180, 550, 380], fill=(240, 20, 50), outline=(255, 255, 255), width=3)
    draw.text((270, 260), "UNIFORM INSERTION PATCH", fill=(255, 255, 255))

    tampered_zeroth = {
        piexif.ImageIFD.Make: b"Canon",
        piexif.ImageIFD.Model: b"Canon EOS R5",
        piexif.ImageIFD.Software: b"Adobe Photoshop 2024 (Windows)",
    }
    tampered_exif = piexif.dump({"0th": tampered_zeroth})
    tampered_out = SAMPLES_DIR / "spliced_tampered_photo.jpg"
    img_tampered.save(tampered_out, format="JPEG", quality=90, exif=tampered_exif)
    print(f"  [OK] Created: {tampered_out.name} (with ELA splicing patch & Photoshop tag)")

    # -------------------------------------------------------------
    # 3. Duplicate Test Reference Assets
    # -------------------------------------------------------------
    ref_img = Image.new("RGB", (512, 512), color=(40, 160, 220))
    ref_draw = ImageDraw.Draw(ref_img)
    ref_draw.ellipse([100, 100, 412, 412], fill=(255, 180, 20), outline=(255, 255, 255), width=8)
    ref_draw.rectangle([180, 220, 332, 292], fill=(60, 60, 60))

    ref_orig_out = SAMPLES_DIR / "reference_media_original.jpg"
    ref_img.save(ref_orig_out, format="JPEG", quality=95)
    print(f"  [OK] Created: {ref_orig_out.name} (for indexing into duplicate database)")

    # Recycled version: scaled down 50% and recompressed at 65% quality
    recycled_img = ref_img.resize((256, 256), Image.Resampling.BILINEAR)
    ref_recycled_out = SAMPLES_DIR / "reference_media_recycled.jpg"
    recycled_img.save(ref_recycled_out, format="JPEG", quality=65)
    print(f"  [OK] Created: {ref_recycled_out.name} (recompressed, scaled duplicate)")

    print("\n[Done] All demo assets generated successfully.")


if __name__ == "__main__":
    generate_samples()
