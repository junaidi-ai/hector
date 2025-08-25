#!/usr/bin/env python3
"""
Generate Shields.io-compatible badge JSON files from the latest curated results.

Outputs:
- docs/badge.json: global badge (e.g., total projects tracked)
- docs/badges/<org>__<repo>.json: per-project score badges

Shields schema: https://shields.io/endpoint
{"schemaVersion":1,"label":"Hector Score","message":"123.4","color":"green"}
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
RESULT_LATEST = ROOT / "result" / "healthtech-tools.md"
DOCS_DIR = ROOT / "docs"
BADGES_DIR = DOCS_DIR / "badges"

RE_ITEM = re.compile(
    # - **[org/repo](https://github.com/org/repo)** (Score: 123.45)
    r"^\s*- \*\*\[(?P<name>[^\]]+)\]\((?P<url>[^\)]+)\)\*\* \(Score: (?P<score>[-0-9.]+)\)",
    re.IGNORECASE,
)


def _color_for_score(score: float) -> str:
    if score >= 500:
        return "brightgreen"
    if score >= 200:
        return "green"
    if score >= 100:
        return "yellowgreen"
    if score >= 50:
        return "yellow"
    if score >= 10:
        return "orange"
    return "lightgrey"


def _slug_from_url(url: str) -> str | None:
    try:
        p = urlparse(url)
        if p.netloc.lower() != "github.com":
            return None
        parts = [seg for seg in p.path.split("/") if seg]
        if len(parts) < 2:
            return None
        org, repo = parts[0], parts[1]
        return f"{org}__{repo}"
    except Exception:
        return None


def parse_results(md_path: Path) -> List[Tuple[str, str, float]]:
    items: List[Tuple[str, str, float]] = []
    if not md_path.exists():
        return items
    for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = RE_ITEM.match(line)
        if not m:
            continue
        url = m.group("url").strip()
        name = m.group("name").strip()
        try:
            score = float(m.group("score"))
        except Exception:
            continue
        items.append((name, url, score))
    return items


def main() -> int:
    items = parse_results(RESULT_LATEST)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    BADGES_DIR.mkdir(parents=True, exist_ok=True)

    # Global badge: number of projects tracked
    global_badge = {
        "schemaVersion": 1,
        "label": "Hector",
        "message": f"{len(items)} projects",
        "color": "blue",
    }
    (DOCS_DIR / "badge.json").write_text(json.dumps(global_badge), encoding="utf-8")

    # Per-project badges
    for name, url, score in items:
        slug = _slug_from_url(url)
        if not slug:
            # Fallback slug from name
            slug = re.sub(r"[^A-Za-z0-9_]+", "_", name)
        badge = {
            "schemaVersion": 1,
            "label": "Hector Score",
            "message": f"{score:.2f}",
            "color": _color_for_score(score),
        }
        (BADGES_DIR / f"{slug}.json").write_text(json.dumps(badge), encoding="utf-8")

    # No Jekyll to allow paths with underscores
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Wrote {len(items)} project badges and global badge to {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
