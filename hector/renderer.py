from collections import defaultdict
from typing import Dict, Iterable, List


def render_markdown(items: List[Dict], output_file: str, categories: Iterable[str]) -> None:
    """Render a simple categorized Markdown file from scored items.

    Expected item keys: name, url, score, description, categories (list[str]), license, stars, forks
    """
    by_cat: Dict[str, List[Dict]] = defaultdict(list)
    for it in items:
        cats = it.get("categories") or ["Uncategorized"]
        for c in cats:
            by_cat[c].append(it)

    # Ensure declared categories appear first, in order
    ordered_sections: List[str] = [str(c) for c in categories]
    for c in by_cat.keys():
        if c not in ordered_sections:
            ordered_sections.append(c)

    lines: List[str] = ["# Curated Healthcare Technology Tools", ""]
    for cat in ordered_sections:
        sect = by_cat.get(cat, [])
        if not sect:
            continue
        lines.append(f"## {cat}")
        for it in sorted(sect, key=lambda x: x.get("score", 0), reverse=True):
            name = it.get("name", "repo")
            url = it.get("url", "")
            score = round(float(it.get("score", 0)), 2)
            desc = it.get("description", "").strip()
            lic = it.get("license", "")
            stars = int(it.get("stars", 0))
            forks = int(it.get("forks", 0))
            lines.append(f"- **[{name}]({url})** (Score: {score})")
            lines.append(f"  - License: {lic} | Stars: {stars} | Forks: {forks}")
            # Optional richer metrics
            extra_parts: List[str] = []
            if it.get("prs_open") is not None:
                extra_parts.append(f"PRs open: {int(it.get('prs_open') or 0)}")
            if it.get("has_discussions") is not None:
                extra_parts.append("Discussions: Yes" if it.get("has_discussions") else "Discussions: No")
            if it.get("contributors_count") is not None:
                extra_parts.append(f"Contributors: {int(it.get('contributors_count') or 0)}")
            if it.get("days_since_push") is not None:
                extra_parts.append(f"Last push: {int(it.get('days_since_push') or 0)} days ago")
            if extra_parts:
                lines.append("  - " + " | ".join(extra_parts))
            if desc:
                lines.append(f"  - Description: {desc}")
        lines.append("")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines).rstrip() + "\n")
