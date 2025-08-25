# Contributing to Hector

Thanks for your interest in contributing! This project curates open‑source healthtech tools to help the community. Please read this guide before opening an issue or PR.

## Getting Started
- Fork the repo and create a feature branch: `git checkout -b feature/your-idea`.
- Install Python (3.10+ recommended) and dependencies from `requirements.txt`.
- Configure `config.yaml` and run locally with `python scan_and_curate.py`.
- Run tests: `pytest -q`.

## Pull Requests
- Keep PRs focused and small. Include before/after examples if changing output.
- Add tests for new logic where possible.
- Update `README.md` and docs if behavior changes.
- Follow conventional commits (feat:, fix:, docs:, chore:, test:, refactor:).

## Code Style
- Python: PEP8; type hints preferred.
- Logging over prints.
- No secrets in code. Use `.env.example` and GitHub Secrets.

## Security
- Report vulnerabilities privately (see `SECURITY.md`).

## Community Standards
- Please be respectful and constructive in issues and PRs.

## License
- By contributing, you agree that your contributions are licensed under the MIT License.
