import os
from datetime import datetime, timezone
from typing import Any, Dict, List
import logging

try:  # Optional dependency guard for dry-run mode
    from github import Github
except Exception:  # pragma: no cover - import-time guard
    Github = None  # type: ignore


def _build_query(search_cfg: Dict[str, Any]) -> str:
    q = (search_cfg.get("query") or "").strip()
    topics = [str(t).strip() for t in (search_cfg.get("topics") or []) if str(t).strip()]
    if topics:
        # Use OR to broaden matches across topics instead of requiring all of them
        topics_clause = " OR ".join([f"topic:{t}" for t in topics])
        q = f"{q} ({topics_clause})".strip()
    logging.getLogger("hector").debug("GitHub search query: %s", q)
    return q.strip()


def _fetch_pagewise(results, remaining: int) -> List[Any]:
    repos: List[Any] = []
    page = 0
    while remaining > 0:
        try:
            page_items = results.get_page(page)
        except Exception:
            break
        if not page_items:
            break
        for r in page_items:
            repos.append(r)
            remaining -= 1
            if remaining <= 0:
                break
        page += 1
    return repos

def search_repositories(cfg: Dict[str, Any], limit: int = 50):
    """Search GitHub repositories using the provided config with pagination.

    Returns a list of PyGithub Repository objects. If in dry_run mode or no token,
    returns an empty list.
    """
    dry = bool(cfg.get("dry_run", False))
    token = cfg.get("auth", {}).get("GITHUB_TOKEN") or os.getenv("GITHUB_TOKEN")

    if dry or not token:
        return []

    if Github is None:
        raise ImportError("PyGithub is required for live scans. Install with 'pip install PyGithub'.")

    gh = Github(token, per_page=50)
    search_cfg = cfg.get("search", {})
    base_q = _build_query(search_cfg)
    languages = search_cfg.get("languages") or []

    remaining = max(1, int(limit))
    all_repos: List[Any] = []
    seen_ids = set()

    if languages:
        for lang in languages:
            if remaining <= 0:
                break
            lang = str(lang).strip()
            if not lang:
                continue
            q = f"{base_q} language:{lang}".strip()
            logging.getLogger("hector").debug("GitHub search (lang=%s): %s", lang, q)
            results = gh.search_repositories(q)
            fetched = _fetch_pagewise(results, remaining)
            for r in fetched:
                rid = getattr(r, "id", None) or getattr(r, "full_name", None)
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                all_repos.append(r)
                remaining -= 1
                if remaining <= 0:
                    break
    else:
        logging.getLogger("hector").debug("GitHub search (single): %s", base_q)
        results = gh.search_repositories(base_q)
        fetched = _fetch_pagewise(results, remaining)
        all_repos.extend(fetched)

    return all_repos


def get_repo_metrics(repo: Any) -> Dict[str, Any]:
    """Collect richer metrics for a repository, best-effort and lightweight.

    Returns keys: prs_open, has_discussions, contributors_count, days_since_push
    """
    metrics: Dict[str, Any] = {
        "prs_open": 0,
        "has_discussions": False,
        "contributors_count": 0,
        "days_since_push": None,
    }

    # PRs open (best-effort; avoid expensive full iteration)
    try:
        pulls = repo.get_pulls(state="open")
        # totalCount may not always be available; fallback to first page length
        count = getattr(pulls, "totalCount", None)
        if count is None:
            try:
                count = len(pulls.get_page(0))
            except Exception:
                count = 0
        metrics["prs_open"] = int(count or 0)
    except Exception:
        pass

    # Discussions flag (count typically not available via REST)
    try:
        metrics["has_discussions"] = bool(getattr(repo, "has_discussions", False))
    except Exception:
        pass

    # Contributors count (soft cap to avoid heavy calls)
    try:
        contribs = repo.get_contributors()
        # Try to quickly count up to a cap
        cap = 100
        c = 0
        first_page = []
        try:
            first_page = contribs.get_page(0)
        except Exception:
            first_page = []
        c += len(first_page)
        metrics["contributors_count"] = int(c)
    except Exception:
        pass

    # Recency (days since last push)
    try:
        pushed_at = getattr(repo, "pushed_at", None)
        if pushed_at:
            now = datetime.now(timezone.utc)
            delta = now - pushed_at
            metrics["days_since_push"] = int(delta.days)
    except Exception:
        pass

    return metrics
