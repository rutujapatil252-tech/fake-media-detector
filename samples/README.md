# Sample Media for Live Demos & Evaluations

This folder provides a catalog of test assets designed for live presentations, automated evaluations, and benchmark testing.

---

## Recommended Demo Categories

When demonstrating the **Fake Media Detector** in an interview or showcase, test with assets representing distinct forensic profiles:

| Category | Typical Forensic Signatures | Expected Detection Profile |
| :--- | :--- | :--- |
| **1. Authentic Camera Photograph** | Valid camera EXIF tags (Make, Model, Exposure), natural sensor Bayer noise, consistent JPEG ELA compression gradient, no C2PA AI flags. | `Likely Authentic` (Score < 0.30, High Confidence) |
| **2. Synthetic AI Image (Midjourney, SDXL, DALL-E)** | Latent diffusion artifacts in high-frequency spectrum, absent or non-camera EXIF headers, elevated AI classifier probability (>0.90). | `Likely AI-generated` (Score >= 0.65, High Confidence) |
| **3. C2PA Provenance Certified Image** | Cryptographically signed manifest (JUMBF container) declaring tool generator or explicit generative AI disclosure assertion. | Absolute Override (`Likely AI-generated` or Verified Authentic with deduction) |
| **4. Manipulated / Spliced Image** | Localized ELA error hotspots showing mismatched compression blocks, editing software tags in EXIF (e.g. Photoshop, GIMP). | `Possibly Manipulated` (Score 0.45 – 0.65) |
| **5. Recycled Reference Image (Meme / Breaking News)** | Pre-registered in perceptual hash database; triggers low Hamming distance (pHash distance <= 8) with >=85% visual similarity. | Reason added: *"Near-duplicate match found in reference database"* |

---

## Generating Synthetic Test Assets

To avoid distributing copyrighted media while providing immediate demo files, run the generator script:

```bash
# From workspace root:
python samples/generate_demo_samples.py
```

This generates:
- `authentic_camera_photo.jpg`: Synthetic landscape with realistic sensor noise and Canon EOS R5 EXIF headers.
- `spliced_tampered_photo.jpg`: Image with a spliced high-contrast patch causing elevated ELA error levels and Photoshop metadata tags.
- `ai_synthetic_sample.jpg`: Diffusion render generated for demonstration.
- `reference_media_original.jpg`: Base image to index into the duplicate database.
- `reference_media_recycled.jpg`: Recompressed, resized (50%) copy demonstrating perceptual hash resilience.

---

## Adding Your Own Real Photos and AI Images

1. **Adding your own authentic camera photo**:
   - Take a picture directly from your smartphone or DSLR.
   - Transfer it via direct USB or cable (do **not** send via WhatsApp or social media, as they strip EXIF headers).
   - Save it into this directory as `my_camera_photo.jpg`.

2. **Adding an AI-generated image**:
   - Generate an image using Midjourney, ChatGPT / DALL-E 3, or Stable Diffusion.
   - Save the raw generated output into this directory as `my_ai_image.png` or `my_ai_image.jpg`.
