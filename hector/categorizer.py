import re
from collections.abc import Iterable


def _normalize(text: str) -> str:
    """Lowercase, replace connectors, strip punctuation, and compress whitespace."""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _phrase_in_text(phrase: str, text: str) -> bool:
    """Check if a phrase exists with word boundaries (allowing whitespace variations)."""
    p = _normalize(phrase)
    if not p:
        return False
    # For short acronyms or tokens without spaces (e.g., nlp, hl7, fhir, dicom),
    # allow relaxed substring match to catch cases like "smartonfhir" or "mednlp".
    # Minimum length: 3 characters (excludes 2-letter tokens like "ct", "ai")
    if " " not in p and 3 <= len(p) <= 4:
        return p in text
    # For single tokens shorter than 3 chars or longer than 4 chars, use word boundaries
    if " " not in p and (len(p) < 3 or len(p) > 4):
        pattern = r"(?:^|\b)" + re.escape(p) + r"(?:\b|$)"
        return re.search(pattern, text) is not None
    # Allow multi-word phrases; respect word boundaries around the whole phrase
    pattern = r"(?:^|\b)" + re.escape(p).replace(r"\ ", r"\s+") + r"(?:\b|$)"
    return re.search(pattern, text) is not None


# Sensible default synonyms to greatly reduce "Uncategorized" cases.
# Users can extend/override these via config (see categorize_repository keywords param).
DEFAULT_KEYWORDS: dict[str, list[str]] = {
    "AI Diagnostics": [
        "diagnostic",
        "diagnosis",
        "triage",
        "decision support",
        "cds",
        "cad",
    ],
    "Telemedicine": [
        "telemedicine",
        "telehealth",
        "virtual care",
        "telemed",
        "remote consult",
    ],
    "EHR & Clinical Systems": [
        "ehr",
        "emr",
        "electronic health record",
        "electronic medical record",
        "clinical system",
        "clinical workflow",
    ],
    "Imaging & Radiology": [
        "radiology",
        "medical imaging",
        "clinical imaging",
        "dicom",
        "pacs",
        "ct scan",
        "computed tomography",
        "mri",
        "xray",
        "x-ray",
        "ultrasound",
    ],
    "Wearables & Remote Monitoring": [
        "wearable",
        "wearables",
        "remote monitoring",
        "rpm",
        "smartwatch",
        "fitness tracker",
    ],
    "Public Health & Epidemiology": [
        "public health",
        "epidemiology",
        "surveillance",
        "outbreak",
    ],
    "Genomics & Precision Medicine": [
        "genomic",
        "genomics",
        "precision medicine",
        "vcf",
        "variant",
        "bioinformatics",
    ],
    "Mental Health": [
        "mental health",
        "psychiatry",
        "psychology",
        "therapy",
        "depression",
        "anxiety",
    ],
    "Scheduling & Patient Portals": [
        "scheduling",
        "appointment",
        "booking",
        "patient portal",
        "portal",
    ],
    "NLP & Clinical Text": [
        "clinical nlp",
        "medical nlp",
        "clinical text mining",
        "natural language",
        "clinical text",
        "de-identification",
        "deidentification",
        "ner",
        "clinical notes",
    ],
    "FHIR & Interoperability": [
        "fhir",
        "hl7",
        "interoperability",
        "ccd",
        "ccda",
        "smart on fhir",
        "smart-on-fhir",
    ],
    "Data Platforms & ETL": [
        "etl",
        "extract transform load",
        "data platform",
        "data pipeline",
        "warehouse",
        "lakehouse",
    ],
}


# Negative-context indicators: if present, repo should be Uncategorized regardless of keyword matches
_NON_HEALTHCARE_INDICATORS: list[str] = [
    "ros2",
    "ros",
    "robot",
    "robotics",
    "autonomous driving",
    "drone",
    "navigation stack",
]

# Strict healthcare context keywords for the AI fallback gate (Task 1)
_HEALTHCARE_ANCHORS: list[str] = [
    "health",
    "medical",
    "clinical",
    "patient",
    "hospital",
    "diagnostic",
    "therapeutic",
    "pharma",
    "biomedical",
    "healthcare",
    "medicine",
    "physician",
    "nurse",
    "care",
]


