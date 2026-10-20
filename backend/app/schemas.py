from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class HealthResponse(BaseModel):
    """Health check endpoint response schema."""
    status: str = Field(
        ...,
        description="Service status indicator",
        json_schema_extra={"example": "ok"}
    )


class MetadataCheckResult(BaseModel):
    """
    Schema for EXIF and file header metadata inspection results.
    """
    has_exif: bool = Field(
        ...,
        description="Whether EXIF metadata was discovered in the uploaded file"
    )
    fields: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of extracted camera, software, and timestamp properties"
    )
    red_flags: List[str] = Field(
        default_factory=list,
        description="List of detected anomalies or suspicious indicators"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated manipulation risk score from 0.0 (clean) to 1.0 (high risk)"
    )


class ELACheckResult(BaseModel):
    """
    Schema for Error Level Analysis (ELA) inspection results.
    """
    heatmap_base64: str = Field(
        ...,
        description="Base64-encoded PNG image displaying the amplified ELA heatmap"
    )
    mean_error: float = Field(
        ...,
        description="Average error/difference level across all image pixels"
    )
    max_error: float = Field(
        ...,
        description="Maximum observed error/difference value in any single pixel"
    )
    suspicious_region_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Fraction of pixels exceeding the anomaly difference threshold"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated manipulation risk score from 0.0 (uniform) to 1.0 (high variance/spliced)"
    )


class C2PACheckResult(BaseModel):
    """
    Schema for C2PA / Content Credentials provenance inspection results.
    """
    has_manifest: bool = Field(
        ...,
        description="Whether a C2PA manifest/JUMBF data was discovered in the image"
    )
    is_valid: Optional[bool] = Field(
        default=None,
        description="True if the manifest cryptographically validates against trusted roots; False if invalid; null if absent"
    )
    issuer: Optional[str] = Field(
        default=None,
        description="Name of the signing authority / certificate issuer"
    )
    claim_generator: Optional[str] = Field(
        default=None,
        description="Software or device that generated the claim (e.g., Photoshop, Leica, Truepic)"
    )
    actions: List[str] = Field(
        default_factory=list,
        description="List of recorded edit/provenance actions"
    )
    ai_generated_flag: bool = Field(
        default=False,
        description="Whether the manifest explicitly declares algorithmic / generative AI origins"
    )
    validation_errors: List[str] = Field(
        default_factory=list,
        description="List of validation errors or warnings reported by the C2PA parser"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Provenance risk score (0.1 authentic, 0.5 neutral/missing, 0.95 AI/tampered)"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if library parsing encountered an issue"
    )
    note: Optional[str] = Field(
        default=None,
        description="Forensic context note explaining the significance of the result"
    )


class DuplicateMatch(BaseModel):
    """
    Schema for a single matching reference image found via perceptual hashing.
    """
    id: int = Field(..., description="Unique database ID of the matching reference")
    label: str = Field(..., description="Label or description of the known reference")
    hamming_distances: Dict[str, int] = Field(
        ...,
        description="Hamming distances for each perceptual hash type (phash, ahash, dhash, whash)"
    )
    similarity_percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Computed visual similarity percentage (100% = identical perceptual layout)"
    )


class DuplicateCheckResult(BaseModel):
    """
    Schema for perceptual-hash duplicate detection check.
    """
    matches: List[DuplicateMatch] = Field(
        default_factory=list,
        description="Top matching reference images within the distance threshold"
    )
    best_match_similarity: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Highest visual similarity percentage among matches (0.0 if no match)"
    )
    is_near_duplicate: bool = Field(
        default=False,
        description="Whether the image is considered a near-duplicate of an existing known reference"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Recycled/duplicate media risk score (0.5 neutral, 0.8+ recycled match)"
    )
    note: Optional[str] = Field(
        default=None,
        description="Contextual note on near-duplicate detection and image recycling"
    )


