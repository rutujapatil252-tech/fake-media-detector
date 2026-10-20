# Fake Media Detector — Phase 1 Technical Guide & Interview Prep

## 1. Overall Architecture

The **Fake Media Detector** backend is structured around a modular, pipeline-style architecture designed to ingest an uploaded media file, perform initial security and boundary validations, and run it through a suite of forensic analysis tests.

```text
                  [ Client / Frontend (React, Vite, Next.js) ]
                                      │
                         POST /analyze (multipart/form-data)
                                      ▼
                             FastAPI (app/main.py)
                                      │
              ┌───────────────────────┴───────────────────────┐
      [ Security & Validation ]                       [ Check Registry ]
       - File size limit (<= 10MB)                     (app/checks/__init__.py)
       - Extension allowlist (.jpg, .png, .webp)               │
       - MIME type verification                                ├──────────────┐
       - Deep Image.verify() decodability                      │              │
                                                               ▼              ▼
                                                     [ Metadata Check ]  [ ELA Check ]
                                                        (metadata.py)      (ela.py)
                                                               │              │
                                                               └──────┬───────┘
                                                                      ▼
                                                            [ JSON Response Payload ]
                                                             - Normalized Risk Scores
                                                             - Base64 ELA Heatmap
```

### Key Design Pillars:
1. **Separation of Concerns**: HTTP routing, domain validation, forensic algorithms, schemas, and configurations are decoupled into isolated modules.
2. **Open-Closed Principle (Check Registry)**: The system is *open for extension, closed for modification*. To add a new forensic check (e.g., deep-learning artifact detection or Discrete Cosine Transform analysis in Phase 2), developers only need to add a function in `checks/` and register it in `AVAILABLE_CHECKS`. The API route automatically executes it without any changes to `main.py`.
3. **Defense in Depth**: We don't just rely on filename extensions or client headers. We check extension, HTTP MIME header, payload size, and run PIL's binary verification (`img.verify()`) to guard against malicious uploads or corrupted data.
4. **Normalized Risk Scoring (0.0 to 1.0)**: Each check produces a risk score on a normalized scale, allowing downstream consumers (or an aggregate scoring engine) to compare and weight signals consistently.

---

## 2. File-by-File Breakdown

| File | Purpose | Why It Exists & Key Decisions |
| :--- | :--- | :--- |
| `backend/app/main.py` | FastAPI application entry point, CORS middleware, and API endpoints (`GET /health`, `POST /analyze`). | Handles HTTP protocols, request parsing, streaming file reading, and exception mappings. Kept free of algorithmic details. |
| `backend/app/config.py` | Centralized constants (MIME types, max file size, CORS origins, ELA thresholds). | Eliminates "magic numbers" scattered across the codebase. Makes tuning thresholds (e.g., changing ELA quality or size limits) trivial. |
| `backend/app/schemas.py` | Pydantic response models and typed contracts. | Ensures strong contract enforcement, automatic serialization, validation, and automated OpenAPI (Swagger) documentation generation. |
| `backend/app/checks/__init__.py` | Forensic check registry and batch runner (`run_all_checks`). | Acts as a plug-and-play dispatch layer for all present and future forensic checks. |
| `backend/app/checks/metadata.py` | EXIF and container metadata inspector. | Extracts camera info, editing software fingerprints, creation vs. modification timestamps, and AI generator tags. |
| `backend/app/checks/ela.py` | Error Level Analysis (ELA) engine. | Computes compression error variance by re-saving to JPEG at quality 90, scaling large images, and creating JET colormap heatmaps. |
| `backend/tests/test_checks.py` | Complete Pytest suite. | Generates synthetic images in-memory to test logic, boundaries, edge cases, and endpoints without relying on brittle external files. |
| `backend/requirements.txt` | Dependency specifications with pinned compatible versions. | Guarantees reproducible builds across environments. |

---

## 3. How the Forensic Checks Work

### A. EXIF & Metadata Analysis (`checks/metadata.py`)

