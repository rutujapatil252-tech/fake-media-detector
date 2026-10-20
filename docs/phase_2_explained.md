# Fake Media Detector — Phase 2 Technical Guide & Interview Prep

## 1. Executive Summary & Architecture Evolution

In **Phase 1**, the Fake Media Detector established the foundational pipeline:
- Ingestion, validation, and error-handling via **FastAPI**
- **EXIF Metadata Inspection** (`checks/metadata.py`) to detect editing tool signatures and missing camera headers
- **Error Level Analysis (ELA)** (`checks/ela.py`) to visualize compression variance anomalies and splicing artifacts

In **Phase 2**, we expand the forensic suite with two industry-standard capabilities:
1. **Provenance & Cryptographic Content Credentials via C2PA** (`checks/c2pa_check.py`):
   Detects whether an image carries cryptographically signed assertions from capture devices (Leica, Sony, Nikon) or generative AI tools (Adobe Firefly, DALL-E, Midjourney).
2. **Perceptual Hashing & Duplicate / Cheapfake Detection** (`checks/duplicate.py`):
   Maps images into structural visual fingerprints (pHash, aHash, dHash, wHash) and indexes them in a lightweight **SQLite** database (`backend/data/hashes.db`). Exposes recycled imagery and viral misinformation.

```text
                               POST /analyze (multipart/form-data)
                                              │
                                              ▼
                                     FastAPI (app/main.py)
                                              │
                        ┌─────────────────────┴─────────────────────┐
                        ▼                                           ▼
             [ Security Validation ]                    [ Forensic Check Registry ]
             - 10MB limit                                (app/checks/__init__.py)
             - .jpg, .png, .webp                                    │
             - Binary decodability                                  │
                                         ┌──────────────┬───────────┴───┬──────────────┐
                                         ▼              ▼               ▼              ▼
                                    [ Metadata ]     [ ELA ]         [ C2PA ]     [ Duplicate ]
                                   (metadata.py)    (ela.py)     (c2pa_check.py) (duplicate.py)
                                                                                       │
                                                                                       ▼
                                                                                [ SQLite DB ]
                                                                             (data/hashes.db)
```

---

## 2. Deep Dive: Forensic Concepts Explained in Simple Terms

### A. What is C2PA / Content Credentials?
- **What it is**: **C2PA** (Coalition for Content Provenance and Authenticity) is an open technical standard governed by the Linux Foundation and backed by Adobe, Microsoft, Google, Intel, Sony, Nikon, Leica, and the BBC.
- **How it works**: It embeds cryptographically signed manifests (using JUMBF — *JPEG Universal Metadata Box Format*) directly into the media container. The manifest records:
  - Who signed the image (the certificate issuer)
  - What device or software made it (the claim generator)
  - What edits were performed (e.g., cropping, color grading)
  - Whether generative AI was utilized (e.g., `digitalSourceType: trainedAlgorithmicMedia`)
- **Crucial Rule — Why a missing manifest is NOT proof of a fake**:
  Almost all major social media platforms (X/Twitter, Facebook, Instagram, WhatsApp, Reddit) automatically strip metadata and container boxes upon upload to save bandwidth and protect user privacy (GPS stripping). As a result, millions of 100% authentic photos uploaded online have no C2PA credentials. Therefore:
  - **No manifest = Neutral Risk (0.5)** (never classify as fake).
  - **Valid camera manifest = Low Risk (0.1)**.
  - **Manifest declaring generative AI = High Risk (0.95)**.
  - **Broken or tampered signature = High Risk (0.9)**.

---

### B. What is Perceptual Hashing vs. Cryptographic Hashing?

