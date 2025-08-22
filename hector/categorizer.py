from typing import Dict, Iterable, List, Optional
import re


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
    # Allow multi-word phrases; respect word boundaries around the whole phrase
    pattern = r"(?:^|\b)" + re.escape(p).replace(r"\ ", r"\s+") + r"(?:\b|$)"
    return re.search(pattern, text) is not None


# Sensible default synonyms to greatly reduce "Uncategorized" cases.
# Users can extend/override these via config (see categorize_repository keywords param).
DEFAULT_KEYWORDS: Dict[str, List[str]] = {
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
        "imaging",
        "dicom",
        "pacs",
        "ct",
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
        "nlp",
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


def categorize_repository(
    name: str,
    description: str,
    categories: Iterable[str],
    keywords: Optional[Dict[str, List[str]]] = None,
) -> List[str]:
    """Assign categories using phrase and synonym matching in name/description.

    - Direct phrase match against the category name (case-insensitive, word-bounded)
    - Fallback to synonyms defined in DEFAULT_KEYWORDS and optional overrides from config
    """
    text = _normalize(f"{name} {description}")
    matched: List[str] = []

    # Merge default keywords with user-provided ones (extend existing where applicable)
    kw_map: Dict[str, List[str]] = {k: list(v) for k, v in DEFAULT_KEYWORDS.items()}
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

    return matched
