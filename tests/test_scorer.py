from types import SimpleNamespace

from hector.scorer import score_repository


def make_repo(stars=10, forks=5, issues=2, license_spdx="MIT"):
    lic = SimpleNamespace(spdx_id=license_spdx) if license_spdx else None
    return SimpleNamespace(
        stargazers_count=stars,
        forks_count=forks,
        open_issues_count=issues,
        license=lic,
    )


def test_score_with_basic_weights():
    repo = make_repo(stars=100, forks=10, issues=5, license_spdx="Apache-2.0")
    weights = {
        "stars": 0.1,
        "forks": 0.2,
        "open_issues": -0.5,
        "license": {"Apache-2.0": 50, "none": -100},
    }
    score = score_repository(repo, weights)
    # base = 100*0.1 + 10*0.2 + 5*(-0.5) = 10 + 2 - 2.5 = 9.5; +50 license = 59.5
    assert abs(score - 59.5) < 1e-6


def test_score_with_metrics_contrib_and_recency():
    repo = make_repo(stars=0, forks=0, issues=0, license_spdx=None)
    weights = {
        "contributors": 1.0,
        "recency_decay": 2.0,
        "license": {"none": 0},
    }
    metrics = {"contributors_count": 10, "days_since_push": 30}
    score = score_repository(repo, weights, metrics)
    # contributors term: 10 * 1.0 = 10
    # recency term: (-30/30) * 2.0 = -2
    assert abs(score - 8.0) < 1e-6


# Task 11 — Comprehensive scorer tests


def test_score_all_zero_weights_with_license_bonus():
    """All-zero weights should result in license bonus only."""
    repo = make_repo(stars=1000, forks=500, issues=100, license_spdx="MIT")
    weights = {
        "stars": 0.0,
        "forks": 0.0,
        "open_issues": 0.0,
        "prs": 0.0,
        "discussions": 0.0,
        "contributors": 0.0,
        "recency_decay": 0.0,
        "license": {"MIT": 100, "none": 0},
    }
    score = score_repository(repo, weights)
    # With all weights 0, base = 0; license bonus = 100
    assert abs(score - 100.0) < 1e-6


def test_score_negative_open_issues_weight_reduces_score():
    """Negative open_issues weight should reduce score for repos with many issues."""
    repo = make_repo(stars=0, forks=0, issues=100, license_spdx=None)
    weights = {
        "open_issues": -0.5,
        "license": {"none": 0},
    }
    score = score_repository(repo, weights)
    # base = 100 * (-0.5) = -50
    assert score < 0
    assert abs(score - (-50.0)) < 1e-6


def test_score_recency_decay_on_old_repo():
    """Recency decay should penalize repos not updated recently (365-day-old repo)."""
    repo = make_repo(stars=0, forks=0, issues=0, license_spdx=None)
    weights = {
        "recency_decay": 1.0,
        "license": {"none": 0},
    }
    metrics = {"days_since_push": 365}
    score = score_repository(repo, weights, metrics)
    # recency_term: (-365/30) * 1.0 ≈ -12.17
    expected = -365 / 30
    assert abs(score - expected) < 0.01


def test_score_unknown_license_fallback_to_none():
    """Unknown license should fallback to 'none' key in license map."""
    repo = make_repo(stars=0, forks=0, issues=0, license_spdx="Unknown-License")
    weights = {
        "license": {"MIT": 100, "none": -50},
    }
    score = score_repository(repo, weights)
    # Unknown license → fallback to "none" → -50
    assert abs(score - (-50.0)) < 1e-6


def test_score_healthcare_relevance_boost():
    """Healthcare relevance boost should be applied for healthcare-domain repos."""
    repo = SimpleNamespace(
        full_name="healthtech/clinical-ai",
        description="AI for clinical decision support",
        stargazers_count=0,
        forks_count=0,
        open_issues_count=0,
        license=None,
    )
    weights = {
        "health_relevance_boost": 200.0,
        "license": {"none": 0},
    }
    score = score_repository(repo, weights)
    # Repo mentions "clinical" which is a healthcare anchor → boost applied
    assert score >= 200.0


def test_score_healthcare_relevance_no_boost_for_non_healthcare():
    """Healthcare relevance boost should NOT apply for non-healthcare repos."""
    repo = SimpleNamespace(
        full_name="awesome-robotics",
        description="Industrial robotics framework",
        stargazers_count=0,
        forks_count=0,
        open_issues_count=0,
        license=None,
    )
    weights = {
        "health_relevance_boost": 200.0,
        "license": {"none": 0},
    }
    score = score_repository(repo, weights)
    # Repo has no healthcare anchors → no boost
    assert score == 0.0


def test_score_with_discussions_and_prs_metrics():
    """Score should include PRs and discussions from metrics."""
    repo = make_repo(stars=0, forks=0, issues=0, license_spdx=None)
    weights = {
        "prs": 0.5,
        "discussions": 2.0,
        "license": {"none": 0},
    }
    metrics = {"prs_open": 5, "has_discussions": True}
    score = score_repository(repo, weights, metrics)
    # prs term: 5 * 0.5 = 2.5
    # discussions term: 1 * 2.0 = 2.0
    # total = 4.5
    assert abs(score - 4.5) < 1e-6


def test_score_missing_repo_attributes():
    """Score should handle repos with missing attributes gracefully."""
    repo = SimpleNamespace()  # Empty repo with no attributes
    weights = {"stars": 1.0, "license": {"none": 50}}
    score = score_repository(repo, weights)
    # Missing attributes default to 0; license defaults to "none" → 50
    assert score == 50.0