class AIDetectorCheckResult(BaseModel):
    """
    Schema for deep learning pretrained AI-generated image classifier check.
    """
    model_name: str = Field(
        ...,
        description="Name or identifier of the pretrained Hugging Face vision model used"
    )
    ai_probability: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated statistical probability that the image was synthesized by AI (0.0 to 1.0)"
    )
    label: str = Field(
        ...,
        description="Classification category: 'likely_ai', 'uncertain', or 'likely_real'"
    )
    risk_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Estimated manipulation risk score (aligned with ai_probability)"
    )
    available: bool = Field(
        default=True,
        description="Whether the underlying neural model was loaded and functional"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error detail if inference or model loading failed"
    )
    note: Optional[str] = Field(
        default=None,
        description="Methodological limitations and interpretation guidance"
    )


class CheckResults(BaseModel):
    """
    Container for all individual check results.
    Maintains backward compatibility across all phases.
    """
    model_config = ConfigDict(extra="allow")

    metadata: MetadataCheckResult
    ela: ELACheckResult
    c2pa: Optional[C2PACheckResult] = None
    duplicate: Optional[DuplicateCheckResult] = None
    ai_detector: Optional[AIDetectorCheckResult] = None


class VerdictEvidenceItem(BaseModel):
    """Evidence line item in the synthesized verdict."""
    check: str = Field(..., description="Name of the forensic check evaluated")
    status: str = Field(
        ...,
        description="Qualitative assessment status: 'suspicious', 'neutral', 'clean', or 'unavailable'"
    )
    score: Optional[float] = Field(
        default=None,
        description="Numeric risk score associated with this check (None if unavailable)"
    )
    summary: str = Field(..., description="One-line plain-English summary of findings")


class VerdictResponse(BaseModel):
    """Synthesized forensic verdict combining all available checks."""
    label: str = Field(
        ...,
        description="Categorical verdict: 'likely_ai_generated', 'possibly_manipulated', 'likely_authentic', or 'inconclusive'"
    )
    display_label: str = Field(..., description="Human-friendly label (e.g. 'Likely AI-generated')")
    overall_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Synthesized suspension score from 0.0 (authentic) to 1.0 (manipulated/synthetic)"
    )
    confidence: str = Field(
        ...,
        description="Confidence level in the assessment: 'low', 'medium', or 'high'"
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Bullet-point list of plain-English arguments supporting the verdict"
    )
    evidence: List[VerdictEvidenceItem] = Field(
        default_factory=list,
        description="Evidence ledger across all checked forensic vectors"
    )


class ImageDimensions(BaseModel):
    """Dimensions of the analyzed image in pixels."""
    width: int = Field(..., description="Image width in pixels")
    height: int = Field(..., description="Image height in pixels")


class AnalysisResponse(BaseModel):
    """
    Top-level response payload for POST /analyze.
    """
    filename: str = Field(..., description="Original filename of the analyzed image")
    image_dimensions: Optional[ImageDimensions] = Field(
        default=None,
        description="Image pixel dimensions (width x height)"
    )
    image_format: Optional[str] = Field(
        default=None,
        description="Image encoding format (e.g. JPEG, PNG, WEBP)"
    )
    checks: Dict[str, Any] = Field(
        ...,
        description="Map of check name to corresponding check analysis results"
    )
    verdict: Optional[VerdictResponse] = Field(
        default=None,
        description="Synthesized multi-check forensic verdict (Phase 4)"
    )
    processing_time_ms: Optional[float] = Field(
        default=None,
        description="Total server-side analysis processing duration in milliseconds"
    )


class ReferenceAddResponse(BaseModel):
    """Response schema for POST /reference/add."""
    id: int = Field(..., description="Auto-incremented ID assigned to the reference")
    label: str = Field(..., description="Label attached to the reference image")
    status: str = Field(default="added", description="Status confirmation")


class ReferenceItem(BaseModel):
    """Summary item of a stored reference image (excludes raw image binary)."""
    id: int = Field(..., description="Reference ID")
    label: str = Field(..., description="Label name")
    created_at: str = Field(..., description="Timestamp of when reference was indexed")


class ReferenceListResponse(BaseModel):
    """Response schema for GET /reference/list."""
    references: List[ReferenceItem] = Field(..., description="List of all stored references")
    count: int = Field(..., description="Total count of reference images")
