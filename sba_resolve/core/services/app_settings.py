"""
============================================================
SBA AI Studio
App Settings Loader
ML-019-001
Version : 1.4.0
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
    load_ai_provider() -> str
    load_groq_api_key() -> str
    load_groq_model() -> str
    load_intelliscript_guidance() -> str
    load_openrouteservice_api_key() -> str
    load_exiftool_path() -> str
    load_resolve_module_path() -> str
    load_theme() -> str
    save_settings(updates: dict) -> None

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
GoPro-to-GoPro control.

To use a different Ollama model for YouTube metadata generation
than the default ("llama3.2"), set:

    {
        "ollama_model": "llama3.1:8b"
    }

Version 1.2.0 added save_settings() - a generic write-back
helper used by the Settings dialog (GUI-010).

Version 1.3.0 (2026-07-19, GUI-011) adds load_theme().

Version 1.4.0 (2026-07-19, PACKAGING) fixes DEFAULT_SETTINGS_PATH
for a PyInstaller-frozen build: the old __file__-based lookup
(Path(__file__).resolve().parents[3]) resolves inside a
temporary extraction folder once bundled into an .exe, not the
real install location - settings would either fail to persist or
get written somewhere useless. When frozen (sys.frozen is True,
set by PyInstaller at runtime), config/settings.json now resolves
relative to the directory containing the actual .exe
(Path(sys.executable).resolve().parent) instead. Running from
source (sys.frozen unset) is completely unaffected - same
parents[3]-based path as before.

Version 1.4.0 also adds load_ai_provider() / load_groq_api_key() /
load_groq_model() (Groq provider backlog item),
load_intelliscript_guidance() (editable prompt request,
2026-07-20), and load_openrouteservice_api_key() (real
road-following map routing, 2026-07-21) - the ORS key is never
logged or printed anywhere it's read.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from sba_resolve.core.models.gap_compression_settings import (
    GapCompressionSettings,
)


def _default_settings_path() -> Path:
    """
    Resolves config/settings.json's location. When running as a
    PyInstaller-frozen .exe, this is next to the real executable
    (so settings persist across runs and are easy for the user to
    find/edit). When running from source, this is the project
    root's config/ folder, exactly as before (three levels up
    from this file's real location: sba_resolve/core/services/).
    """

    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "config" / "settings.json"

    return (
        Path(__file__).resolve().parents[3] / "config" / "settings.json"
    )


# config/settings.json - see _default_settings_path() for how
# this resolves differently between a frozen .exe and running
# from source.
DEFAULT_SETTINGS_PATH = _default_settings_path()


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
    OFF, not ON.
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


def load_ai_provider(path: Path | None = None) -> str:
    """
    Reads "ai_provider" from config/settings.json.

    Returns "ollama" (the original, only-ever behaviour before this
    setting existed) if the file is missing, isn't valid JSON,
    doesn't contain that key, or the value isn't "ollama" or "groq" -
    this never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_provider = "ollama"

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_provider

    value = raw.get("ai_provider", default_provider)

    if value not in ("ollama", "groq"):
        return default_provider

    return value


def load_groq_api_key(path: Path | None = None) -> str:
    """
    Reads "groq_api_key" from config/settings.json. Returns "" (no
    key set) if the file is missing, isn't valid JSON, doesn't
    contain that key, or the value isn't a string - this never
    raises. Never logged or printed anywhere this value is read.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    value = raw.get("groq_api_key", "")

    if not isinstance(value, str):
        return ""

    return value


def load_groq_model(path: Path | None = None) -> str:
    """
    Reads "groq_model" from config/settings.json.

    Returns "llama-3.3-70b-versatile" (Groq's general-purpose default
    model) if the file is missing, isn't valid JSON, doesn't contain
    that key, or the value isn't a non-empty string - this never
    raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_model = "llama-3.3-70b-versatile"

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_model

    value = raw.get("groq_model", default_model)

    if not isinstance(value, str) or not value.strip():
        return default_model

    return value