#### How it works:
When a physical camera (such as an iPhone, Samsung Galaxy, or DSLR) takes a photograph, it writes a rich set of EXIF (Exchangeable Image File Format) metadata into the header of the JPEG/TIFF/WebP container. This includes:
- **Device Identifiers**: `Make` (e.g., Apple, Canon), `Model` (e.g., iPhone 15 Pro, EOS R5).
- **Timestamps**: `DateTimeOriginal` (when the shutter clicked) and `DateTime` (when the file was last modified).
- **Software Used**: If opened and re-exported in Adobe Photoshop, GIMP, or Canva, the application typically stamps its name in `Image Software`.
- **GPS Coordinates**: Latitude and longitude tags if location services were enabled.

#### Simple Example:
Imagine an authentic photo taken on a Nikon D850:
- `Make`: "NIKON CORPORATION"
- `Model`: "NIKON D850"
- `DateTimeOriginal`: "2024:04:10 11:20:00"
- `DateTime`: "2024:04:10 11:20:00"
- `Software`: None (or camera firmware like "Ver.1.20")
- **Risk Score**: `0.05` (Clean camera photo).

Now imagine someone pastes a fake politician into the photo using Adobe Photoshop:
- `Software`: "Adobe Photoshop 2024 (Macintosh)"
- `DateTime`: "2024:06:01 16:35:12" (differs from `DateTimeOriginal`)
- **Red Flags**:
  - `Image editing software detected in metadata: 'Adobe Photoshop 2024'`
  - `Timestamp discrepancy detected: Original (2024:04:10) differs from Modified (2024:06:01)`
- **Risk Score**: `0.75` (High risk of manipulation).

#### The Social Media Caveat (Crucial Interview Detail!):
> **Why Missing EXIF is a Weak Signal**:
> When a user uploads a photo to Twitter, Instagram, Facebook, or WhatsApp, those platforms **strip all EXIF metadata** to protect user privacy (preventing strangers from finding home GPS coordinates) and reduce file size.
> Therefore, an image lacking EXIF could simply be a legitimate family photo downloaded from Instagram. We assign a baseline uncertainty score (`0.35`) and explicitly document that missing EXIF is a weak clue, not definitive proof.

---

### B. Error Level Analysis (ELA) (`checks/ela.py`)

#### How it works:
JPEG compression is **lossy**. It converts an image from spatial coordinates to the frequency domain using the Discrete Cosine Transform (DCT) across 8x8 pixel blocks, quantizing high frequencies where human eyes are less sensitive.

Every time a JPEG is saved, some information is permanently discarded. If you repeatedly save a JPEG at the same quality level, it eventually reaches a **compression equilibrium** where subsequent saves produce minimal error.

**Error Level Analysis works by exploiting this equilibrium:**
1. We take the input image and re-save it in memory at a reference quality of **90**.
2. We subtract the re-saved image from the input image to measure the absolute per-pixel error:
   $$\text{Error}(x, y) = |\text{Original}(x, y) - \text{Resaved}(x, y)|$$
3. In an unmodified original photo, all regions of the image have gone through the exact same compression history, so the error rate across the entire image is relatively **uniform**.
4. If a fraudster pastes an uncompressed graphic (or an element from a different image) into the photo:
   - The original background is already near equilibrium and shows very low error.
   - The newly inserted element has never been compressed at that level before; it experiences massive quantization loss and lights up with high error.
5. We amplify this error and render it as an intuitive **JET colormap heatmap** (Blue = low error, Red/Yellow = high error).

#### Simple Example:
- **Authentic Photo**: A picture of a beach. When analyzed with ELA, the entire image exhibits a uniform dark-blue/cyan haze. Edges show slightly higher error (normal due to high-frequency transitions), but the error level is homogeneous across the whole frame.
- **Spliced Forgery**: Someone splices a shark fin into the ocean. The ocean shows very low error (blue), while the pasted shark fin glows bright yellow and red. The high localized discrepancy exposes the splice.

