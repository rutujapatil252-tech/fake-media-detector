# Fake Media Detector — Web Client

A modern, responsive React + Vite + Tailwind CSS frontend for the **Fake Media Detector** forensic analysis platform.

## Features

- **Drag-and-Drop Media Upload**: Direct client-side validation for JPG, JPEG, PNG, and WebP files up to 10 MB.
- **Explainable Verdict Card**: Prominently highlights the synthesized decision (`likely_ai_generated`, `possibly_manipulated`, `likely_authentic`, or `inconclusive`), the overall suspicion percentage gauge, and the system confidence level (`high`, `medium`, `low`).
- **"Why This Verdict" Breakdown**: Direct plain-English forensic rationale explaining exactly which checks triggered anomalies and why.
- **Forensic Evidence Matrix**: Overview table displaying status chips (`Suspicious`, `Neutral`, `Clean`, `Unavailable`), normalized risk scores, and summary findings for all 5 independent forensic checks.
- **Deep-Dive Forensic Tabs**:
  - **AI Synthesis**: Vision Transformer diffusion classifier confidence distribution, raw softmax scores, and model metadata.
  - **Error Level Analysis (ELA)**: Side-by-side comparison of the original upload and the 10x amplified JPEG compression error heatmap.
  - **C2PA Provenance**: Cryptographic manifest verification, generator tools, issuer credentials, and explicit AI generation flags.
  - **EXIF Metadata**: Camera hardware signatures, timestamp chronology, editing software red flags, and raw header attributes.
  - **Perceptual Duplicate Matcher**: 64-bit DCT perceptual hash (pHash, aHash, dHash) and similarity percentage against the reference database.
- **Reference Image Database Manager**: Modal interface allowing users to index new ground-truth reference images into the perceptual hash database (`POST /reference/add`) and query indexed records (`GET /reference/list`).
- **Forensic Report Export**: One-click download of the complete raw JSON forensic report.
- **Responsible Forensics Disclaimer**: Explicit notice emphasizing that heuristics and stripped metadata are probabilistic indicators rather than definitive proof of forgery.

---

## Prerequisites

- **Node.js**: v18.0.0 or higher
- **Backend API**: Running on `http://localhost:8000` (FastAPI backend)

---

## Installation & Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Configure Environment Variables (Optional):**
   By default, the client talks to `http://localhost:8000`. You can override this in `.env`:
   ```bash
   VITE_API_URL=http://localhost:8000
   ```

4. **Start Development Server:**
   ```bash
   npm run dev
   ```
   The application will run locally at `http://localhost:5173`.

5. **Build for Production:**
   ```bash
   npm run build
   ```
   The bundled production assets will be placed in the `dist/` directory.

---

## Project Structure

```
frontend/
├── public/                 # Static assets
├── src/
│   ├── assets/             # Icons and graphic resources
│   ├── components/
│   │   ├── CheckDetails.jsx     # In-depth forensic detail tabs (ELA heatmap, C2PA, EXIF, etc.)
│   │   ├── EvidenceTable.jsx    # Forensic evidence matrix table with status chips
│   │   ├── Navbar.jsx           # Top navigation bar with API health status indicator
│   │   ├── ReferenceManager.jsx # Modal for indexing & browsing perceptual hash reference images
│   │   ├── UploadBox.jsx        # Drag-and-drop file upload with client-side validation
│   │   └── VerdictCard.jsx      # Top-level synthesized verdict card with suspicion gauge
│   ├── api.js              # Centralized backend HTTP client (Fetch API)
│   ├── App.jsx             # Main single-page application workflow
│   ├── index.css           # Tailwind CSS directives and custom styling tokens
│   └── main.jsx            # React root entry point
├── index.html              # HTML5 entry with metadata
├── package.json            # Node.js scripts and dependencies
├── vite.config.js          # Vite configuration with Tailwind CSS plugin
└── README.md
```
