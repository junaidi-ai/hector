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
- Python 3.8+ (recommended 3.10+).
- GitHub Actions enabled (for automation).

### Installation

```bash
# Clone your fork/repo
git clone https://github.com/your-username/hector.git

# (Optional) create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate

# Install dependencies
pip install PyGithub
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
  categories: ["AI Diagnostics", "Telemedicine", "Health Data"]
```

Notes:
- Increase or decrease weights to reflect your priorities.
- `license` values act like additive bonuses/penalties.
- `categories` guide tagging of repositories in the final list.

## Run Locally

Run your scanner script (example filename):

```bash
python scan_and_curate.py
```

This will generate/update `healthtech-tools.md` with a ranked list according to `config.yaml`.

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
  - Topic/keyword relevance boosts.

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
