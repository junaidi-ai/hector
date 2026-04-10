# Hector — Fix & Enhancement TODO

> Version: post-v0.1.0 → target v0.2.0
> Priority order: P0 (blocking correctness) → P1 (quality) → P2 (enhancement)

---

## P0 — Correctness: Wrong Categorization

### Task 1 — Remove/restrict the AI-indicator fallback in `categorizer.py`
- **File**: `hector/categorizer.py` → `categorize_repository()`
- **Problem**: The `ai_indicators` fallback at the end of the function matches any AI/ML repo (ROS2, robotics, arxiv trackers, autonomous driving) and dumps it into "AI Diagnostics".
- Subtasks:
  - [x] Remove the fallback entirely, OR gate it behind an explicit healthcare-context check (repo must also match ≥1 health keyword from a strict allowlist: "health", "medical", "clinical", "patient", "hospital", "diagnostic", "therapeutic", "pharma", "biomedical")
  - [x] If repo matches no category after keyword pass and passes no healthcare gate → assign "Uncategorized" only, do not force-assign "AI Diagnostics"

### Task 2 — Tighten keyword lists in `DEFAULT_KEYWORDS`
- **File**: `hector/categorizer.py` → `DEFAULT_KEYWORDS`
- **Problem**: Keywords are too broad:
  - `"imaging"` matches camera/sensor repos (RealSense, Gazebo, reComputer)
  - `"nlp"` matches all NLP regardless of domain
  - `"robotic"` / `"robotics"` (if user-configured) matches ROS2 industrial/drone repos
  - `"ct"` is a 2-letter token that can false-positive on common words
- Subtasks:
  - [x] Replace `"imaging"` → `"medical imaging"`, `"clinical imaging"`
  - [x] Replace `"nlp"` → `"clinical nlp"`, `"medical nlp"`, `"clinical text mining"`
  - [x] Replace `"ct"` → `"ct scan"`, `"computed tomography"`
  - [x] Add negative-context guard: if description/name contains `"ros2"`, `"ros "`, `"autonomous driving"`, `"drone"`, `"navigation stack"` → skip category assignment for that repo entirely (or assign "Uncategorized")
  - [x] Enforce minimum keyword length of 3 characters in `_phrase_in_text()` for non-phrase (no-space) tokens

### Task 3 — Add a healthcare relevance pre-filter in `categorize_repository()`
- **File**: `hector/categorizer.py`
- **Problem**: Repos with zero healthcare context are being categorized.
- Subtasks:
  - [x] Implement `_is_healthcare_relevant(text: str) -> bool` using a strict allowlist of health domain anchors (see Task 1 list)
  - [x] Call it at the top of `categorize_repository()`; if `False`, return `["Uncategorized"]` immediately, skipping all keyword passes
  - [x] Expose a config toggle `categorizer.require_health_context: true/false` (default `true`) so power users can opt out

---

## P0 — Correctness: Scanner Pulling Non-Healthcare Repos

