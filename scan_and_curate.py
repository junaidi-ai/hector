#!/usr/bin/env python3
import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime

from hector import scanner
from hector.categorizer import categorize_repository
from hector.config import load_config
from hector.renderer import render_markdown
from hector.scorer import score_repository


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hector HealthTech Tools Scanner")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    p.add_argument("--limit", type=int, default=50, help="Max repositories to process")

    mode_group = p.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Skip GitHub API: use fixture data, run categorization/scoring, write output",
    )
    mode_group.add_argument(
        "--categories-only",
        dest="categories_only",
        metavar="PATH",
        help="Re-categorize repos from existing markdown file (e.g., result/healthtech-tools.md)",
    )
    mode_group.add_argument(
        "--live",
        dest="dry_run",
        action="store_false",
        help="Run live with GitHub API (default)",
    )
    p.set_defaults(dry_run=None, categories_only=None)

    p.add_argument("--output", help="Override output markdown file path")
    p.add_argument(
        "--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    return p.parse_args(argv)


def setup_logging(level: str) -> None:
    level_num = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level_num,
        format="%(asctime)s hector %(levelname)s %(message)s",
    )


def _resolve_output_paths(cfg: dict, cli_output: str | None) -> tuple[str, str | None]:
    """Resolve the output markdown path and optional 'latest' path.

    Supports {date} placeholder in config's output.file. If cli_output is provided,
    it takes precedence (no templating), but we still honor output.latest if present.
    """
    out_cfg = cfg.get("output", {})
    latest_path = out_cfg.get("latest")

    if cli_output:
        return cli_output, latest_path

    file_tmpl = out_cfg.get("file", "healthtech-tools.md")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    out_file = str(file_tmpl).replace("{date}", today)
    return out_file, latest_path


def _load_fixture_repos(fixture_path: str = "tests/fixtures/sample-repos.json") -> list:
    """Load sample repository data from a JSON fixture file for dry-run mode.

    Args:
        fixture_path: Path to JSON fixture file with repo data

    Returns:
        List of repo-like objects (SimpleNamespace) with required attributes
    """
    from types import SimpleNamespace

    if not os.path.exists(fixture_path):
        # Return empty list if fixture doesn't exist (user can create one)
        return []

    try:
        with open(fixture_path) as f:
            repos_data = json.load(f)
        # Convert dicts to SimpleNamespace objects
        repos = []
        for repo_data in repos_data:
            # Reconstruct license object if present
            if "license" in repo_data and repo_data["license"]:
                repo_data["license"] = SimpleNamespace(**repo_data["license"])
            repos.append(SimpleNamespace(**repo_data))
        return repos
    except Exception as e:
        raise ValueError(f"Failed to load fixture from {fixture_path}: {e}") from e


def _load_repos_from_markdown(md_path: str) -> list[dict]:
    """Parse repositories from an existing curated markdown file.

    Extracts repo information from markdown format like:
    - **[repo-name](https://github.com/user/repo)** (Score: 85)
      - License: MIT | Stars: 1.2k | Forks: 300
      - Description: ...

    Args:
        md_path: Path to markdown file

    Returns:
        List of repo dicts with name, url, description, license, stars, forks
    """
    import re

    if not os.path.exists(md_path):
        raise FileNotFoundError(f"Markdown file not found: {md_path}")

    repos: list[dict] = []
    with open(md_path) as f:
        content = f.read()

    # Pattern: - **[name](url)** (Score: number)
    pattern = r"-\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*\s+\(Score:\s*([\d.]+)\)"
    for match in re.finditer(pattern, content):
        repo_name = match.group(1)
        repo_url = match.group(2)
        # Extract owner/repo from GitHub URL
        if "github.com" in repo_url:
            parts = repo_url.rstrip("/").split("/")
            if len(parts) >= 2:
                full_name = f"{parts[-2]}/{parts[-1]}"
            else:
                full_name = repo_name
        else:
            full_name = repo_name

        repos.append(
            {
                "name": repo_name,
                "full_name": full_name,
                "url": repo_url,
                "score": float(match.group(3)),
                "description": "",  # Not extracted from markdown for simplicity
                "categories": [],
                "license": "none",
                "stars": 0,
                "forks": 0,
            }
        )

    return repos


