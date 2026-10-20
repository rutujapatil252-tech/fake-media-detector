# Phase 4 Explained: Explainable Verdict Engine & Modern Web Interface

This document explains the architecture, design choices, scoring mathematics, and frontend-backend communication implemented in **Phase 4** of the **Fake Media Detector** project.

---

## 1. System Architecture: From Upload to Verdict

The Fake Media Detector operates as a decoupled, multi-layered forensic platform:

```
[User Browser / Client]
        │
        │ 1. Drag & drop image (client-side validation: format & <=10MB)
        ▼
   [UploadBox.jsx] ────► [api.js (FormData)]
                               │
                               │ 2. HTTP POST /analyze
                               ▼
                    [FastAPI Backend (app/main.py)]
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
 3. [EXIF Check]         [ELA Check]            [C2PA Check]
 (Camera tags & flags) (Compression heatmaps) (Cryptographic manifest)
        │                      │                      │
 4. [Duplicate Check]    [AI Vision Check]            │
 (Perceptual pHash DB) (ViT Diffusion model)          │
        │                      │                      │
        └──────────────────────┬──────────────────────┘
                               │
                               ▼ 5. checks dictionary
                    [Verdict Engine (app/verdict.py)]
                    - Weighted average aggregation
                    - Offline/error weight renormalization
                    - Provenance & heuristic overrides
                    - Confidence assessment
                               │
                               ▼ 6. Combined JSON response
                    { filename, checks, verdict, processing_time_ms }
                               │
                               ▼
                     [React Client (App.jsx)]
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
  [VerdictCard]         [EvidenceTable]         [CheckDetails]
 (Label & gauge)       (Status chips & scores) (Side-by-side ELA & tabs)
```

---

## 2. How the Verdict Engine Works Step by Step

The function `compute_verdict(checks: dict) -> dict` in `backend/app/verdict.py` evaluates the forensic signals through six systematic steps:

### Step 1: Filter Available Checks & Extract Evidence
Each forensic check (`ai_detector`, `ela`, `metadata`, `c2pa`, `duplicate`) is inspected:
- If a check threw an exception or has `check.get("error")`, it is marked as `"unavailable"`.
- If available, its `risk_score` (between `0.0` and `1.0`) is parsed, and it is assigned an evidence status:
  - `suspicious` if `risk_score >= 0.65`
  - `clean` if `risk_score <= 0.30`
  - `neutral` otherwise.
- A concise plain-English `summary` is attached.

### Step 2: Weight Renormalization
Each check has a configured base weight in `app/config.py`:
- `ai_detector`: 0.45
- `ela`: 0.15
- `metadata`: 0.15
- `c2pa`: 0.15
- `duplicate`: 0.10
*(Sum of base weights = 1.0)*

If any check is unavailable (for example, the AI model server is offline or crashed), its weight is excluded and the remaining available weights are **renormalized** so that their sum equals `1.0`:
$$\text{normalized\_weight}_i = \frac{\text{weight}_i}{\sum_{j \in \text{available}} \text{weight}_j}$$

$$\text{overall\_score} = \sum_{i \in \text{available}} \left(\text{risk\_score}_i \times \text{normalized\_weight}_i\right)$$

### Step 3: Forensic & Provenance Overrides
Authoritative cryptographic and heuristic signals can modify the score or enforce an absolute verdict:
1. **C2PA Generative AI Override**: If `c2pa.get("ai_generated_flag") is True`, the authoring software cryptographically certified that the media was synthesized by AI.
   - **Action**: Force `label = "likely_ai_generated"`, `overall_score = max(overall_score, 0.95)`, `confidence = "high"`, and add explanation reason.
2. **C2PA Authentic Hardware Manifest**: If a valid C2PA manifest is present without AI flags (e.g., from a certified Leica or Sony camera):
   - **Action**: Reduce overall suspicion score by `0.20` (bounded to `0.0`), and add explanation reason.
3. **C2PA Tampered Manifest**: If a manifest is present but cryptographic signature validation failed:
   - **Action**: Increase score by `0.25` (capped at `1.0`), and add a warning reason.
