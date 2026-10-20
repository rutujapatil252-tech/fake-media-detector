"""
C2PA (Coalition for Content Provenance and Authenticity) Check.

The C2PA open standard provides tamper-evident provenance metadata ("Content Credentials")
cryptographically bound to digital media assets. Supported by industry leaders (Adobe, Microsoft,
Google, Truepic, Leica, Nikon, Sony), C2PA manifests cryptographically record who produced an asset,
the capture device or editing software utilized, the history of alterations, and whether
generative AI was involved (e.g., via digitalSourceType assertions like 'trainedAlgorithmicMedia').

Critical Forensic Considerations & Limitations:
1. Absence is NOT proof of manipulation: Mainstream social media networks (e.g., X/Twitter,
   Instagram, WhatsApp) routinely strip all embedded container metadata and JUMBF manifests
   upon upload to optimize bandwidth and privacy. Therefore, an image lacking a C2PA manifest
   must receive a NEUTRAL score (0.5), not a high-risk score.
2. Cryptographic Integrity: If a manifest IS present, we verify digital signatures against trusted
   X.509 PKI roots. A broken signature or altered binary payload flags active tampering.
3. Declarative AI Flags: Content Credentials declare whether an asset was generated or edited
   using generative AI (e.g., Adobe Firefly, Midjourney, OpenAI DALL-E).
"""

import json
import os
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional

from app.config import (
    C2PA_AI_GENERATED_RISK,
    C2PA_AUTHENTIC_RISK,
    C2PA_INVALID_MANIFEST_RISK,
    C2PA_NEUTRAL_RISK,
)

# Detect if c2pa-python is available and importable
C2PA_AVAILABLE = False
C2PA_IMPORT_ERROR: Optional[str] = None

try:
    import c2pa
    from c2pa import Reader, C2paError
    C2PA_AVAILABLE = True
except Exception as _err:
    C2PA_AVAILABLE = False
    C2PA_IMPORT_ERROR = str(_err)


# AI generator keywords and digital source types in C2PA assertions
AI_DIGITAL_SOURCE_TYPES = {
    "trainedalgorithmicmedia",
    "compositewithtrainedalgorithmicmedia",
    "algorithmicmedia",
    "datadrivenmedia",
    "virtualrecording",
}

AI_INDICATOR_KEYWORDS = [
    "midjourney",
    "dall-e",
    "dalle",
    "stable diffusion",
    "stablediffusion",
    "firefly",
    "novelai",
    "comfyui",
    "flux",
    "leonardo",
    "bing image creator",
]


def _detect_ai_declaration(manifest_data: Dict[str, Any], active_manifest: Dict[str, Any]) -> bool:
    """
    Inspects assertions and actions in a C2PA manifest to detect declared Generative AI origins.

    Checks:
    1. digitalSourceType in 'c2pa.actions' assertions
    2. digitalSourceType URI / IPTC values
    3. Claim generator signatures matching known AI generation pipelines
    4. Explicit training-mining assertions
    """
    # 1. Search actions
    assertions = active_manifest.get("assertions", [])
    for assertion in assertions:
        label = str(assertion.get("label", "")).lower()
        data = assertion.get("data", {})

        # Check actions
        if "c2pa.actions" in label and isinstance(data, dict):
            actions = data.get("actions", [])
            for action in actions:
                if isinstance(action, dict):
                    source_type = str(action.get("digitalSourceType", "")).lower()
                    for ai_type in AI_DIGITAL_SOURCE_TYPES:
                        if ai_type in source_type:
                            return True

                    # Check software agents in action
                    software_agent = str(action.get("softwareAgent", "")).lower()
                    if any(kw in software_agent for kw in AI_INDICATOR_KEYWORDS):
                        return True

        # Check general digitalSourceType assertions
        if "digitalsourcetype" in label:
            source_str = json.dumps(data).lower()
            if any(ai_type in source_str for ai_type in AI_DIGITAL_SOURCE_TYPES):
                return True

    # 2. Check claim generator name for AI generators
    claim_gen = str(active_manifest.get("claim_generator", "")).lower()
    claim_gen_info = active_manifest.get("claim_generator_info", [])
    if isinstance(claim_gen_info, list):
        for info in claim_gen_info:
            if isinstance(info, dict):
                claim_gen += " " + str(info.get("name", "")).lower()

    if any(kw in claim_gen for kw in AI_INDICATOR_KEYWORDS):
        return True

    return False


