"""
Forensic checks package for Fake Media Detector.

Provides an extensible registry architecture so that adding forensic tests
(e.g., metadata, ELA, C2PA provenance, perceptual duplicate detection, and deep learning AI detection)
only requires registering a new analysis function without touching routing or schema code.
"""

from typing import Any, Callable, Dict
from app.checks.ela import analyze_ela
from app.checks.metadata import analyze_metadata
from app.checks.c2pa_check import analyze_c2pa
from app.checks.duplicate import analyze_duplicate
from app.checks.ai_detector import analyze_ai_generated

# Type alias for a forensic check function
CheckFunction = Callable[[bytes], Dict[str, Any]]

# Central registry of available checks.
# Phase 1: metadata, ela
# Phase 2: c2pa, duplicate
# Phase 3: ai_detector
AVAILABLE_CHECKS: Dict[str, CheckFunction] = {
    "metadata": analyze_metadata,
    "ela": analyze_ela,
    "c2pa": analyze_c2pa,
    "duplicate": analyze_duplicate,
    "ai_detector": analyze_ai_generated,
}


def run_all_checks(image_bytes: bytes) -> Dict[str, Any]:
    """
    Executes all registered forensic checks sequentially against the provided image bytes.

    Args:
        image_bytes: Raw binary bytes of the uploaded image.

    Returns:
        dict: Mapping of check name -> check result dictionary.
    """
    results: Dict[str, Any] = {}
    for name, check_fn in AVAILABLE_CHECKS.items():
        results[name] = check_fn(image_bytes)
    return results


__all__ = [
    "analyze_metadata",
    "analyze_ela",
    "analyze_c2pa",
    "analyze_duplicate",
    "analyze_ai_generated",
    "AVAILABLE_CHECKS",
    "run_all_checks",
]
