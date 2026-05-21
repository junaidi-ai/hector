#!/usr/bin/env python3
"""
Generate docs/index.html from result/healthtech-tools.md.

Reads the canonical curated list and emits a static HTML page that renders
all repos grouped by category with score chips, metadata, and descriptions.
Optionally reads result/run-summary.json for the stats bar.

Run:
    python scripts/generate_pages_html.py
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULT_MD = ROOT / "result" / "healthtech-tools.md"
RUN_SUMMARY = ROOT / "result" / "run-summary.json"
OUT_HTML = ROOT / "docs" / "index.html"

# ── Regex patterns matching renderer.py output ────────────────────────────────
RE_H2 = re.compile(r"^## (.+)$")
RE_ITEM = re.compile(
    r"^\s*- \*\*\[(?P<name>[^\]]+)\]\((?P<url>[^\)]+)\)\*\* \(Score: (?P<score>[-0-9.]+)\)"
)
RE_META = re.compile(
    r"^\s*- License:\s*(?P<lic>[^|]+)\|\s*Stars:\s*(?P<stars>\d+)\s*\|\s*Forks:\s*(?P<forks>\d+)"
)
RE_EXTRA = re.compile(r"^\s*- (?:PRs open:|Discussions:|Contributors:|Last push:)")
RE_DESC = re.compile(r"^\s*- Description:\s*(.+)$")


# ── Score → color (mirrors generate_badge_json.py) ────────────────────────────
def _color_for_score(score: float) -> str:
    if score >= 500:
        return "#22c55e"  # brightgreen
    if score >= 200:
        return "#4ade80"  # green
    if score >= 100:
        return "#a3e635"  # yellowgreen
    if score >= 50:
        return "#facc15"  # yellow
    if score >= 10:
        return "#fb923c"  # orange
    return "#9ca3af"  # lightgrey


# ── Markdown parser ────────────────────────────────────────────────────────────
def parse_result_md(path: Path) -> list[dict]:
    """Return list of category dicts: {name, repos: [{name, url, score, lic, stars, forks, desc}]}."""
    if not path.exists():
        return []

    categories: list[dict] = []
    current_cat: dict | None = None
    current_repo: dict | None = None

    def _flush_repo() -> None:
        if current_cat is not None and current_repo is not None:
            current_cat["repos"].append(current_repo)

    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m_h2 = RE_H2.match(line)
        if m_h2:
            _flush_repo()
            current_repo = None
            current_cat = {"name": m_h2.group(1).strip(), "repos": []}
            categories.append(current_cat)
            continue

        m_item = RE_ITEM.match(line)
        if m_item and current_cat is not None:
            _flush_repo()
            try:
                score = float(m_item.group("score"))
            except ValueError:
                score = 0.0
            current_repo = {
                "name": m_item.group("name").strip(),
                "url": m_item.group("url").strip(),
                "score": score,
                "lic": "",
                "stars": 0,
                "forks": 0,
                "desc": "",
            }
            continue

        if current_repo is None:
            continue

        m_meta = RE_META.match(line)
        if m_meta:
            current_repo["lic"] = m_meta.group("lic").strip()
            current_repo["stars"] = int(m_meta.group("stars"))
            current_repo["forks"] = int(m_meta.group("forks"))
            continue

        m_desc = RE_DESC.match(line)
        if m_desc:
            current_repo["desc"] = m_desc.group(1).strip()
            continue

    _flush_repo()
    return [c for c in categories if c["repos"]]


def _load_run_summary(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


# ── HTML helpers ──────────────────────────────────────────────────────────────
def _e(s: object) -> str:
    return html.escape(str(s))


def _repo_card(repo: dict) -> str:
    color = _color_for_score(repo["score"])
    score_chip = (
        f'<span class="score-chip" style="background:{color}">' f'Score {repo["score"]:.1f}</span>'
    )
    stars = f'⭐ {repo["stars"]:,}' if repo["stars"] else ""
    forks = f'🍴 {repo["forks"]:,}' if repo["forks"] else ""
    lic = (
        f'<span class="badge">{_e(repo["lic"])}</span>'
        if repo["lic"] and repo["lic"] != "none"
        else ""
    )
    meta_parts = [p for p in [stars, forks] if p]
    meta_str = " &nbsp;·&nbsp; ".join(_e(p) for p in meta_parts)
    desc_html = f'<p class="repo-desc">{_e(repo["desc"])}</p>' if repo["desc"] else ""

    return f"""
      <div class="repo-card" data-name="{_e(repo['name'].lower())}" data-desc="{_e(repo['desc'].lower())}">
        <div class="repo-header">
          <a class="repo-name" href="{_e(repo['url'])}" target="_blank" rel="noopener">{_e(repo['name'])}</a>
          {score_chip}
        </div>
        <div class="repo-meta">{lic} {meta_str}</div>
        {desc_html}
      </div>"""


def _category_section(cat: dict) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", cat["name"].lower()).strip("-")
    cards = "\n".join(_repo_card(r) for r in cat["repos"])
    count = len(cat["repos"])
    return f"""
    <section class="cat-section" id="cat-{_e(slug)}" data-category="{_e(slug)}">
      <h2 class="cat-heading">
        {_e(cat['name'])}
        <span class="cat-count">{count}</span>
      </h2>
      <div class="repo-grid">
{cards}
      </div>
    </section>"""


def _stats_bar(summary: dict) -> str:
    if not summary:
        return ""
    stats = summary.get("stats", {})
    total_in = summary.get("total_in_output", 0)
    total_scanned = stats.get("total_scanned", 0)
    ts = summary.get("timestamp", "")
    date_str = ts[:10] if ts else ""
    return f"""
    <div class="stats-bar" id="stats-bar">
      <span>📊 <strong>{total_in}</strong> repos curated</span>
      <span class="sep">·</span>
      <span><strong>{total_scanned}</strong> scanned</span>
      {f'<span class="sep">·</span><span>Last run: {_e(date_str)}</span>' if date_str else ""}
    </div>"""


def _category_pills(categories: list[dict]) -> str:
    pills = ['<button class="pill active" data-filter="all">All</button>']
    for cat in categories:
        slug = re.sub(r"[^a-z0-9]+", "-", cat["name"].lower()).strip("-")
        pills.append(
            f'<button class="pill" data-filter="{_e(slug)}">{_e(cat["name"])}'
            f' <span class="pill-count">{len(cat["repos"])}</span></button>'
        )
    return '<div class="pills" id="cat-pills">\n      ' + "\n      ".join(pills) + "\n    </div>"


def build_html(categories: list[dict], summary: dict) -> str:
    total = sum(len(c["repos"]) for c in categories)
    stats_bar = _stats_bar(summary)
    pills = _category_pills(categories)
    sections = "\n".join(_category_section(c) for c in categories)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Hector • Healthtech Tools ({total} projects)</title>
  <style>
    :root {{
      color-scheme: light dark;
      --bg: #0b0b0c;
      --text: #e7e7ea;
      --muted: #9aa0a6;
      --card-bg: rgb(255 255 255 / 0.06);
      --card-border: rgb(255 255 255 / 0.10);
      --link: #7dd3fc;
      --link-hover: #38bdf8;
      --pill-bg: rgb(255 255 255 / 0.08);
      --pill-active-bg: #0ea5e9;
      --pill-active-text: #fff;
      --stats-bg: rgb(255 255 255 / 0.04);
    }}
    @media (prefers-color-scheme: light) {{
      :root {{
        --bg: #f7fafc; --text: #0f172a; --muted: #475569;
        --card-bg: #ffffff; --card-border: rgb(0 0 0 / 0.08);
        --link: #0ea5e9; --link-hover: #0284c7;
        --pill-bg: #e2e8f0; --stats-bg: #eef2f7;
      }}
    }}
    [data-theme="light"] {{
      --bg: #f7fafc; --text: #0f172a; --muted: #475569;
      --card-bg: #ffffff; --card-border: rgb(0 0 0 / 0.08);
      --link: #0ea5e9; --link-hover: #0284c7;
      --pill-bg: #e2e8f0; --stats-bg: #eef2f7;
    }}
    [data-theme="dark"] {{
      --bg: #0b0b0c; --text: #e7e7ea; --muted: #9aa0a6;
      --card-bg: rgb(255 255 255 / 0.06); --card-border: rgb(255 255 255 / 0.10);
      --link: #7dd3fc; --link-hover: #38bdf8;
      --pill-bg: rgb(255 255 255 / 0.08); --stats-bg: rgb(255 255 255 / 0.04);
    }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 0; background: var(--bg); color: var(--text); }}
    header {{ position: relative; padding: 40px 20px 32px; text-align: center; background: linear-gradient(135deg,#0ea5e9 0%,#22c55e 100%); color: #fff; }}
    header h1 {{ margin: 0 0 6px; font-size: 2rem; }}
    header p {{ margin: 0; opacity: .85; font-size: 1rem; }}
    .theme-select {{ position: absolute; top: 14px; right: 14px; background: rgb(255 255 255 / 0.92); color: #0f172a; border: none; border-radius: 999px; padding: 6px 12px; font-size: 13px; cursor: pointer; }}
    .stats-bar {{ display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; padding: 10px 20px; background: var(--stats-bg); border-bottom: 1px solid var(--card-border); font-size: 14px; color: var(--muted); justify-content: center; }}
    .stats-bar .sep {{ opacity: .4; }}
    main {{ max-width: 960px; margin: 0 auto; padding: 20px 16px 60px; }}
    .search-wrap {{ margin: 0 0 16px; }}
    #search {{ width: 100%; padding: 10px 16px; border-radius: 10px; border: 1px solid var(--card-border); background: var(--card-bg); color: var(--text); font-size: 15px; outline: none; }}
    #search:focus {{ border-color: #0ea5e9; }}
    .pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 24px; }}
    .pill {{ padding: 6px 14px; border-radius: 999px; border: none; background: var(--pill-bg); color: var(--text); font-size: 13px; cursor: pointer; transition: background .15s; }}
    .pill:hover {{ background: var(--pill-active-bg); color: var(--pill-active-text); }}
    .pill.active {{ background: var(--pill-active-bg); color: var(--pill-active-text); }}
    .pill-count {{ opacity: .7; font-size: 11px; }}
    .cat-section {{ margin-bottom: 40px; }}
    .cat-heading {{ font-size: 1.2rem; font-weight: 700; margin: 0 0 14px; padding-bottom: 8px; border-bottom: 1px solid var(--card-border); display: flex; align-items: center; gap: 10px; }}
    .cat-count {{ font-size: 12px; font-weight: 500; background: var(--pill-bg); padding: 2px 8px; border-radius: 999px; color: var(--muted); }}
    .repo-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; }}
    .repo-card {{ background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 16px; transition: border-color .15s; }}
    .repo-card:hover {{ border-color: #0ea5e9; }}
    .repo-header {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; margin-bottom: 8px; }}
    .repo-name {{ color: var(--link); font-weight: 600; font-size: 14px; text-decoration: none; flex: 1; min-width: 0; word-break: break-word; }}
    .repo-name:hover {{ color: var(--link-hover); text-decoration: underline; }}
    .score-chip {{ flex-shrink: 0; font-size: 11px; font-weight: 700; color: #000; padding: 3px 8px; border-radius: 999px; white-space: nowrap; }}
    .repo-meta {{ font-size: 12px; color: var(--muted); margin-bottom: 6px; }}
    .badge {{ background: var(--pill-bg); padding: 1px 6px; border-radius: 4px; font-size: 11px; margin-right: 4px; }}
    .repo-desc {{ margin: 0; font-size: 13px; color: var(--muted); line-height: 1.5; }}
    .hidden {{ display: none !important; }}
    #no-results {{ display: none; text-align: center; color: var(--muted); padding: 48px 0; font-size: 15px; }}
    footer {{ text-align: center; color: var(--muted); font-size: 13px; padding: 24px; }}
  </style>
</head>
<body>
  <header>
    <label style="position:absolute;left:-9999px" for="theme-select">Color theme</label>
    <select class="theme-select" id="theme-select" aria-label="Color theme">
      <option value="system">System</option>
      <option value="light">Light</option>
      <option value="dark">Dark</option>
    </select>
    <h1>Hector</h1>
    <p>Curated open-source Healthtech tools &mdash; {total} projects tracked</p>
  </header>

  {stats_bar}

  <main>
    <div class="search-wrap">
      <input type="search" id="search" placeholder="Search repos by name or description…" autocomplete="off" />
    </div>

    {pills}

    <div id="no-results">No repos match your search.</div>

{sections}
  </main>

  <footer>
    <small>Published via GitHub Pages &bull; Updated automatically by CI &bull;
    <a href="https://github.com/junaidi-ai/hector" target="_blank" rel="noopener">Source</a></small>
  </footer>

  <script>
    // ── Theme toggle ──────────────────────────────────────────────────────────
    (function() {{
      const KEY = 'hector:theme';
      const root = document.documentElement;
      const sel = document.getElementById('theme-select');
      function apply(t) {{ t === 'system' ? root.removeAttribute('data-theme') : root.setAttribute('data-theme', t); }}
      const saved = localStorage.getItem(KEY) || 'system';
      sel.value = saved; apply(saved);
      sel.addEventListener('change', e => {{ localStorage.setItem(KEY, e.target.value); apply(e.target.value); }});
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {{ if ((localStorage.getItem(KEY) || 'system') === 'system') apply('system'); }});
    }})();

    // ── Search + category filter ──────────────────────────────────────────────
    (function() {{
      const searchEl = document.getElementById('search');
      const pills = document.querySelectorAll('.pill');
      const sections = document.querySelectorAll('.cat-section');
      const noResults = document.getElementById('no-results');
      let activeCat = 'all';

      function filter() {{
        const q = searchEl.value.trim().toLowerCase();
        let visibleTotal = 0;

        sections.forEach(sec => {{
          const catSlug = sec.dataset.category;
          const catMatch = activeCat === 'all' || activeCat === catSlug;
          if (!catMatch) {{ sec.classList.add('hidden'); return; }}

          const cards = sec.querySelectorAll('.repo-card');
          let visibleInSec = 0;
          cards.forEach(card => {{
            const nameMatch = !q || card.dataset.name.includes(q);
            const descMatch = !q || card.dataset.desc.includes(q);
            if (nameMatch || descMatch) {{ card.classList.remove('hidden'); visibleInSec++; }}
            else {{ card.classList.add('hidden'); }}
          }});
          sec.classList.toggle('hidden', visibleInSec === 0);
          visibleTotal += visibleInSec;
        }});

        noResults.style.display = visibleTotal === 0 ? 'block' : 'none';
      }}

      searchEl.addEventListener('input', filter);

      pills.forEach(pill => {{
        pill.addEventListener('click', () => {{
          pills.forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          activeCat = pill.dataset.filter;
          filter();
        }});
      }});
    }})();
  </script>
</body>
</html>
"""


# ── Entry point ────────────────────────────────────────────────────────────────
def main() -> int:
    categories = parse_result_md(RESULT_MD)
    summary = _load_run_summary(RUN_SUMMARY)

    if not categories:
        print(f"Warning: no categories parsed from {RESULT_MD}. Writing empty page.")

    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    html_content = build_html(categories, summary)
    OUT_HTML.write_text(html_content, encoding="utf-8")

    total = sum(len(c["repos"]) for c in categories)
    print(f"Wrote {total} repos across {len(categories)} categories → {OUT_HTML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
