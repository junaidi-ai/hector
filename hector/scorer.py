import re
from typing import Any

# Healthcare context anchors for relevance boost (Task 8)
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


def _get(repo: Any, attr: str, default: float = 0.0) -> float:
    try:
        return float(getattr(repo, attr))
    except Exception:
        return float(default)


def _normalize(text: str) -> str:
    """Lowercase and normalize text for matching."""
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_healthcare_relevant(text: str) -> bool:
    """Check if text contains healthcare domain anchors (Task 8)."""
    normalized = _normalize(text)
    for anchor in _HEALTHCARE_ANCHORS:
        # Short anchors (<=4 chars) need word boundaries
        if len(anchor) <= 4:
            pattern = r"(?:^|\b)" + re.escape(anchor) + r"(?:\b|$)"
            if re.search(pattern, normalized):
                return True
        else:
            if anchor in normalized:
                return True
    return False


def _license_id(repo: Any) -> str:
    try:
        lic = getattr(repo, "license", None)
        if lic and getattr(lic, "spdx_id", None):
            return lic.spdx_id  # type: ignore[attr-defined]
    except Exception:
        pass
    return "none"


def score_repository(
    repo: Any, weights: dict[str, Any], metrics: dict[str, Any] | None = None
) -> float:
    """Compute a score for a repository based on weights config.

    Includes optional healthcare domain relevance boost (Task 8).
    """
    stars_w = float(weights.get("stars", 0))
    forks_w = float(weights.get("forks", 0))
    issues_w = float(weights.get("open_issues", 0))
    prs_w = float(weights.get("prs", 0))
    disc_w = float(weights.get("discussions", 0))
    contrib_w = float(weights.get("contributors", 0))
    recency_w = float(weights.get("recency_decay", 0))
    health_relevance_w = float(weights.get("health_relevance_boost", 0))

    stars = _get(repo, "stargazers_count", 0)
    forks = _get(repo, "forks_count", 0)
    open_issues = _get(repo, "open_issues_count", 0)

    # Use provided metrics if available
    prs = 0.0
    discussions = 0.0
    contributors = 0.0
    recency_term = 0.0
    if metrics:
        prs = float(metrics.get("prs_open", 0) or 0)
        discussions = 1.0 if bool(metrics.get("has_discussions", False)) else 0.0
        contributors = float(metrics.get("contributors_count", 0) or 0)
        days_since_push = metrics.get("days_since_push")
        if days_since_push is not None:
            # Negative contribution increases with staleness; approx per month
            recency_term = -float(days_since_push) / 30.0

    base = (
        stars * stars_w
        + forks * forks_w
        + open_issues * issues_w
        + prs * prs_w
        + discussions * disc_w
        + contributors * contrib_w
        + recency_term * recency_w
    )

    # Healthcare relevance boost (Task 8)
    health_relevance_boost = 0.0
    if health_relevance_w > 0:
        name = getattr(repo, "full_name", getattr(repo, "name", "")) or ""
        description = getattr(repo, "description", "") or ""
        combined_text = f"{name} {description}"
        if _is_healthcare_relevant(combined_text):
            health_relevance_boost = health_relevance_w

    lic_map = weights.get("license", {}) or {}
    bonus = float(lic_map.get(_license_id(repo), lic_map.get("none", 0)))

    return float(base + bonus + health_relevance_boost)
