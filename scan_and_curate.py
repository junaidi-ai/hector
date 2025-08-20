#!/usr/bin/env python3
import argparse
import logging
import sys
from typing import Dict, List

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

    items = []
    for r in repos:
        try:
            name = getattr(r, "full_name", getattr(r, "name", "unknown"))
            url = getattr(r, "html_url", "")
            desc = getattr(r, "description", "") or ""
            metrics = scanner.get_repo_metrics(r)
            score = score_repository(r, weights, metrics)
            cats = categorize_repository(name, desc, cats_config)
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

    output_file = cfg.get("output", {}).get("file", "healthtech-tools.md")
    if not items:
        log.info("No repositories processed; writing an empty curated list stub to %s", output_file)
        render_markdown([], output_file, cats_config)
        return 0

    log.info("Rendering results to %s ...", output_file)
    render_markdown(items, output_file, cats_config)
    log.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