### Task 4 — Strengthen the scanner query in `config.yaml`
- **File**: `config.yaml` (user's config, document the requirement in README)
- **Problem**: Current query/topics are too permissive; pulling in robotics, arxiv trackers, autonomous driving.
- Subtasks:
  - [ ] Add healthcare-specific required terms to the base query (e.g., `healthcare OR medical OR clinical OR "health tech"`) so GitHub's search engine pre-filters
  - [ ] Remove or scope down generic topics that bleed in non-healthcare repos
  - [ ] Document recommended query structure in README with a "query hygiene" section
  - [ ] Add a `scanner.min_stars` config option (default: `10`) and filter repos below threshold before scoring

### Task 5 — Add post-scan relevance filter in `scanner.py` or pipeline entry point
- **File**: `hector/scanner.py` or `scan_and_curate.py`
- **Problem**: Even with a better query, marginal repos slip through.
- Subtasks:
  - [ ] After `search_repositories()` returns, pass each repo through a lightweight relevance check using the same healthcare anchor list from Task 3
  - [ ] Check `repo.name`, `repo.description`, and `repo.topics` (GitHub topics list)
  - [ ] Discard repos where none of name/description/topics contain a healthcare anchor

---

## P0 — Correctness: Negative-Score Repos Included in Output

### Task 6 — Add score floor filter before rendering
- **File**: `hector/renderer.py` or pipeline entry point
- **Problem**: Many repos with scores < 0 (e.g., -132, -95) appear in the output.
- Subtasks:
  - [ ] Add `output.min_score` config key (default: `0`)
  - [ ] Filter `items` in `render_markdown()` (or before calling it) to exclude entries below `min_score`
  - [ ] Log count of excluded repos at INFO level

---

## P1 — Quality: Result File Hygiene

### Task 7 — Enforce single canonical result file; purge dated duplicates
- **File**: `result/` directory, `hector/renderer.py`, CI workflow
- **Problem**: Dated files (e.g., `healthtech-tools-2025-01-15.md`) accumulate alongside the canonical `healthtech-tools.md`. Only the canonical file should be kept per project policy.
- Subtasks:
  - [ ] In `render_markdown()` (or pipeline), write only to `output.latest` path (`result/healthtech-tools.md`)
  - [ ] Remove `output.file` dated-template logic from the default pipeline (keep the config key but do not write it by default; gate it behind `output.keep_dated: true`, default `false`)
  - [ ] Add a CI step (or post-run script) to delete any `result/healthtech-tools-*.md` files if `keep_dated` is false
  - [ ] **Immediate one-time cleanup**: delete all existing dated files in `result/`, keep only `result/healthtech-tools.md`

---

## P1 — Quality: Scorer Improvements

### Task 8 — Add healthcare-domain relevance boost to scoring
- **File**: `hector/scorer.py`
- **Problem**: Score is purely GitHub popularity metrics; a highly-starred ROS2 repo outscores a niche but directly relevant clinical tool.
- Subtasks:
  - [ ] Add optional `weights.health_relevance_boost` config key (default: `0`)
  - [ ] In `score_repository()`, compute a boolean relevance flag using the same anchor check from Task 3 and multiply by the boost weight
  - [ ] This allows operators to dial up domain relevance vs. raw popularity

### Task 9 — Cap contributor count at first-page limit in `get_repo_metrics()`
- **File**: `hector/scanner.py` → `get_repo_metrics()`
- **Problem**: Current code fetches only page 0 but stores `len(first_page)` which is at most 30, distorting contributor weight for large projects.
- Subtasks:
  - [ ] Document in code that `contributors_count` is "first-page count (≤30), not total"
  - [ ] Add `contributors_count_capped: true` field in metrics dict so scorer/renderer can note this
  - [ ] OR: use `repo.get_stats_contributors()` which returns aggregate data but is rate-limit heavier — gate behind `scanner.fetch_contributor_stats: false` (default)

---

## P1 — Quality: Categorizer Robustness

### Task 10 — Add unit tests for `categorizer.py`
- **File**: `tests/test_categorizer.py` (new)
- Subtasks:
  - [ ] Test: known-good healthcare repos → correctly categorized
  - [ ] Test: ROS2/robotics repos → "Uncategorized" (not "AI Diagnostics" or "NLP & Clinical Text")
  - [ ] Test: arxiv paper tracker → "Uncategorized"
  - [ ] Test: DICOM/PACS tool → "Imaging & Radiology"
  - [ ] Test: `_phrase_in_text` boundary conditions (short tokens, multi-word phrases)
  - [ ] Test: `_is_healthcare_relevant` allowlist (Task 3)

### Task 11 — Add unit tests for `scorer.py`
- **File**: `tests/test_scorer.py` (new)
- Subtasks:
  - [ ] Test: all-zero weights → score equals license bonus only
  - [ ] Test: negative open_issues weight reduces score
  - [ ] Test: recency_decay on a 365-day-old repo
  - [ ] Test: unknown license → falls back to "none" key in license map

---

## P2 — Enhancement: Observability

### Task 12 — Add run summary output
- **File**: pipeline entry point (`scan_and_curate.py`)
- Subtasks:
  - [ ] After rendering, print/log: total scanned, total passed relevance filter, total above min_score, count per category, count "Uncategorized"
  - [ ] Write summary as a brief `result/run-summary.json` (overwrite each run) for CI artifact inspection

### Task 13 — Add `--dry-run` and `--categories-only` CLI flags
- **File**: `scan_and_curate.py`
- Subtasks:
  - [ ] `--dry-run`: skip GitHub API calls, load fixture data if present, run scoring/categorization, write output — useful for testing categorizer changes without burning API quota
  - [ ] `--categories-only path/to/existing.md`: re-categorize an existing result file without re-scanning

---

## Versioning

| Task group | Target version |
|---|---|
| P0 (Tasks 1–7) | v0.2.0 |
| P1 (Tasks 8–11) | v0.2.0 |
| P2 (Tasks 12–13) | v0.3.0 |
