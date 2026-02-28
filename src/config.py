"""
Load and validate the tax-organizer configuration.
"""

import json
import os
import sys
from typing import Any

CONFIG_PATHS = [
    os.path.join(os.path.dirname(__file__), "..", "config", "config.json"),
    os.path.join(os.path.dirname(__file__), "..", "config", "config.example.json"),
]


def load_config() -> dict[str, Any]:
    """
    Load config from config/config.json, falling back to config.example.json.

    Returns:
        Parsed configuration dict with taxYear and categories.
    """
    for path in CONFIG_PATHS:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            with open(abs_path, "r") as f:
                config = json.load(f)
            _validate(config, abs_path)
            return config

    print("ERROR: No config file found.")
    print("  Copy config/config.example.json → config/config.json")
    print("  and edit folder paths to match your OneDrive structure.")
    sys.exit(1)


def _validate(config: dict, path: str) -> None:
    """Basic validation of required config fields."""
    if "taxYear" not in config:
        raise ValueError(f"Config {path} missing 'taxYear'")
    if "categories" not in config or not isinstance(config["categories"], list):
        raise ValueError(f"Config {path} missing 'categories' array")
    for i, cat in enumerate(config["categories"]):
        for field in ("id", "name", "folders"):
            if field not in cat:
                raise ValueError(f"Category #{i} missing '{field}' in {path}")
