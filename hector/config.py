import os
from typing import Any, Dict

import yaml

REQUIRED_TOP_LEVEL_KEYS = ["search", "weights", "output"]


def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Load YAML config, inject env overrides, and validate."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}

    # Inject environment variables (e.g., GitHub token)
    token = os.getenv("GITHUB_TOKEN")
    cfg.setdefault("auth", {})
    if token:
        cfg["auth"]["GITHUB_TOKEN"] = token

    validate_config(cfg)
    return cfg


def validate_config(cfg: Dict[str, Any]) -> None:
    missing = [k for k in REQUIRED_TOP_LEVEL_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing required top-level keys in config: {missing}")

    # Minimal field checks
    search = cfg.get("search", {})
    if not isinstance(search, dict):
        raise ValueError("'search' must be a mapping")

    weights = cfg.get("weights", {})
    if not isinstance(weights, dict):
        raise ValueError("'weights' must be a mapping")

    output = cfg.get("output", {})
    if not isinstance(output, dict) or not output.get("file"):
        raise ValueError("'output.file' must be provided")