4. **Duplicate Reuse Finding**: If perceptual hash matches a known database image (`is_duplicate is True`):
   - **Action**: Add an informative reason flagging potential recycled or reused media.

### Step 4: Classification Label Assignment
The synthesized `overall_score` is mapped to categorical thresholds:
- $\ge 0.65 \implies$ `"likely_ai_generated"` (*"Likely AI-generated"*)
- $0.45 \text{ to } 0.65 \implies$ `"possibly_manipulated"` (*"Possibly manipulated"*)
- $< 0.30 \implies$ `"likely_authentic"` (*"Likely authentic"*)
- Otherwise $\implies$ `"inconclusive"` (*"Inconclusive"*)

*Fallback Rule*: If `ai_detector` was unavailable and no other strong suspicious signals exist ($\text{overall\_score} < 0.65$), the system defaults to `"inconclusive"` because pixel-level AI artifacts could not be evaluated.

### Step 5: Confidence Calculation
Confidence is scored based on agreement across independent signals:
- **`"high"`**: C2PA override triggered, or $\ge 3$ checks agree on the same status, or the top-weighted signals strongly align.
- **`"low"`**: Strong conflict (e.g., one check indicates $>0.80$ while another indicates $<0.15$), or fewer than 2 checks were available.
- **`"medium"`**: Standard multi-signal baseline.

---

## 3. Worked Numeric Examples

### Example A: Standard Multi-Vector Weighted Average
An uploaded image yields the following risk scores:
- `ai_detector`: $0.80$ (Weight: $0.45$)
- `ela`: $0.50$ (Weight: $0.15$)
- `metadata`: $0.60$ (Weight: $0.15$)
- `c2pa`: $0.20$ (Weight: $0.15$)
- `duplicate`: $0.00$ (Weight: $0.10$)

**Calculation:**
$$\text{overall\_score} = (0.80 \times 0.45) + (0.50 \times 0.15) + (0.60 \times 0.15) + (0.20 \times 0.15) + (0.00 \times 0.10)$$
$$\text{overall\_score} = 0.36 + 0.075 + 0.090 + 0.030 + 0.000 = 0.555$$

**Outcome:**
- Score: $0.56$ ($56\%$)
- Threshold: Between $0.45$ and $0.65 \implies$ **`possibly_manipulated`**
- Confidence: **`medium`** (AI detector is elevated, but duplicate is 0 and C2PA is low)

---

### Example B: Unavailable Check with Renormalization and C2PA Override
Suppose the `ai_detector` server is down (`unavailable`), but `c2pa` contains an embedded generative AI flag (`ai_generated_flag: True`):
- Available weights: `ela` ($0.15$), `metadata` ($0.15$), `c2pa` ($0.15$), `duplicate` ($0.10$).
- Total available weight sum = $0.15 + 0.15 + 0.15 + 0.10 = 0.55$.
- Normalized weight for `ela` = $\frac{0.15}{0.55} \approx 0.2727$.
- Even with nominal base scores, the **C2PA Generative AI Override** immediately triggers:
  - Label: **`likely_ai_generated`**
  - Display Label: **`"Likely AI-generated"`**
  - Overall Score: forced to $\ge 0.95$
  - Confidence: **`high`**
  - Reason added: *"C2PA Content Credentials explicitly declare this image was generated using AI tools."*

---

## 4. Key Design Decisions

### Why a Layered Report Instead of a Bare "Fake" or "Real"?
In digital media forensics, a binary "fake vs. real" binary output is dangerous, unscientific, and often wrong:
1. **Context Matters**: An authentic photograph opened in Photoshop to adjust brightness or crop for social media has modified EXIF metadata, but is not a deepfake.
2. **Platform Stripping**: Platforms like Twitter/X, Instagram, and WhatsApp strip EXIF and C2PA metadata on upload to protect user privacy and reduce bandwidth. Treating missing EXIF as proof of fakery would misclassify 99% of web photos.
3. **Probabilistic Nature of Deep Learning**: Vision Transformers output probabilities based on latent artifacts. Presenting raw scores alongside ELA compression heatmaps empowers human analysts to verify the evidence themselves.

