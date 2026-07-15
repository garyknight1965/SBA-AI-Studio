"""
============================================================
SBA AI Studio
App Settings Loader
ML-019-001
Version : 1.0.0 Alpha
============================================================

Loads user-configurable app settings from config/settings.json,
falling back to safe defaults if the file is missing, malformed,
or doesn't contain a given section - a bad or absent config file
never crashes the app, it just runs with defaults.

Currently exposes:

    load_gap_compression_settings() -> GapCompressionSettings

To turn Gap Compression on, edit config/settings.json:

    {
        "gap_compression": {
            "enabled": true,
            "gap_threshold_seconds": 60,
            "compressed_gap_seconds": 2
        }
    }

Gap Compression is OFF by default (both here and in
GapCompressionSettings itself), so an untouched settings.json
reproduces the original, fully gap-preserving placement
behaviour exactly.
"""

from __future__ import annotations

import json
from pathlib import Path

from sba_resolve.core.models.gap_compression_settings import (
    GapCompressionSettings,
)

# config/settings.json, relative to the project root. This file
# lives at sba_resolve/core/services/, so the project root is
# three levels up.
DEFAULT_SETTINGS_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "settings.json"
)


def load_gap_compression_settings(
    path: Path | None = None,
) -> GapCompressionSettings:
    """
    Reads the "gap_compression" section of config/settings.json
    and returns a GapCompressionSettings built from it.

    Returns GapCompressionSettings() (disabled, default
    thresholds) if the file is missing, isn't valid JSON, doesn't
    contain a "gap_compression" section, or that section has
    invalid values - this never raises, so a typo in the config
    file can't crash a Resolve import.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return GapCompressionSettings()

    section = raw.get("gap_compression")

    if not isinstance(section, dict):
        return GapCompressionSettings()

    try:
        return GapCompressionSettings(
            enabled=bool(section.get("enabled", False)),
            gap_threshold_seconds=float(
                section.get("gap_threshold_seconds", 60.0)
            ),
            compressed_gap_seconds=float(
                section.get("compressed_gap_seconds", 2.0)
            ),
        )
    except (TypeError, ValueError):
        return GapCompressionSettings()
