from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from hector.scanner import get_repo_metrics


class _Pulls:
    def __init__(self, count=3):
        self._count = count
        self.totalCount = count

    def get_page(self, i):
        return [object()] * self._count if i == 0 else []


class _Contribs:
    def __init__(self, count=5):
        self._count = count

    def get_page(self, i):
        return [object()] * self._count if i == 0 else []


class _Repo:
    def __init__(self):
        self.has_discussions = True
        self.pushed_at = datetime.now(timezone.utc) - timedelta(days=7)

    def get_pulls(self, state="open"):
        return _Pulls(4)

    def get_contributors(self):
        return _Contribs(6)


def test_get_repo_metrics_mocked():
    repo = _Repo()
    m = get_repo_metrics(repo)
    assert m["prs_open"] == 4
    assert m["has_discussions"] is True
    assert m["contributors_count"] == 6
    assert isinstance(m["days_since_push"], int) and m["days_since_push"] >= 7
