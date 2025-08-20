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
