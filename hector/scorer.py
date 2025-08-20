from typing import Any, Dict, Optional


def _get(repo: Any, attr: str, default: float = 0.0) -> float:
    try:
        return float(getattr(repo, attr))
    except Exception:
        return float(default)


def _license_id(repo: Any) -> str:
    try:
        lic = getattr(repo, "license", None)
        if lic and getattr(lic, "spdx_id", None):
            return lic.spdx_id  # type: ignore[attr-defined]
    except Exception:
        pass
    return "none"


def score_repository(repo: Any, weights: Dict[str, Any], metrics: Optional[Dict[str, Any]] = None) -> float:
    """Compute a score for a repository based on weights config."""
    stars_w = float(weights.get("stars", 0))
    forks_w = float(weights.get("forks", 0))
    issues_w = float(weights.get("open_issues", 0))
    prs_w = float(weights.get("prs", 0))
    disc_w = float(weights.get("discussions", 0))
    contrib_w = float(weights.get("contributors", 0))
    recency_w = float(weights.get("recency_decay", 0))

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

    lic_map = weights.get("license", {}) or {}
    bonus = float(lic_map.get(_license_id(repo), lic_map.get("none", 0)))

    return float(base + bonus)
