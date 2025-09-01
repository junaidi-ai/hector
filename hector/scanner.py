import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import logging

try:  # Optional dependency guard for dry-run mode
    from github import Github
except Exception:  # pragma: no cover - import-time guard
    Github = None  # type: ignore


def _build_query(search_cfg: Dict[str, Any]) -> str:
    """Build the base search query with topics and common exclusions."""
    q = (search_cfg.get("query") or "").strip()
    topics = [str(t).strip() for t in (search_cfg.get("topics") or []) if str(t).strip()]
    if topics:
        # Use OR to broaden matches across topics instead of requiring all of them
        topics_clause = " OR ".join([f"topic:{t}" for t in topics])
        q = f"{q} ({topics_clause})".strip()

    # Exclusions
    if bool(search_cfg.get("exclude_forks", False)) and "fork:" not in q:
        q = f"{q} fork:false".strip()
    if bool(search_cfg.get("exclude_archived", False)) and "archived:" not in q:
        q = f"{q} archived:false".strip()

    logging.getLogger("hector").debug("GitHub base query: %s", q)
    return q.strip()


def _apply_date_bounds(q: str, use: Optional[str], search_cfg: Dict[str, Any]) -> str:
    """Append created:/pushed: qualifiers based on window settings."""
    now = datetime.utcnow()
    if use == "pushed_within_days":
        days = int(search_cfg.get("pushed_within_days", 0) or 0)
        if days > 0:
            since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            q = f"{q} pushed:>={since}"
    elif use == "created_within_days":
        days = int(search_cfg.get("created_within_days", 0) or 0)
        if days > 0:
            since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
            q = f"{q} created:>={since}"
    return q


