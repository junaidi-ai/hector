# Changelog

All notable changes to this project will be documented in this file.

The format is loosely based on Keep a Changelog, and this project adheres to tags to mark releases (e.g., v0.1.0).

## [v0.3.0] - 2026-05-21

### Added
- **Enhanced CLI modes**:
  - `--dry-run`: Test categorization/scoring with fixture data (no GitHub API calls)
  - `--categories-only`: Re-categorize existing markdown files without re-scanning
  - Fixture data: `tests/fixtures/sample-repos.json` with 5 sample healthcare repos
- **Run observability**: JSON summary output (`result/run-summary.json`) with pipeline statistics
- **Comprehensive unit tests**:
  - 18 tests for categorizer.py covering healthcare detection, ROS2/autonomous driving exclusion
  - 8 tests for scorer.py covering weights, license bonuses, recency decay, healthcare boost
  - 100% test coverage of core scoring and categorization logic
- **Documentation updates**: Usage examples for all CLI modes in README

### Fixed
- Text normalization in phrase matching (both phrase and text now normalized)
- Removed "care" from healthcare anchors (too broad, caused false positives)
- Extended relaxed substring matching to 3-8 character tokens for root words like "health"

### Changed
- CI workflow: Only add canonical result file to PRs (no dated archives by default)
- Score filtering: Applied before rendering with configurable `output.min_score`
- Healthcare relevance: Pre-filter in categorizer ensures only relevant repos are categorized

### Improved
- Contributor count metrics: Flag indicates if capped (first page ~30 only)
- Health relevance boost: Optional weight to prioritize domain-relevant repos
- Type safety: Full mypy type checking on all production code

## [v0.2.0] - 2025-12-xx

- Initial P0/P1 feature release with core correctness and quality improvements
- Categorization robustness, scoring enhancements, result file hygiene

## [v0.1.3] - 2025-08-25

- ci(release): use PR_TOKEN and set committer for changelog PR (d7b5dd2) by Kresna Sucandra