def _is_healthcare_relevant(text: str) -> bool:
    """Check if text contains healthcare domain anchors (strict allowlist)."""
    normalized = _normalize(text)
    for anchor in _HEALTHCARE_ANCHORS:
        # Short anchors (<=4 chars) need word boundaries to avoid false positives
        # e.g., "care" should not match "scare" or "childcare"
        if len(anchor) <= 4:
            pattern = r"(?:^|\b)" + re.escape(anchor) + r"(?:\b|$)"
            if re.search(pattern, normalized):
                return True
        else:
            if anchor in normalized:
                return True
    return False


def _has_non_healthcare_context(text: str) -> bool:
    """Check if text contains non-healthcare indicators (robotics, autonomous systems, etc.)."""
    normalized = _normalize(text)
    for ind in _NON_HEALTHCARE_INDICATORS:
        # Use word boundaries for single-word indicators (ros, robot, drone)
        # Multi-word indicators (ros2, autonomous driving, navigation stack) are exact matches
        if " " in ind or len(ind) > 5:  # multi-word or long exact matches
            if ind in normalized:
                return True
        else:
            # Single short words need word boundaries to avoid "scare" matching "care"
            pattern = r"(?:^|\b)" + re.escape(ind) + r"(?:\b|$)"
            if re.search(pattern, normalized):
                return True
    return False


def categorize_repository(
    name: str,
    description: str,
    categories: Iterable[str],
    keywords: dict[str, list[str]] | None = None,
    require_health_context: bool = True,
) -> list[str]:
    """Assign categories using phrase and synonym matching in name/description.

    - Direct phrase match against the category name (case-insensitive, word-bounded)
    - Fallback to synonyms defined in DEFAULT_KEYWORDS and optional overrides from config
    - AI-related fallback only applies if healthcare context is detected
    - Returns empty list (Uncategorized) if non-healthcare indicators detected
    - Healthcare relevance pre-filter: if no health context, returns Uncategorized
    """
    text = _normalize(f"{name} {description}")

    # Healthcare relevance pre-filter (Task 3): skip categorization if no health context
    if require_health_context and not _is_healthcare_relevant(text):
        return []

    # Negative-context guard: skip categorization for robotics/autonomous systems
    if _has_non_healthcare_context(text):
        return []

    matched: list[str] = []

    # Merge default keywords with user-provided ones (extend existing where applicable)
    kw_map: dict[str, list[str]] = {k: list(v) for k, v in DEFAULT_KEYWORDS.items()}
    if keywords:
        for cat, kws in keywords.items():
            key = str(cat).strip()
            if not key:
                continue
            base = kw_map.get(key, [])
            # Keep only non-empty strings
            extra = [str(x).strip() for x in (kws or []) if str(x).strip()]
            kw_map[key] = list(dict.fromkeys(base + extra))  # dedupe, preserve order

    for cat in categories:
        norm_cat = str(cat).strip()
        if not norm_cat:
            continue
        # Direct phrase match to the category label
        if _phrase_in_text(norm_cat, text):
            matched.append(norm_cat)
            continue
        # Synonym/keyword matches
        for kw in kw_map.get(norm_cat, []):
            if _phrase_in_text(kw, text):
                matched.append(norm_cat)
                break

    # Fallback: if nothing matched but text is clearly AI-related AND has healthcare context,
    # map to AI Diagnostics. Without healthcare context, repos get "Uncategorized".
    if not matched and _is_healthcare_relevant(text):
        ai_indicators = [
            "ai",
            "artificial intelligence",
            "machine learning",
            "deep learning",
            "foundation model",
            "large language model",
            "llm",
            "vision-language model",
            "vlm",
            "multimodal",
            "multi-modal",
            "vqa",
            "retrieval augmented generation",
            "retrieval-augmented generation",
            "rag",
            "agent",
            "agentic",
            "transformer",
            "attention",
            "self-attention",
            "graph neural network",
            "gnn",
            "graph-based attention",
            "gat",
            "gcn",
            "graph attention network",
            "medical reasoning",
            "clinical decision support",
        ]
        if any(ind in text for ind in ai_indicators) and any(
            _normalize(str(c)) == _normalize("AI Diagnostics") for c in categories
        ):
            matched.append("AI Diagnostics")

    return matched