def _write_run_summary(summary_path: str, stats: dict, items: list, log: logging.Logger) -> None:
    """Write a run summary JSON file with pipeline statistics.

    Args:
        summary_path: Path to write result/run-summary.json
        stats: Dictionary with pipeline statistics
        items: List of final curated items
        log: Logger instance
    """
    # Count categories
    category_counts: dict[str, int] = {}
    uncategorized_count = 0
    for item in items:
        cats = item.get("categories", ["Uncategorized"])  # type: ignore[union-attr]
        if not cats or (len(cats) == 1 and cats[0] == "Uncategorized"):
            uncategorized_count += 1
        else:
            for cat in cats:
                category_counts[cat] = category_counts.get(cat, 0) + 1

    stats_dict: dict = {
        "total_scanned": int(stats.get("total_scanned", 0)),
        "after_min_stars": int(stats.get("after_min_stars", 0)),
        "after_relevance_filter": int(stats.get("after_relevance_filter", 0)),
        "after_score_filter": int(stats.get("after_score_filter", 0)),
        "min_score_threshold": float(stats.get("min_score", 0)),
    }

    summary: dict = {
        "timestamp": datetime.utcnow().isoformat(),
        "stats": stats_dict,
        "categories": category_counts,
        "uncategorized_count": uncategorized_count,
        "total_in_output": len(items),
    }

    # Ensure output directory exists
    summary_dir = os.path.dirname(summary_path)
    if summary_dir:
        os.makedirs(summary_dir, exist_ok=True)

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Log the summary
    log.info("Run Summary (written to %s):", summary_path)
    log.info("  Total scanned: %d", stats_dict["total_scanned"])
    log.info("  After min_stars filter: %d", stats_dict["after_min_stars"])
    log.info("  After relevance filter: %d", stats_dict["after_relevance_filter"])
    log.info(
        "  After score filter (min=%.1f): %d",
        stats_dict["min_score_threshold"],
        stats_dict["after_score_filter"],
    )
    log.info("  Uncategorized: %d", uncategorized_count)
    if category_counts:
        log.info("  Categories:")
        for cat in sorted(category_counts.keys()):
            log.info("    %s: %d", cat, category_counts[cat])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    setup_logging(args.log_level)
    log = logging.getLogger("hector")

    cfg = load_config(args.config)

    # Optional overrides from CLI
    if args.dry_run is not None:
        cfg["dry_run"] = bool(args.dry_run)
    if args.output:
        cfg.setdefault("output", {})["file"] = args.output

    # Handle --categories-only mode (Task 13): re-categorize existing markdown
    if args.categories_only:
        log.info("Categories-only mode: re-categorizing repos from %s", args.categories_only)
        try:
            repos_data = _load_repos_from_markdown(args.categories_only)
            if not repos_data:
                log.warning("No repositories found in %s", args.categories_only)
                return 0

            log.info("Loaded %d repos from %s", len(repos_data), args.categories_only)

            # Re-categorize without re-scoring (no need to fetch weights for categories-only)
            cat_categories: list[str] = cfg.get("output", {}).get("categories", [])
            cat_kw: dict = cfg.get("category_keywords") or cfg.get("output", {}).get(
                "category_keywords", {}
            )
            cat_require_health: bool = cfg.get("categorizer", {}).get(
                "require_health_context", True
            )

            items = []
            for repo_info in repos_data:
                cats = categorize_repository(
                    repo_info["full_name"],
                    repo_info.get("description", ""),
                    cat_categories,
                    cat_kw,
                    cat_require_health,
                )
                repo_info["categories"] = cats or ["Uncategorized"]
                items.append(repo_info)

            log.info("Re-categorized %d repos", len(items))

            output_file, latest_file = _resolve_output_paths(cfg, args.output)
            if latest_file:
                render_markdown(items, latest_file, cat_categories)
                log.info("Updated canonical index at %s", latest_file)

            log.info("Done.")
            return 0
        except Exception as e:
            log.error("Failed to process categories-only mode: %s", e)
            return 1

    # Handle --dry-run mode (Task 13): use fixture data instead of GitHub API
    if args.dry_run:
        log.info("Dry-run mode: using fixture data instead of GitHub API")
        try:
            repos = _load_fixture_repos()
            if not repos:
                log.info("No fixture data found at tests/fixtures/sample-repos.json")
                log.info(
                    "Dry-run: configuration validated. Create fixture file to test categorization."
                )
                return 0
            log.info("Loaded %d repos from fixture", len(repos))
        except Exception as e:
            log.error("Failed to load fixture: %s", e)
            return 1
    else:
        limit = int(args.limit)
        log.info("Searching repositories... limit=%s", limit)
        repos = scanner.search_repositories(cfg, limit=limit)

    # Track statistics for run summary (Task 12)
    stats: dict = {"total_scanned": len(repos)}

    # Apply min_stars filter
    min_stars = int(cfg.get("search", {}).get("min_stars", 0) or 0)
    if min_stars > 0:
        original_count = len(repos)
        repos = [r for r in repos if int(getattr(r, "stargazers_count", 0) or 0) >= min_stars]
        filtered_count = original_count - len(repos)
        log.info(
            "Applied min_stars=%d filter: %d repos → %d repos (filtered %d)",
            min_stars,
            original_count,
            len(repos),
            filtered_count,
        )
    stats["after_min_stars"] = len(repos)

    # Apply healthcare relevance post-scan filter (Task 5)
    apply_relevance_filter = cfg.get("search", {}).get("relevance_filter", True)
    if apply_relevance_filter and repos:
        original_count = len(repos)
        repos = [r for r in repos if scanner.is_repo_healthcare_relevant(r)]
        filtered_count = original_count - len(repos)
        if filtered_count > 0:
            log.info(
                "Applied healthcare relevance filter: %d repos → %d repos (filtered %d)",
                original_count,
                len(repos),
                filtered_count,
            )
    stats["after_relevance_filter"] = len(repos)

    weights: dict = cfg.get("weights", {})
    cats_config: list[str] = cfg.get("output", {}).get("categories", [])
    cat_keywords: dict = cfg.get("category_keywords") or cfg.get("output", {}).get(
        "category_keywords", {}
    )
    require_health_context: bool = cfg.get("categorizer", {}).get("require_health_context", True)

    items = []
    for r in repos:
        try:
            name = getattr(r, "full_name", getattr(r, "name", "unknown"))
            url = getattr(r, "html_url", "")
            desc = getattr(r, "description", "") or ""
            # Best-effort: include repo topics to improve categorization recall
            repo_topics: list[str] = []
            try:
                get_topics = getattr(r, "get_topics", None)
                if callable(get_topics):
                    repo_topics = get_topics() or []
            except Exception:
                repo_topics = []
            desc_for_cat = (desc + " " + " ".join(repo_topics)).strip()
            metrics = scanner.get_repo_metrics(r)
            score = score_repository(r, weights, metrics)
            cats = categorize_repository(
                name, desc_for_cat, cats_config, cat_keywords, require_health_context
            )
            lic = getattr(getattr(r, "license", None), "spdx_id", None) or "none"
            stars = int(getattr(r, "stargazers_count", 0) or 0)
            forks = int(getattr(r, "forks_count", 0) or 0)
            items.append(
                {
                    "name": name,
                    "url": url,
                    "score": score,
                    "description": desc,
                    "categories": cats or ["Uncategorized"],
                    "license": lic,
                    "stars": stars,
                    "forks": forks,
                    # extra metrics for renderer
                    "prs_open": metrics.get("prs_open"),
                    "has_discussions": metrics.get("has_discussions"),
                    "contributors_count": metrics.get("contributors_count"),
                    "contributors_count_capped": metrics.get("contributors_count_capped"),
                    "days_since_push": metrics.get("days_since_push"),
                }
            )
        except Exception as e:
            log.warning("Skipping repository due to error: %s", e)
            continue

    # Apply score floor filter (Task 6)
    min_score_cfg = cfg.get("output", {}).get("min_score")
    min_score = float(min_score_cfg) if min_score_cfg is not None else 0.0
    if min_score != 0 and items:
        original_count = len(items)
        filtered_items = []
        for item in items:
            score = item.get("score")  # type: ignore[assignment]
            try:
                score_val = float(score) if score is not None else 0.0
                if score_val >= min_score:
                    filtered_items.append(item)
            except (ValueError, TypeError):
                pass
        items = filtered_items
        filtered_count = original_count - len(items)
        if filtered_count > 0:
            log.info(
                "Applied min_score=%.1f filter: %d repos → %d repos (filtered %d)",
                min_score,
                original_count,
                len(items),
                filtered_count,
            )
    stats["after_score_filter"] = len(items)
    stats["min_score"] = min_score

    output_file, latest_file = _resolve_output_paths(cfg, args.output)
    keep_dated = bool(cfg.get("output", {}).get("keep_dated", False))

    # Ensure output directories exist
    paths_to_prepare = [latest_file] if latest_file else []
    if keep_dated:
        paths_to_prepare.append(output_file)
    for p in paths_to_prepare:
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)

    if not items:
        log.info("No repositories processed; writing an empty curated list stub")
        if latest_file:
            render_markdown([], latest_file, cats_config)
            log.info("Updated canonical index at %s", latest_file)
        if keep_dated:
            render_markdown([], output_file, cats_config)
            log.info("Also updated dated archive at %s", output_file)
        # Write run summary even with no items (Task 12)
        stats["after_score_filter"] = 0
        if latest_file:
            summary_path = os.path.join(os.path.dirname(latest_file), "run-summary.json")
            _write_run_summary(summary_path, stats, [], log)
        return 0

    log.info("Rendering results...")
    if latest_file:
        render_markdown(items, latest_file, cats_config)
        log.info("Updated canonical index at %s", latest_file)
    if keep_dated:
        render_markdown(items, output_file, cats_config)
        log.info("Also updated dated archive at %s", output_file)

    # Clean up old dated files if keep_dated is false (Task 7)
    if not keep_dated and latest_file:
        result_dir = os.path.dirname(latest_file)
        if result_dir:
            # Find and delete dated files matching the pattern healthtech-tools-YYYY-MM-DD.md
            pattern = os.path.join(result_dir, "healthtech-tools-????-??-??.md")
            for dated_file in glob.glob(pattern):
                try:
                    os.remove(dated_file)
                    log.debug("Deleted dated result file: %s", dated_file)
                except OSError as e:
                    log.warning("Failed to delete dated result file %s: %s", dated_file, e)

    # Write run summary (Task 12)
    if latest_file:
        summary_path = os.path.join(os.path.dirname(latest_file), "run-summary.json")
        _write_run_summary(summary_path, stats, items, log)

    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
