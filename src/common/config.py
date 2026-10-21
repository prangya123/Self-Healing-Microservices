"""Single entry point for loading config.yaml so every script sees the same values."""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_PATH = os.path.join(REPO_ROOT, "config.yaml")


@lru_cache(maxsize=1)
def load_config(path: str = CONFIG_PATH) -> dict[str, Any]:
    with open(path) as f:
        cfg = yaml.safe_load(f)
    return cfg


def resolve_path(relative_or_abs: str) -> str:
    """Resolve a config path (which may be relative to the repo root) to an absolute path."""
    if os.path.isabs(relative_or_abs):
        return relative_or_abs
    return os.path.abspath(os.path.join(REPO_ROOT, relative_or_abs))
