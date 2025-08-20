from pathlib import Path

from hector.renderer import render_markdown


def test_render_markdown_includes_metrics(tmp_path: Path):
    items = [
        {
            "name": "owner/repo",
            "url": "https://github.com/owner/repo",
            "score": 42.5,
            "description": "Test repo",
            "categories": ["Telemedicine"],
            "license": "MIT",
            "stars": 100,
            "forks": 10,
            "prs_open": 3,
            "has_discussions": True,
            "contributors_count": 7,
            "days_since_push": 5,
        }
    ]
    out = tmp_path / "out.md"
    render_markdown(items, str(out), ["Telemedicine"])  # categories order respected
    text = out.read_text()
    assert "PRs open: 3" in text
    assert "Discussions: Yes" in text
    assert "Contributors: 7" in text
    assert "Last push: 5 days ago" in text