#### Cryptographic Hashing (e.g., SHA-256 or MD5):
Designed for security and integrity verification. Even a **single bit change** in an image completely randomizes the resulting hash output (known as the *avalanche effect*).
- Image A (Original): `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Image A (1 pixel brightness shifted by 1%): `8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4`
- Result: **0% match**. Cryptographic hashes cannot detect recycled or recompressed media.

#### Perceptual Hashing (pHash, aHash, dHash, wHash):
Designed to emulate human visual perception. It extracts low-frequency structural features (e.g., via Discrete Cosine Transform or Haar Wavelets). Images that look visually similar produce **nearly identical hashes**.
- Image A (Original): `8f8f8700003c3c7e`
- Image A (Resized to 50% and saved at low JPEG quality): `8f8f8700003c3c7e`
- Result: **100% match!**

#### The 4 Algorithms Used in Our Implementation:
1. **pHash (DCT-based)**: Computes Discrete Cosine Transform; tracks frequency distribution; highly resistant to minor edits and scaling.
2. **aHash (Average)**: Compares 8x8 pixel blocks to overall average luminance; very fast baseline.
3. **dHash (Difference)**: Evaluates whether adjacent pixels are brighter or darker (gradient tracking); sensitive to structural composition.
4. **wHash (Wavelet)**: Uses Discrete Wavelet Transform (Haar); balances frequency and spatial domain stability.

---

### C. What is Hamming Distance?
**Hamming distance** is the number of bit positions in which two binary strings differ.
For two 64-bit hexadecimal hashes:
- `Hash 1`: `0000` (binary: `0000 0000 0000 0000`)
- `Hash 2`: `0001` (binary: `0000 0000 0000 0001`)
- **Hamming Distance**: `1` (differ only in 1 bit).

In our system:
- **Distance = 0**: Perceptually identical image (100% similarity).
- **Distance <= 10**: Near-duplicate (recompressed, resized, or minor watermark added; similarity >= 84%).
- **Distance > 20**: Visually distinct, completely different scenes.

---

## 3. How the New Modules Plug Into `/analyze`

The system adheres to the **Open-Closed Principle** via the registry pattern in [`backend/app/checks/__init__.py`](file:///c:/Users/Rutuja/.gemini/antigravity-ide/scratch/fake-media-detector/backend/app/checks/__init__.py):

```python
AVAILABLE_CHECKS: Dict[str, CheckFunction] = {
    "metadata": analyze_metadata,
    "ela": analyze_ela,
    "c2pa": analyze_c2pa,          # <-- Added in Phase 2
    "duplicate": analyze_duplicate,  # <-- Added in Phase 2
}
```

When a client sends `POST /analyze`, FastAPI invokes `run_all_checks(image_bytes)`. The dispatcher runs all 4 checks and packages them into the response without any tight coupling between routes and algorithms.

---

## 4. New Endpoints Overview

| Endpoint | Method | Input | Output | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| `/analyze` | `POST` | `multipart/form-data` image file | Full JSON report (4 checks) | Multi-vector forensic inspection |
| `/reference/add` | `POST` | `file` + `label` (form) | `{"id": int, "label": str, "status": "added"}` | Index a known reference image |
| `/reference/list` | `GET` | None | `{"references": [...], "count": int}` | Inspect database contents |
| `/health` | `GET` | None | `{"status": "ok"}` | Service liveness probe |

---

## 5. Top 6 Interview Questions & Model Answers

### Q1: Why can't we treat the absence of a C2PA manifest as evidence that an image is fake or AI-generated?
**Answer**:
"Because digital transmission channels strip metadata. When users upload images to WhatsApp, Twitter, Instagram, or Discord, those platforms transcode the image to reduce bandwidth and remove metadata for user privacy. If we assigned a high-risk score to images without C2PA manifests, we would produce a massive false positive rate for everyday authentic photos. Therefore, missing C2PA credentials must always be scored neutrally (around 0.5)."

---

### Q2: How does perceptual hashing (e.g., pHash) differ from cryptographic hashing (e.g., SHA-256), and why is pHash necessary here?
**Answer**:
"Cryptographic hashes are designed to maximize sensitivity: changing a single bit produces a completely different hash digest (the avalanche effect). In contrast, perceptual hashing is designed to maximize invariance: it captures the low-frequency visual structure of the image (via DCT or Wavelet analysis). If an image is resized, compressed as a JPEG, or slightly filtered, its perceptual hash remains identical or within a small Hamming distance (<= 10), enabling us to detect recycled viral misinformation."

---

### Q3: What is Hamming distance, and how do you calculate visual similarity percentage from it?
**Answer**:
"Hamming distance is the count of bit positions that differ between two equal-length binary strings. Our perceptual hashes are 64-bit values. A Hamming distance of 0 means 0 differing bits (identical). We calculate similarity percentage as:
`similarity = max(0.0, (1.0 - (average_hamming_distance / 64.0)) * 100.0)`.
For example, an average Hamming distance of 4 out of 64 bits yields a 93.75% visual similarity."

---

### Q4: Why did you choose SQLite without an ORM for storing perceptual hashes in Phase 2?
**Answer**:
"SQLite is built directly into Python's standard library (`sqlite3`), requiring zero external database services or heavyweight ORMs like SQLAlchemy. For our reference database, the schema is simple (id, label, 4 hash strings, and a timestamp), and queries are straightforward point lookups and linear scans. We also implemented explicit connection lifecycle management (`get_db_connection`) to prevent file lock issues on Windows, and enabled custom database path injection so unit tests run in isolated temporary directories without polluting production data."

---

### Q5: How do you detect if a C2PA manifest declares Generative AI?
**Answer**:
"The C2PA standard utilizes the IPTC Digital Source Type taxonomy. We inspect the manifest's assertion store — specifically assertions with the `c2pa.actions` label. Inside each action, we evaluate the `digitalSourceType` field for values such as `trainedAlgorithmicMedia`, `compositeWithTrainedAlgorithmicMedia`, or `algorithmicMedia`. We also inspect the `claim_generator` string for known AI synthesis pipelines such as Adobe Firefly, Midjourney, or DALL-E."

---

### Q6: What happens if the `c2pa-python` native binary library fails to load on a host machine?
**Answer**:
"We implemented a defensive import pattern. If `c2pa-python` is unavailable or if operating system policies block its native C/Rust DLL, our module catches the exception at import or runtime, falls back gracefully, and returns `has_manifest=False`, a neutral risk score of `0.5`, and an informative error message in the response payload. The server never crashes, and other forensic checks (Metadata, ELA, and Duplicate detection) continue operating normally."