DEFAULT_INTELLISCRIPT_GUIDANCE = """Act as an expert video editor working on a motorcycle vlog.

Below is a numbered list of transcript segments, in original
spoken order. For EACH segment, decide whether to KEEP or CUT it,
and whether it starts a new paragraph (topic/beat change).

Guidelines:
- Cut dead air, stuttering, and repetitive filler.
- Cut rambling, confusing, or unfinished asides that don't add
  anything to the story.
- Cut meta-commentary about the video itself (e.g. the speaker
  talking about what they've just been talking about).
- Keep the core storyline and message engaging.
- Group consecutive KEPT segments into paragraphs by topic - set
  paragraph_break_before true whenever a segment starts a new
  topic or beat, false if it continues the same paragraph as the
  previous kept segment.

CRITICAL: you are ONLY deciding keep/cut and paragraph grouping.
Do not rewrite, reword, correct, or paraphrase anything - you
have no ability to supply replacement text, and any text you
included in your response would be ignored. The exact original
words are reassembled automatically from your keep/cut decisions."""


def load_intelliscript_guidance(path: Path | None = None) -> str:
    """
    Reads "intelliscript_prompt_guidance" from config/settings.json -
    the editorial instructions portion of IntelliScriptEditor's
    prompt (what counts as filler/rambling/meta-commentary, how to
    group paragraphs). Deliberately does NOT cover the mechanical
    parts of the prompt (the segment list itself, or the JSON
    response-format instructions) - those stay fixed in
    intelliscript_editor.py, since a broken JSON-format instruction
    would break parsing regardless of what Gary intended.

    Returns DEFAULT_INTELLISCRIPT_GUIDANCE (the original, only-ever
    wording before this was editable) if the file is missing, isn't
    valid JSON, doesn't contain that key, or the value isn't a
    non-empty string - this never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_INTELLISCRIPT_GUIDANCE

    value = raw.get(
        "intelliscript_prompt_guidance", DEFAULT_INTELLISCRIPT_GUIDANCE
    )

    if not isinstance(value, str) or not value.strip():
        return DEFAULT_INTELLISCRIPT_GUIDANCE

    return value


def load_openrouteservice_api_key(path: Path | None = None) -> str:
    """
    Reads "openrouteservice_api_key" from config/settings.json.
    Returns "" (no key set - MapWidget falls back to the original
    straight pin-to-pin lines) if the file is missing, isn't valid
    JSON, doesn't contain that key, or the value isn't a string -
    this never raises. Never logged or printed anywhere this value
    is read.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    value = raw.get("openrouteservice_api_key", "")

    if not isinstance(value, str):
        return ""

    return value


def load_exiftool_path(path: Path | None = None) -> str:
    """
    Reads "exiftool" from config/settings.json. Returns "" (an
    unset path) if the file is missing, isn't valid JSON, doesn't
    contain that key, or the value isn't a string - this never
    raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    value = raw.get("exiftool", "")

    if not isinstance(value, str):
        return ""

    return value


def load_resolve_module_path(path: Path | None = None) -> str:
    """
    Reads "resolve_module_path" from config/settings.json.
    Returns "" (unset - falls back to auto-detection elsewhere)
    if the file is missing, isn't valid JSON, doesn't contain
    that key, or the value isn't a string - this never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    value = raw.get("resolve_module_path", "")

    if not isinstance(value, str):
        return ""

    return value


def load_theme(path: Path | None = None) -> str:
    """
    Reads "theme" from config/settings.json. Returns "dark" if
    the file is missing, isn't valid JSON, doesn't contain that
    key, or the value isn't the string "dark" or "light" - this
    never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_theme = "dark"

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_theme

    value = raw.get("theme", default_theme)

    if value not in ("dark", "light"):
        return default_theme

    return value


def save_settings(updates: dict, path: Path | None = None) -> None:
    """
    Merges `updates` into config/settings.json and writes it
    back, preserving every existing key not present in `updates`
    (e.g. recent_folder, recent_projects) - never overwrites the
    whole file blindly. Creates config/settings.json (and its
    parent folder) if it doesn't exist yet, or if the existing
    file isn't valid JSON (a corrupt settings file is replaced
    with a fresh one built from `updates` plus defaults, rather
    than blocking the person from ever saving settings again).

    `updates` uses the same shape as config/settings.json itself -
    top-level keys are merged directly; a nested dict value (e.g.
    "gap_compression") REPLACES the existing nested dict entirely,
    it isn't deep-merged, so callers should always pass every field
    of a nested section together.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raw = {}
    except (OSError, json.JSONDecodeError):
        raw = {}

    raw.update(updates)

    settings_path.parent.mkdir(parents=True, exist_ok=True)

    settings_path.write_text(
        json.dumps(raw, indent=4), encoding="utf-8"
    )