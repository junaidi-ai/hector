#!/usr/bin/env python3
import argparse
import re
from typing import Dict, List, Optional, Tuple

from hector.config import load_config
from hector.categorizer import categorize_repository
from hector.renderer import render_markdown

HEADER_RE = re.compile(r"^- \*\*\[(?P<name>.+?)\]\((?P<url>.+?)\)\*\* \(Score: (?P<score>[-\d\.]+)\)")
LICENSE_RE = re.compile(r"^\s*- License: (?P<license>[^|]+)\| Stars: (?P<stars>\d+) \| Forks: (?P<forks>\d+)")
EXTRA_RE = re.compile(r"^\s*- (?P<parts>.+)$")
DESC_RE = re.compile(r"^\s*- Description: (?P<desc>.+)$")


def parse_items(lines: List[str]) -> List[Dict]:
    items: List[Dict] = []
    current: Optional[Dict] = None

    def commit():
        nonlocal current
        if current is not None:
            items.append(current)
            current = None

    for raw in lines:
        line = raw.rstrip("\n")
        if line.startswith("# ") or line.startswith("## ") or not line.strip():
            # section headers and blanks are ignored for parsing items
            continue
        m = HEADER_RE.match(line)
        if m:
            commit()
            current = {
                "name": m.group("name").strip(),
                "url": m.group("url").strip(),
                "score": float(m.group("score")),
                "license": "",
                "stars": 0,
                "forks": 0,
                "prs_open": None,
                "has_discussions": None,
                "contributors_count": None,
                "days_since_push": None,
                "description": "",
            }
            continue
        if current is None:
            continue
        m = LICENSE_RE.match(line.replace("  - ", "- "))
        if m:
            current["license"] = m.group("license").strip()
            current["stars"] = int(m.group("stars"))
            current["forks"] = int(m.group("forks"))
            continue
        if line.strip().startswith("- PRs open:"):
            # Normalize the indent for regex
            parts = [p.strip() for p in line.split(":", 1)[1].split("|")]
            # Fallback: use a simple parse to avoid overfitting regex
            try:
                prs_part = parts[0].strip()
                current["prs_open"] = int(prs_part)
            except Exception:
                pass
            for p in parts[1:]:
                p = p.strip()
                if p.lower().startswith("discussions:"):
                    val = p.split(":", 1)[1].strip().lower()
                    current["has_discussions"] = True if val.startswith("yes") else False
                elif p.lower().startswith("contributors:"):
                    try:
                        current["contributors_count"] = int(p.split(":", 1)[1].strip())
                    except Exception:
                        pass
                elif p.lower().startswith("last push:") and p.lower().endswith("days ago"):
                    num = p.split(":", 1)[1].strip().split(" ")[0]
                    try:
                        current["days_since_push"] = int(num)
                    except Exception:
                        pass
            continue
        m = DESC_RE.match(line.strip())
        if m:
            current["description"] = m.group("desc").strip()
            continue

    commit()
    return items


def recategorize_file(path: str, cats_config: List[str], cat_keywords: Dict) -> Tuple[int, int]:
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    items = parse_items(lines)
    before = len(items)

    for it in items:
        desc = it.get("description", "")
        cats = categorize_repository(it.get("name", ""), desc, cats_config, cat_keywords)
        it["categories"] = cats or ["Uncategorized"]

    # Re-render in place
    render_markdown(items, path, cats_config)

    after = len(items)
    return before, after


def main():
    ap = argparse.ArgumentParser(description="Re-categorize existing curated markdown files in-place")
    ap.add_argument("files", nargs="+", help="Paths to markdown files to recategorize")
    ap.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    cats_config: List[str] = cfg.get("output", {}).get("categories", [])
    cat_keywords: Dict = cfg.get("category_keywords") or cfg.get("output", {}).get("category_keywords", {})

    for p in args.files:
        before, after = recategorize_file(p, cats_config, cat_keywords)
        print(f"Processed {p}: {before} items recategorized")


if __name__ == "__main__":
    main()
