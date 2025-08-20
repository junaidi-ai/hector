from pathlib import Path

import pytest

from hector.config import load_config


def test_load_config_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "\n".join(
            [
                "search:",
                "  query: test",
                "weights:",
                "  stars: 1",
                "output:",
                "  file: out.md",
                "",
            ]
        )
    )

    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token")
    cfg = load_config(str(cfg_path))

    assert cfg["search"]["query"] == "test"
    assert cfg["output"]["file"] == "out.md"
    assert cfg.get("auth", {}).get("GITHUB_TOKEN") == "dummy-token"