def _iter_strategies(search_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Yield effective search strategies. Backward compatible.

    If search_cfg["strategies"] exists, use it. Otherwise, synthesize a single
    strategy from top-level sort/order/use settings.
    """
    strategies = search_cfg.get("strategies") or []
    if strategies:
        # Normalize each entry with defaults from top-level
        norm: List[Dict[str, Any]] = []
        for s in strategies:
            s = dict(s or {})
            s.setdefault("sort", search_cfg.get("sort"))
            s.setdefault("order", search_cfg.get("order"))
            norm.append(s)
        return norm

    # Fallback single strategy
    return [
        {
            "name": "default",
            "sort": search_cfg.get("sort"),
            "order": search_cfg.get("order"),
            # If either window is set, prefer pushed window unless explicitly specified
            "use": (
                "pushed_within_days"
                if int(search_cfg.get("pushed_within_days", 0) or 0) > 0
                else ("created_within_days" if int(search_cfg.get("created_within_days", 0) or 0) > 0 else None)
            ),
            "query_extra": search_cfg.get("query_extra", ""),
        }
    ]


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
    orgs = [str(x).strip() for x in (search_cfg.get("orgs") or []) if str(x).strip()]
    users = [str(x).strip() for x in (search_cfg.get("users") or []) if str(x).strip()]
    topics: List[str] = [str(t).strip() for t in (search_cfg.get("topics") or []) if str(t).strip()]
    # Build a base query that excludes topics to enable per-topic batching when needed
    search_cfg_no_topics = dict(search_cfg)
    if "topics" in search_cfg_no_topics:
        search_cfg_no_topics["topics"] = []
    base_q_no_topics = _build_query(search_cfg_no_topics)

    remaining = max(1, int(limit))
    all_repos: List[Any] = []
    seen_ids = set()
    log = logging.getLogger("hector")

    def _add_repo(r: Any) -> bool:
        nonlocal remaining
        rid = getattr(r, "id", None) or getattr(r, "full_name", None)
        if rid in seen_ids:
            return False
        seen_ids.add(rid)
        all_repos.append(r)
        remaining -= 1
        return remaining > 0

    # 1) Multi-strategy search (with topic batching to avoid overly long queries)
    for strat in _iter_strategies(search_cfg):
        if remaining <= 0:
            break
        sort = strat.get("sort") or None
        order = strat.get("order") or None
        q = base_q
        q_extra = (strat.get("query_extra") or "").strip()
        if q_extra:
            q = f"{q} {q_extra}".strip()
        q = _apply_date_bounds(q, strat.get("use"), search_cfg)

        # Decide whether to batch topics
        use_topic_batching = len(topics) > 8  # threshold to avoid long OR clauses
        topic_iter: List[List[str]]
        if use_topic_batching and topics:
            # Per-topic batches (size=1) to keep queries small and robust
            topic_iter = [[t] for t in topics]
        else:
            # Single batch containing all topics (handled by _build_query already)
            topic_iter = [topics] if topics else [[]]

        for t_batch in topic_iter:
            if remaining <= 0:
                break
            if t_batch:
                # Build query without the giant OR clause, and add a small topic batch
                topics_clause = " OR ".join([f"topic:{t}" for t in t_batch])
                q_effective = f"{base_q_no_topics} ({topics_clause}) {q_extra}".strip()
                q_effective = _apply_date_bounds(q_effective, strat.get("use"), search_cfg)
            else:
                q_effective = q

            if languages:
                for lang in languages:
                    if remaining <= 0:
                        break
                    lang = str(lang).strip()
                    if not lang:
                        continue
                    q_lang = f"{q_effective} language:{lang}".strip()
                    log.debug(
                        "GitHub search (strategy=%s, topics=%s, lang=%s): %s",
                        strat.get("name", "default"),
                        ",".join(t_batch) if t_batch else "-",
                        lang,
                        q_lang,
                    )
                    try:
                        results = gh.search_repositories(q_lang, sort=sort, order=order)
                    except Exception as e:
                        log.info("Search failed (lang batch). strategy=%s topics=%s error=%s", strat.get("name", "default"), ",".join(t_batch) if t_batch else "-", e)
                        continue
                    for r in _fetch_pagewise(results, remaining):
                        if not _add_repo(r):
                            break
            else:
                log.debug(
                    "GitHub search (strategy=%s, topics=%s): %s",
                    strat.get("name", "default"),
                    ",".join(t_batch) if t_batch else "-",
                    q_effective,
                )
                try:
                    results = gh.search_repositories(q_effective, sort=sort, order=order)
                except Exception as e:
                    log.info("Search failed (no-lang). strategy=%s topics=%s error=%s", strat.get("name", "default"), ",".join(t_batch) if t_batch else "-", e)
                    results = None
                if results is not None:
                    for r in _fetch_pagewise(results, remaining):
                        if not _add_repo(r):
                            break

    # 2) Explicit orgs/users enumeration (best-effort)
    def _iter_repos_from_org(org_name: str):
        try:
            org = gh.get_organization(org_name)
            return org.get_repos(type="public")
        except Exception:
            return []

    def _iter_repos_from_user(user_name: str):
        try:
            usr = gh.get_user(user_name)
            return usr.get_repos(type="public")
        except Exception:
            return []

    for org in orgs:
        if remaining <= 0:
            break
        log.debug("Enumerating org repos: %s", org)
        repos_iter = _iter_repos_from_org(org)
        try:
            page = 0
            while remaining > 0:
                page_items = repos_iter.get_page(page) if hasattr(repos_iter, "get_page") else []
                if not page_items:
                    break
                for r in page_items:
                    if not _add_repo(r):
                        break
                page += 1
        except Exception:
            continue

    for user in users:
        if remaining <= 0:
            break
        log.debug("Enumerating user repos: %s", user)
        repos_iter = _iter_repos_from_user(user)
        try:
            page = 0
            while remaining > 0:
                page_items = repos_iter.get_page(page) if hasattr(repos_iter, "get_page") else []
                if not page_items:
                    break
                for r in page_items:
                    if not _add_repo(r):
                        break
                page += 1
        except Exception:
            continue

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
