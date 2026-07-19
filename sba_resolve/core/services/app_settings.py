"""
============================================================
SBA AI Studio
App Settings Loader
ML-019-001
Version : 1.1.0
============================================================

Loads user-configurable app settings from config/settings.json,
falling back to safe defaults if the file is missing, malformed,
or doesn't contain a given section - a bad or absent config file
never crashes the app, it just runs with defaults.

Currently exposes:

    load_gap_compression_settings() -> GapCompressionSettings
    load_timeline_creation_enabled() -> bool
    load_multicam_audio_sync_enabled() -> bool
    load_ollama_model() -> str

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

To turn Resolve timeline creation off entirely (e.g. while
focusing on other work, without touching the placement/sync
code at all), set:

    {
        "enable_timeline_creation": false
    }

Timeline creation is ON by default (an absent or malformed key
reproduces the original, always-create-a-timeline behaviour).

To turn multicam audio sync verification ON (ML-054), set:

    {
        "enable_multicam_audio_sync": true
    }

Multicam audio sync is OFF by default (2026-07-19) - real-world
testing found the FFT band cross-correlation approach unreliable
across every real footage pair tested, including a same-brand
GoPro-to-GoPro control. With this OFF, multicam candidate clips
(other than the trusted HERO13 time-anchor) are never sent
through audio correlation at all - they go straight to a
placeholder track for manual sync in Resolve, with no ffmpeg/
audio work attempted. Flip this on later if a cleaner audio
setup makes the correlation approach worth trying again.

To use a different Ollama model for YouTube metadata generation
than the default ("llama3.2"), set:

    {
        "ollama_model": "llama3.1:8b"
    }
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


def load_timeline_creation_enabled(
    path: Path | None = None,
) -> bool:
    """
    Reads "enable_timeline_creation" from config/settings.json.

    Returns True (timeline creation ON, the original behaviour)
    if the file is missing, isn't valid JSON, doesn't contain
    that key, or the value isn't a plain bool - this never
    raises, so a typo in the config file can't silently disable
    timeline creation without the person realising why.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True

    value = raw.get("enable_timeline_creation", True)

    if not isinstance(value, bool):
        return True

    return value


def load_multicam_audio_sync_enabled(
    path: Path | None = None,
) -> bool:
    """
    Reads "enable_multicam_audio_sync" from config/settings.json.

    Returns False (audio sync OFF, the current default per
    Gary's 2026-07-19 decision) if the file is missing, isn't
    valid JSON, doesn't contain that key, or the value isn't a
    plain bool - this never raises. Unlike
    load_timeline_creation_enabled(), the safe default here is
    OFF, not ON: real-world testing found the correlation
    approach unreliable, so an absent/malformed key must not
    silently turn on a feature that risks wasted processing time
    with no real chance of succeeding.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    value = raw.get("enable_multicam_audio_sync", False)

    if not isinstance(value, bool):
        return False

    return value


def load_ollama_model(path: Path | None = None) -> str:
    """
    Reads "ollama_model" from config/settings.json.

    Returns "llama3.2" (a small, widely-available default model)
    if the file is missing, isn't valid JSON, doesn't contain
    that key, or the value isn't a non-empty string - this never
    raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_model = "llama3.2"

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_model

    value = raw.get("ollama_model", default_model)

    if not isinstance(value, str) or not value.strip():
        return default_model

    return value