### Why Exclude Unavailable Checks and Renormalize?
If an unavailable check was treated as $0.0$, the overall suspicion score would be artificially suppressed (false negative). If treated as $0.5$, it would artificially inflate suspicion on clean images. By removing unavailable checks from the denominator and scaling remaining weights proportionally, the system preserves fair mathematical balance.

---

## 5. Frontend-Backend Communication

1. **Client Request**: The browser packages the image into a `multipart/form-data` payload via standard `Fetch API` in `frontend/src/api.js`.
2. **Server Execution**: FastAPI processes the image across the 5 forensic check modules, runs `compute_verdict(checks)`, and tracks execution time with `time.perf_counter()`.
3. **Response Payload**:
   ```json
   {
     "filename": "sample.jpg",
     "file_size": 245100,
     "mime_type": "image/jpeg",
     "image_format": "JPEG",
     "image_dimensions": {"width": 1024, "height": 1024},
     "checks": { ... },
     "verdict": {
       "label": "likely_ai_generated",
       "display_label": "Likely AI-generated",
       "overall_score": 0.88,
       "confidence": "high",
       "reasons": ["AI synthesis detector identified diffusion artifacts (92.4% probability)."],
       "evidence": [ ... ]
     },
     "processing_time_ms": 142
   }
   ```
4. **State Management**: React (`App.jsx`) transitions from upload state to a loading spinner (`Running 5 independent forensic checks...`), then displays the `VerdictCard`, `EvidenceTable`, and tabbed `CheckDetails`. If an error occurs, an error card with a one-click retry button is presented.

---

## 6. Interview Questions & Model Answers

### Q1: How did you design the scoring engine to combine deep learning with traditional forensics?
> *"I built a layered ensemble engine. Rather than relying solely on a black-box neural network, our backend synthesizes five distinct signals: deep-learning diffusion classification, JPEG Error Level Analysis, C2PA cryptographic provenance, EXIF metadata tags, and perceptual hashing. We use a normalized weighted average combined with rule-based overrides for authoritative signals like cryptographic C2PA manifests."*

### Q2: Why does the system exclude unavailable checks and renormalize weights?
> *"In production environments, external services or heavy models might experience latency or failures. If we assigned an arbitrary default score like 0.0 or 0.5 to failed checks, we would bias the verdict toward either false negatives or false positives. Excluding the failed check and renormalizing the remaining available weights ensures that the final score reflects only verifiable evidence while maintaining a valid 0.0 to 1.0 scale."*

### Q3: How would you improve the scoring engine in a future iteration?
> *"Currently, weights and thresholds are heuristically tuned based on domain knowledge. In production, I would train a calibrated meta-classifier (such as a Logistic Regression or Gradient Boosted Tree) on a balanced, labeled benchmark dataset of real photos, spliced images, and diffusion-generated media. The model would learn the optimal feature weights directly from historical ground truth and output statistically calibrated confidence intervals."*

### Q4: Why must missing EXIF metadata never be treated as proof of fakery?
> *"Social media platforms and messaging apps like WhatsApp and Instagram routinely strip EXIF metadata to protect user privacy and save bandwidth. If our system flagged images without EXIF as fake, it would trigger massive false positive rates on benign web content. We treat missing EXIF as a neutral observation rather than suspicious evidence."*

### Q5: How is C2PA integrated, and why is it considered an override?
> *"C2PA (Coalition for Content Provenance and Authenticity) relies on public-key cryptography and digital certificates embedded directly into the media file. If an image contains a cryptographically valid C2PA manifest with an explicit generative AI flag (e.g. from DALL-E, Firefly, or Midjourney), that is an authoritative digital proof signed by the generating software. Because cryptographic signatures are tamper-evident, it supersedes heuristic estimates and immediately sets a high-confidence verdict."*

### Q6: How does the frontend handle heavy forensic assets like ELA heatmaps?
> *"Rather than saving heatmaps to disk and requiring separate static file serving or cloud storage URLs, the backend encodes the difference heatmap into an in-memory base64 PNG string (`heatmap_base64`). The React client renders this directly using a Data URL (`data:image/png;base64,...`) alongside the original preview, ensuring instant side-by-side rendering with zero file-system clutter or latency."*