def analyze_c2pa(image_bytes: bytes) -> Dict[str, Any]:
    """
    Analyzes C2PA Content Credentials provenance metadata in uploaded image bytes.

    Gracefully handles absence of manifests, broken signatures, and library environment errors
    without raising uncaught exceptions.

    Args:
        image_bytes: Raw binary image bytes.

    Returns:
        dict: Normalized C2PA inspection results conforming to C2PACheckResult schema.
    """
    # Fallback if library cannot be loaded on this system
    if not C2PA_AVAILABLE:
        return {
            "has_manifest": False,
            "is_valid": None,
            "issuer": None,
            "claim_generator": None,
            "actions": [],
            "ai_generated_flag": False,
            "validation_errors": [],
            "risk_score": C2PA_NEUTRAL_RISK,
            "error": f"c2pa-python unavailable: {C2PA_IMPORT_ERROR}",
            "note": (
                "C2PA inspection library could not be loaded in the current runtime environment. "
                "Defaulting to neutral risk (0.5)."
            ),
        }

    # Write to a secure temporary file to ensure binary container compatibility
    temp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".tmp", delete=False) as tmp_file:
            tmp_file.write(image_bytes)
            tmp_file.flush()
            temp_path = tmp_file.name

        # Attempt to read manifest via Reader
        try:
            with Reader(temp_path) as reader:
                manifest_json_str = reader.json()
                manifest_data = json.loads(manifest_json_str) if manifest_json_str else {}
                active_manifest = reader.get_active_manifest() or {}
                validation_state = reader.get_validation_state()
                validation_results = reader.get_validation_results() or {}

                # Extract issuer
                signature_info = active_manifest.get("signature_info") or {}
                issuer = signature_info.get("issuer")

                # Extract claim generator
                claim_generator = active_manifest.get("claim_generator")
                if not claim_generator and "claim_generator_info" in active_manifest:
                    info_list = active_manifest.get("claim_generator_info")
                    if isinstance(info_list, list) and info_list:
                        claim_generator = info_list[0].get("name")

                # Extract actions
                actions_list: List[str] = []
                for assertion in active_manifest.get("assertions", []):
                    if assertion.get("label") == "c2pa.actions":
                        action_items = assertion.get("data", {}).get("actions", [])
                        for item in action_items:
                            if isinstance(item, dict):
                                act_name = item.get("action", "")
                                if act_name:
                                    actions_list.append(str(act_name))
                            elif isinstance(item, str):
                                actions_list.append(item)

                # Validation state & errors
                validation_errors: List[str] = []
                is_valid: Optional[bool] = None

                if validation_state is not None:
                    is_valid = validation_state.strip().lower() in {"valid", "ok", "passed"}
                    if not is_valid:
                        validation_errors.append(f"Validation state: {validation_state}")

                # Collect errors from validation_results if present
                if isinstance(validation_results, dict):
                    errors = validation_results.get("errors") or []
                    for err in errors:
                        if isinstance(err, dict):
                            validation_errors.append(str(err.get("description") or err.get("code") or err))
                        elif isinstance(err, str):
                            validation_errors.append(err)

                # Detect AI declaration
                ai_generated = _detect_ai_declaration(manifest_data, active_manifest)

                # Determine risk score based on forensic provenance rules
                if not is_valid and validation_errors:
                    # Broken or tampered manifest signature indicates high risk
                    risk_score = C2PA_INVALID_MANIFEST_RISK
                    note = "C2PA manifest signature is invalid or tampered with."
                elif ai_generated:
                    # Explicitly declared as Generative AI
                    risk_score = C2PA_AI_GENERATED_RISK
                    note = "C2PA manifest explicitly declares generative AI origins (e.g. trainedAlgorithmicMedia)."
                elif is_valid is True:
                    # Valid signature from camera or legitimate editing software
                    risk_score = C2PA_AUTHENTIC_RISK
                    note = f"Valid C2PA Content Credentials verified from issuer: {issuer or 'Trusted Authority'}."
                else:
                    # Valid structure, neutral/low risk
                    risk_score = 0.2
                    note = "Valid C2PA manifest found without generative AI flags."

                return {
                    "has_manifest": True,
                    "is_valid": is_valid,
                    "issuer": issuer,
                    "claim_generator": claim_generator,
                    "actions": actions_list,
                    "ai_generated_flag": ai_generated,
                    "validation_errors": validation_errors,
                    "risk_score": risk_score,
                    "error": None,
                    "note": note,
                }

        except C2paError.ManifestNotFound:
            # Expected standard case for images without C2PA credentials
            return {
                "has_manifest": False,
                "is_valid": None,
                "issuer": None,
                "claim_generator": None,
                "actions": [],
                "ai_generated_flag": False,
                "validation_errors": [],
                "risk_score": C2PA_NEUTRAL_RISK,
                "error": None,
                "note": (
                    "No C2PA Content Credentials manifest found. Absence of credentials is not "
                    "proof of tampering because social media and online platforms routinely strip container metadata."
                ),
            }

        except Exception as c2pa_err:
            # Non-fatal error during C2PA parsing
            return {
                "has_manifest": False,
                "is_valid": None,
                "issuer": None,
                "claim_generator": None,
                "actions": [],
                "ai_generated_flag": False,
                "validation_errors": [str(c2pa_err)],
                "risk_score": C2PA_NEUTRAL_RISK,
                "error": str(c2pa_err),
                "note": f"Error parsing C2PA manifest: {str(c2pa_err)}",
            }

    except Exception as general_err:
        return {
            "has_manifest": False,
            "is_valid": None,
            "issuer": None,
            "claim_generator": None,
            "actions": [],
            "ai_generated_flag": False,
            "validation_errors": [],
            "risk_score": C2PA_NEUTRAL_RISK,
            "error": str(general_err),
            "note": f"C2PA inspection encountered an unexpected error: {str(general_err)}",
        }

    finally:
        # Guarantee cleanup of temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
