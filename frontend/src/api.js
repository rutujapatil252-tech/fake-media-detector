/**
 * API client service for Fake Media Detector.
 * Connects to the FastAPI backend running at VITE_API_URL (default: http://localhost:8000).
 */

// Detect current browser host to match localhost vs 127.0.0.1 and prevent IPv6 mismatch
const DEFAULT_HOST = typeof window !== 'undefined' && window.location.hostname 
  ? window.location.hostname 
  : '127.0.0.1';

const PRIMARY_URL = import.meta.env.VITE_API_URL || `http://${DEFAULT_HOST}:8000`;
const FALLBACK_URL = DEFAULT_HOST === '127.0.0.1' ? 'http://localhost:8000' : 'http://127.0.0.1:8000';

/**
 * Robust fetch helper that tries PRIMARY_URL, and falls back to FALLBACK_URL
 * if the first attempt encounters a network/connection failure.
 */
async function fetchWithFallback(endpoint, options = {}) {
  try {
    const res = await fetch(`${PRIMARY_URL}${endpoint}`, options);
    return res;
  } catch (err) {
    // If it was a network error (like connection refused), try the alternate host
    if (PRIMARY_URL !== FALLBACK_URL && (err.name === 'TypeError' || err.message?.includes('fetch'))) {
      try {
        const fallbackRes = await fetch(`${FALLBACK_URL}${endpoint}`, options);
        return fallbackRes;
      } catch {
        // Fallback also failed; throw original with clear diagnostic
        throw new Error(
          `Cannot connect to backend server at ${PRIMARY_URL} or ${FALLBACK_URL}. Please ensure FastAPI is running (uvicorn app.main:app --host 127.0.0.1 --port 8000).`
        );
      }
    }
    throw err;
  }
}

/**
 * Checks server health and connection status.
 */
export async function checkHealth() {
  const response = await fetchWithFallback('/health');
  if (!response.ok) {
    throw new Error(`Server returned status ${response.status}`);
  }
  return response.json();
}

/**
 * Submits an image file to POST /analyze for multi-vector forensic inspection.
 * @param {File} file - The image file to analyze
 * @returns {Promise<Object>} Analysis response including checks, verdict, and timing
 */
export async function analyzeImage(file) {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetchWithFallback('/analyze', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'Analysis request failed.';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = `Server error (${response.status}: ${response.statusText})`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Adds a reference image with a label to the perceptual hash database.
 * @param {File} file - Reference image file
 * @param {string} label - Human-readable description
 */
export async function addReferenceImage(file, label) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('label', label);

  const response = await fetchWithFallback('/reference/add', {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to index reference image.';
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      errorDetail = `Server error (${response.status})`;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Retrieves the list of stored reference images.
 * @returns {Promise<{references: Array, count: number}>}
 */
export async function listReferenceImages() {
  const response = await fetchWithFallback('/reference/list');
  if (!response.ok) {
    throw new Error(`Failed to fetch references (${response.status})`);
  }
  return response.json();
}

// Convenient aliases matching different component naming styles
export const addReference = addReferenceImage;
export const listReferences = listReferenceImages;
