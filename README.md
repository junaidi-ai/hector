# Hector — HealthTech Tools Scanner Bot

[![Hector Score](https://img.shields.io/endpoint?url=https://junaidi-ai.github.io/hector/badge.json)](#hector-score-badge)

Hector is an automated bot that discovers, scores, and curates open‑source healthcare technology repositories on GitHub. It uses the GitHub API (no scraping) to evaluate projects against weighted criteria and keeps a ranked, categorized list up to date via scheduled runs or a GitHub Actions workflow.

> Goal: help the community quickly find high‑quality, actively maintained HealthTech tools.

---

## Latest Results

- View the latest curated list here: [result/healthtech-tools.md](result/healthtech-tools.md)

---

## Table of Contents
- [Features](#features)
- [How It Works](#how-it-works)
- [Quickstart](#quickstart)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Authentication](#authentication)
- [Configuration](#configuration)
- [Run Locally](#run-locally)
- [Automate with GitHub Actions](#automate-with-github-actions)
- [Output Example](#output-example)
- [Scoring Methodology](#scoring-methodology)
- [Ethical Considerations](#ethical-considerations)
- [Limitations](#limitations)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Support & Contact](#support--contact)

---

## Features

- **Discovery**
  - Finds public, open‑source HealthTech repos using GitHub Search API queries and/or topic filters.
- **Curation**
  - Scores repos by weighted criteria like:
    - License (e.g., MIT, Apache‑2.0, GPL)
    - Stars, forks, contributors/activity
    - Pull requests, issues, discussions
    - Recent commits/maintenance recency
- **Automation**
  - Runs on a schedule (e.g., daily) via GitHub Actions.
  - Can open PRs to update a curated list file and optionally start discussions for review.
- **Extensibility**
  - Fully configurable weights, search terms, and categories (e.g., Telemedicine, AI Diagnostics).
- **Ethical by Design**
  - Uses GitHub API with rate‑limit awareness and adheres to GitHub Terms of Service (no scraping).

## How It Works

1. **Scan**: Query GitHub for repositories using keywords and/or topics (e.g., "healthtech", "medtech").
2. **Score**: Apply configurable weights to metadata (stars, forks, issues, license, etc.).
3. **Categorize**: Tag repos by focus area using keywords (optional NLP can be added).
4. **Update**: Write a ranked list (e.g., `healthtech-tools.md`) and propose updates via PRs.
5. **Engage**: Optionally open issues/discussions to gather community input.

## Quickstart

### Prerequisites

- GitHub account and a Personal Access Token (PAT) with repo/read access.
- Python 3.10+.
- [uv](https://docs.astral.sh/uv/) installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`).
- GitHub Actions enabled (for automation).

### Installation

```bash
# Clone your fork/repo
git clone https://github.com/your-username/hector.git
cd hector

# Create virtual environment and install dependencies
uv sync

# Or install with dev dependencies (pytest, pre-commit)
uv sync --extra dev
```

### Authentication

Set your GitHub token as an environment variable locally:

```bash
export GITHUB_TOKEN=your_token_here
```

Or store it in GitHub Actions secrets as `GITHUB_TOKEN`.

## Configuration

Create a `config.yaml` in the project root to customize search and scoring:

```yaml
search:
  query: "healthcare technology is:public stars:>50"
  topics: ["healthtech", "medtech", "telemedicine"]
  min_stars: 10              # Filter out repos below this star threshold
  relevance_filter: true     # Discard repos without healthcare keywords (name/description/topics)

weights:
  stars: 0.3
  forks: 0.2
  open_issues: -0.1
  prs: 0.2
  discussions: 0.15
  license: { "MIT": 50, "Apache-2.0": 50, "GPL-3.0": 30, "none": -100 }

output:
  file: "result/healthtech-tools-{date}.md"
  latest: "result/healthtech-tools.md"
  keep_dated: false          # Keep dated archives (default: false, keep only canonical file)
  min_score: 0               # Filter out repos with score below this threshold
  categories: ["AI Diagnostics", "Telemedicine", "Health Data"]
```

Notes:
- Increase or decrease weights to reflect your priorities.
- `license` values act like additive bonuses/penalties.
- `categories` guide tagging of repositories in the final list.
- Set `min_stars` to filter out low-star hobby projects (default: 0, recommended: 10+).

### Query Hygiene

When configuring the search query, be aware of false positives from generic keywords:

**Problems:**
- Keywords like `"robotics"`, `"ros"` pull in industrial/autonomous driving projects (ROS2, navigation stacks)
- Generic `"ai"`, `"edge-ai"`, `"tinyml"` match non-healthcare ML projects
- Arxiv paper trackers, computer vision projects can match on `"imaging"` alone
- These repos pollute the results even if they're technically valid open-source projects

**Best Practices:**

1. **Use healthcare-specific keywords in the base query:**
   - Include explicit healthcare anchors: `healthcare OR medical OR clinical OR health`
   - Example: `(health OR healthcare OR medical OR clinical) in:name,description,readme is:public`

2. **Scope topics to healthcare-specific ones:**
   - ✅ Keep: `digital-therapeutics`, `telemedicine`, `fhir`, `ehr`, `clinical-scribe`
   - ⚠️ Remove or use sparingly: `robotics`, `ros`, `ai`, `edge-ai` (too generic)
   - ⚠️ Avoid: `nextflow`, `wdl`, `vr`, `ar` (common in non-health bioinformatics/game dev)

3. **Use `min_stars` to filter marginal projects:**
   - Set `min_stars: 10` or higher to exclude hobby projects and false positives
   - Higher threshold (e.g., 50+) gives fewer, higher-quality results

4. **Enable post-scan relevance filter:**
   - Set `relevance_filter: true` (default) to automatically discard repos without healthcare keywords
   - Uses a strict allowlist: "health", "medical", "clinical", "patient", "hospital", "diagnostic", etc.
   - Checks repo name, description, and GitHub topics
   - Disable with `relevance_filter: false` for experimental/broader discovery

5. **Validate results manually:**
   - Review high-scoring projects to ensure they're genuinely healthcare-related
   - Check for outliers (e.g., ROS2 robotics, arxiv trackers) that slipped through
   - Update topics list as needed based on findings

## Run Locally

### Standard Mode (Live)

Run your scanner script to scan GitHub and update the curated list:

```bash
python scan_and_curate.py --live --limit 100
```

This will generate/update `healthtech-tools.md` with a ranked list according to `config.yaml`.

### Dry-Run Mode

Test categorization and scoring without hitting the GitHub API:

```bash
python scan_and_curate.py --dry-run
```

This uses sample fixture data from `tests/fixtures/sample-repos.json` to run the full pipeline (categorization, scoring, rendering) without making GitHub API calls. Useful for:
- Testing categorizer changes without burning API quota
- Verifying configuration changes
- Offline development and testing

### Categories-Only Mode

Re-categorize an existing curated list without re-scanning GitHub:

```bash
python scan_and_curate.py --categories-only result/healthtech-tools.md
```

This loads repositories from an existing markdown file and re-categorizes them based on current keyword configurations. Useful for:
- Updating categories when keyword definitions change
- Batch re-processing without GitHub API calls
- Quick iteration on category keywords

## Automate with GitHub Actions

Create `.github/workflows/hector.yml`:

```yaml
name: Hector HealthTech Scan

on:
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install PyGithub
      - name: Run Hector
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: python scan_and_curate.py
      - name: Commit changes
        uses: EndBug/add-and-commit@v9
        with:
          message: "Update curated healthtech list"
```

## Result File Management

By default, Hector maintains a single canonical result file:
- **`result/healthtech-tools.md`** — the canonical, always-current curated list

If you want to keep historical dated archives:
- Set `output.keep_dated: true` in your config
- Files like `result/healthtech-tools-2025-01-15.md` will be retained alongside the canonical file
- Default behavior (`keep_dated: false`) automatically removes old dated files to keep the result directory clean

This policy prevents result file proliferation while allowing optional archival if needed.

## Run Summary

After each scan, Hector writes a JSON summary file to `result/run-summary.json` with pipeline statistics:

```json
{
  "timestamp": "2026-05-21T18:45:30.123456",
  "stats": {
    "total_scanned": 150,
    "after_min_stars": 120,
    "after_relevance_filter": 95,
    "after_score_filter": 78,
    "min_score_threshold": 0
  },
  "categories": {
    "AI Diagnostics": 25,
    "Telemedicine": 18,
    "EHR & Clinical Systems": 15,
    "Imaging & Radiology": 12,
    "Data Platforms & ETL": 8
  },
  "uncategorized_count": 0,
  "total_in_output": 78
}
```

This summary helps you:
- Monitor filter effectiveness (how many repos pass each stage)
- Track category distribution in your curated list
- Verify that min_score filtering is working as expected
- Inspect runs via CI artifacts (GitHub Actions)

## Output Example

A generated `healthtech-tools.md` might look like:

```markdown
# Curated Healthcare Technology Tools

## AI Diagnostics
- **[repo-name](https://github.com/user/repo)** (Score: 85)
  - License: MIT | Stars: 1.2k | Forks: 300 | Active PRs: 5
  - Description: AI-powered diagnostic tool for radiology.

## Telemedicine
- **[another-repo](https://github.com/user/another)** (Score: 78)
  - License: Apache-2.0 | Stars: 900 | Forks: 200 | Discussions: 15
  - Description: Open-source telemedicine platform.
```

## Scoring Methodology

- Base score = weighted sum of metrics defined in `weights`.
- Example components:
  - `stars`, `forks`: popularity indicators.
  - `open_issues`, `prs`, `discussions`: community engagement and maintenance signals.
  - `license`: bonus/penalty based on open‑source friendliness.
- You can enrich the model with:
  - Commit recency decay (favor recently updated repos).
  - Contributor count and bus‑factor signals.
  - Healthcare domain relevance boost (favor healthcare-focused repos).

**Healthcare Domain Relevance Boost:**
- Use `weights.health_relevance_boost` (default: `0`) to give domain-relevant repos a scoring advantage.
- Example: set to `20` to add 20 points for any repo with healthcare keywords (health, medical, clinical, patient, etc.).
- This helps prioritize niche but highly-relevant clinical tools over popular but non-healthcare projects.
- Trade-off: higher boost values favor domain relevance over raw GitHub popularity metrics.

**Score Floor Filtering:**
- Use `output.min_score` (default: `0`) to exclude low-scoring repos from the output.
- Repos with negative scores (e.g., from missing licenses or low activity) are often low-quality or abandoned.
- Set to `0` or higher to filter these out before rendering.
- Example: `min_score: 10` keeps only repos that score positively overall.

## Ethical Considerations

- Uses the GitHub API, respects rate limits, and follows GitHub ToS.
- No unsolicited actions against external repositories.
- Respects repository licenses and community guidelines.

## Medical Disclaimer

Hector provides software analytics and curation of public open‑source repositories. It does not provide medical, diagnostic, or treatment advice. Content and scores are for informational and research purposes only and are not a substitute for professional medical judgment. Always seek the advice of qualified health providers with any questions regarding medical conditions.

## Limitations

- GitHub API rate limits can restrict large scans.
- Categorization is keyword‑based by default; manual review may be needed.
- Bot‑authored issues/discussions are intentionally conservative and may require human oversight.

## Roadmap

- Add caching to reduce API calls and handle pagination efficiently.
- Optional NLP tagging for better categorization.
- Configurable decay functions for activity recency.
- CLI options (e.g., dry‑run, top‑N, category filters).
- Tests and schema validation for `config.yaml`.
- Optional web UI to browse curated results.

## Contributing

Contributions are welcome!

1. Fork the repo.
2. Create a feature branch: `git checkout -b feature/your-idea`.
3. Commit your changes and open a PR describing your approach.
4. Please include tests or example outputs when relevant.

## License

Hector is licensed under the MIT License. See `LICENSE` for details.

## Support & Contact

- Open a GitHub Issue for bugs and feature requests.
- Use Discussions for design ideas and feedback.
- Prefer async support via GitHub; no private data should be shared.

---

## Hector Score Badge (MVP)

This repository publishes Hector Score badges via GitHub Pages + Shields.io.

- Global badge (projects tracked):

```text
https://img.shields.io/endpoint?url=https://junaidi-ai.github.io/hector/badge.json
```

- Per-project badge (replace org/repo):

```text
https://img.shields.io/endpoint?url=https://junaidi-ai.github.io/hector/badges/<org>__<repo>.json
```

Example:

```text
https://img.shields.io/endpoint?url=https://junaidi-ai.github.io/hector/badges/Project-MONAI__MONAI.json
```

Projects can embed the badge in their README to display their latest Hector Score.
