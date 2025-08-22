#!/usr/bin/env python3
import argparse
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from hector.config import load_config
from hector import scanner
from hector.scorer import score_repository
from hector.categorizer import categorize_repository
from hector.renderer import render_markdown


def parse_args(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Hector HealthTech Tools Scanner")
    p.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    p.add_argument("--limit", type=int, default=50, help="Max repositories to process")
    group = p.add_mutually_exclusive_group()
    group.add_argument("--dry-run", dest="dry_run", action="store_true", help="Validate config only")
    group.add_argument("--live", dest="dry_run", action="store_false", help="Run live with GitHub API")
    p.set_defaults(dry_run=None)
    p.add_argument("--output", help="Override output markdown file path")
    p.add_argument("--log-level", default="INFO", help="Logging level (DEBUG, INFO, WARNING, ERROR)")
    return p.parse_args(argv)


def setup_logging(level: str) -> None:
    level_num = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=level_num,
        format="%(asctime)s hector %(levelname)s %(message)s",
    )


def _resolve_output_paths(cfg: Dict, cli_output: Optional[str]) -> Tuple[str, Optional[str]]:
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


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    setup_logging(args.log_level)
    log = logging.getLogger("hector")

    cfg = load_config(args.config)

    # Optional overrides from CLI
    if args.dry_run is not None:
        cfg["dry_run"] = bool(args.dry_run)
    if args.output:
        cfg.setdefault("output", {})["file"] = args.output

    if cfg.get("dry_run", False):
        log.info("Dry-run: configuration validated. Set --live or dry_run: false to run live.")
        return 0

    limit = int(args.limit)
    log.info("Searching repositories... limit=%s", limit)
    repos = scanner.search_repositories(cfg, limit=limit)

    weights: Dict = cfg.get("weights", {})
    cats_config: List[str] = cfg.get("output", {}).get("categories", [])
    cat_keywords: Dict = cfg.get("category_keywords") or cfg.get("output", {}).get("category_keywords", {})

    items = []
    for r in repos:
        try:
            name = getattr(r, "full_name", getattr(r, "name", "unknown"))
            url = getattr(r, "html_url", "")
            desc = getattr(r, "description", "") or ""
            # Best-effort: include repo topics to improve categorization recall
            repo_topics: List[str] = []
            try:
                get_topics = getattr(r, "get_topics", None)
                if callable(get_topics):
                    repo_topics = get_topics() or []
            except Exception:
                repo_topics = []
            desc_for_cat = (desc + " " + " ".join(repo_topics)).strip()
            metrics = scanner.get_repo_metrics(r)
            score = score_repository(r, weights, metrics)
            cats = categorize_repository(name, desc_for_cat, cats_config, cat_keywords)
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
                    "days_since_push": metrics.get("days_since_push"),
                }
            )
        except Exception as e:
            log.warning("Skipping repository due to error: %s", e)
            continue

    output_file, latest_file = _resolve_output_paths(cfg, args.output)
    # Ensure output directories exist
    paths_to_prepare = [output_file]
    if latest_file:
        paths_to_prepare.append(latest_file)
    for p in paths_to_prepare:
        d = os.path.dirname(p)
        if d:
            os.makedirs(d, exist_ok=True)
    if not items:
        log.info("No repositories processed; writing an empty curated list stub to %s", output_file)
        render_markdown([], output_file, cats_config)
        if latest_file:
            log.info("Also updating latest index at %s", latest_file)
            render_markdown([], latest_file, cats_config)
        return 0

    log.info("Rendering results to %s ...", output_file)
    render_markdown(items, output_file, cats_config)
    if latest_file:
        log.info("Also updating latest index at %s", latest_file)
        render_markdown(items, latest_file, cats_config)
    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