#### Limitations of ELA:
1. **Non-JPEG Formats**: PNGs or raw images have never been lossily compressed. Re-saving them as JPEG causes the entire canvas to light up with high error, which can fool naive algorithms into a false positive.
2. **High-Contrast Edges**: Genuine sharp edges (e.g., text, high-contrast tree branches against a bright sky) naturally produce higher DCT quantization error than smooth regions.
3. **Re-compression Washing**: If a manipulated image is downsized and heavily re-compressed across multiple passes (e.g., re-encoded multiple times), the error levels can equalize, causing a false negative.

---

## 4. Top 5 Job Interview Questions & Answers

### Q1: Why did you choose FastAPI over Flask or Django for this service?
**Answer:**
> "I chose FastAPI for three primary reasons:
> 1. **High Performance & Asynchronous I/O**: FastAPI is built on Starlette and Uvicorn, offering native `async/await` support which is ideal for streaming file uploads and concurrent forensic workloads.
> 2. **Type Safety & Automatic Validation**: Through Pydantic models, request payloads and response contracts are strictly validated at runtime with zero boilerplate, automatically preventing malformed requests.
> 3. **Interactive Documentation**: FastAPI automatically generates interactive OpenAPI/Swagger documentation (`/docs`), making API integration straightforward for frontend engineers and QA."

### Q2: How does your architecture handle scaling when new forensic checks need to be added?
**Answer:**
> "I implemented the Open-Closed Principle using an extensible **Check Registry pattern** in `app/checks/`. 
> All forensic checks share a standard signature `(image_bytes: bytes) -> dict`. In `app/checks/__init__.py`, checks are registered in an `AVAILABLE_CHECKS` map. The `/analyze` endpoint simply invokes the registry runner.
> When we want to add frequency domain analysis (FFT), noise inconsistency detection, or a PyTorch deepfake classifier in Phase 2, we can implement the new module and register it with a single line of code—without touching routing, HTTP validation, or existing check logic."

### Q3: Why can't we rely solely on EXIF metadata to determine if an image is authentic?
**Answer:**
> "EXIF metadata is a valuable heuristic, but it is neither necessary nor sufficient evidence of authenticity:
> 1. **Stripping by Platforms**: Social media networks (Twitter, Instagram, WhatsApp) strip EXIF metadata by design for privacy and bandwidth optimization. Lack of EXIF does not prove an image is fake.
> 2. **Trivial to Forge**: EXIF headers are plain text fields inside the file container. Anyone with tools like `exiftool` or Python can spoof camera make, model, and capture date in milliseconds.
> Therefore, we treat EXIF as a complementary clue and combine it with physical pixel-level analyses like ELA."

### Q4: How does Error Level Analysis work, and why do you resize large images before running it?
**Answer:**
> "ELA works by re-compressing the image as a JPEG at a reference quality (90) and calculating the absolute difference against the original. Because lossy JPEG compression reaches an equilibrium over successive saves, regions with differing compression histories (like a spliced element) exhibit distinct error rates.
> We downscale images exceeding 1024px for two reasons:
> 1. **Performance & Memory Protection**: Large multi-megapixel images (e.g., 48MP phone photos) consume hundreds of megabytes of RAM when expanded into uncompressed float32 NumPy arrays and take several seconds to process.
> 2. **Forensic Validity**: Downscaling to 1024px preserves the macroscopic compression boundaries and high-frequency discrepancies while ensuring sub-second response times and preventing DoS vulnerability from huge uploads."

### Q5: What security practices did you build into the file upload endpoint?
**Answer:**
> "We implement defense-in-depth across multiple layers:
> 1. **Extension Allowlist**: Strict check against `.jpg`, `.jpeg`, `.png`, and `.webp`.
> 2. **MIME Type Verification**: Ensures the `Content-Type` header matches standard image media types.
> 3. **File Size Hard Limits**: Enforces a strict 10 MB ceiling, rejecting oversized files with HTTP 400 before heavy computation occurs.
> 4. **Deep Binary Verification**: We use Pillow's `Image.open().verify()` on the byte stream to verify that the file is actually a decodable image and not an executable or malicious script disguised with an image extension.
> 5. **Safe Memory Operations**: Image transformations and ELA re-saves occur strictly in in-memory byte buffers (`io.BytesIO`), avoiding unsafe disk writes and preventing temporary file race conditions or path traversal vulnerabilities."
