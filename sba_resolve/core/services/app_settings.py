"""
============================================================
SBA AI Studio
App Settings Loader
ML-019-001
Version : 1.7.0
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
    load_ollama_fallback_model() -> str
    load_ai_provider() -> str
    load_groq_api_key() -> str
    load_groq_model() -> str
    load_intelliscript_guidance() -> str
    load_youtube_metadata_guidance() -> str
    load_openrouteservice_api_key() -> str
    load_camera_luts() -> dict[str, str]
    load_exiftool_path() -> str
    load_thumbnail_logo_path() -> str
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

Version 1.5.0 (2026-07-23, ML-058 v2) adds
load_youtube_metadata_guidance() - Gary wasn't happy with the
generated YouTube description quality and wanted (a) a natural,
in-flow mention that the video was edited with SBA AI Studio and
DaVinci Resolve rather than a bolted-on fixed line, and (b) the
ability to tune the brand-voice/style instructions himself, the
same way IntelliScript's prompt guidance already works. This
replaces the previously-hardcoded BRAND_VOICE_GUIDANCE constant in
youtube_metadata_generator.py and the short-lived, deterministically
-appended EDITOR_CREDIT line it briefly had - both approaches are
gone now that the guidance itself is editable and instructs the
model to weave the editing credit in naturally.

Version 1.6.0 (2026-07-24, ML-071) adds
load_ollama_fallback_model() - after switching to qwen3.6 on
Gary's 8GB-VRAM AMD card, generation is noticeably slower (heavy
CPU offload) and occasionally risks timing out on a long
IntelliScript prompt. OllamaClient now retries automatically with
a fallback model if the primary model times out (see ML-071 in
ollama_client.py). Defaults to "llama3.2" (small, fast, already
proven reliable in this app) if unset. To disable the fallback
entirely, set it to an empty string:

    {
        "ollama_fallback_model": ""
    }

Version 1.7.0 (2026-07-24, ML-072) adds load_camera_luts() - a
per-camera-manufacturer "Input LUT" mapping applied automatically
to Media Pool clips during timeline creation (see
_apply_camera_luts() in create_timeline.py). GoPro/DJI/Insta360
footage in this project is imported into Resolve but NOT
auto-placed onto any timeline - Gary drags it in manually later -
so the LUT is set on the Media Pool clip itself (via
MediaPoolItem.SetClipProperty("Input LUT", ...)), not via
TimelineItem.SetLUT() (which only works once a clip is already
sitting on a timeline). Set like:

    {
        "camera_luts": {
            "GoPro": "GoPro/HERO13_Flat_to_Rec709.cube",
            "DJI": "DJI/DJI_Flat_Look.cube",
            "Insta360": "Insta360/X3_FlatColor_Look.cube"
        }
    }

Each value must be the LUT exactly as it appears in Resolve's own
LUT browser/dropdown (Project Settings > Color Management >
Lookup Tables) - the LUT file has to already be installed under
Resolve's recognized LUT folder for the reference to mean
anything; SetClipProperty() can return True even for a value
Resolve doesn't actually recognize, so a successful write doesn't
guarantee the grade visibly changed. A manufacturer with no entry
(or omitted "camera_luts" entirely) is left untouched - this is
opt-in per camera, matching CameraManufacturer's values exactly
("GoPro", "DJI", "Insta360", "Sony", "Canon").
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


def load_ollama_fallback_model(path: Path | None = None) -> str:
    """
    Reads "ollama_fallback_model" from config/settings.json - the
    model OllamaClient automatically retries with if the primary
    model (load_ollama_model()) times out (ML-071).

    Returns "llama3.2" if the file is missing, isn't valid JSON,
    or the key isn't present at all - this never raises.

    Unlike most loaders in this module, an explicit empty string
    IS a valid, meaningful value here (it means "no fallback,
    disable this feature") - so this deliberately does NOT fall
    back to the default just because the value is "". Only a
    missing key, missing file, bad JSON, or a non-string value
    triggers the "llama3.2" default.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_fallback = "llama3.2"

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default_fallback

    if "ollama_fallback_model" not in raw:
        return default_fallback

    value = raw["ollama_fallback_model"]

    if not isinstance(value, str):
        return default_fallback

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

    Returns "openai/gpt-oss-120b" (Groq's general-purpose default
    model) if the file is missing, isn't valid JSON, doesn't contain
    that key, or the value isn't a non-empty string - this never
    raises.

    Note: the default was "llama-3.3-70b-versatile" until 2026-07-23,
    when it was changed here because Groq deprecated that model
    (shutdown date 08/16/26). openai/gpt-oss-120b was chosen over the
    other Groq-recommended replacement, qwen/qwen3.6-27b, because
    Qwen 3.6 27B is a reasoning/thinking model whose JSON output can
    end up in its internal reasoning stream instead of the final
    response, which caused real "Failed to validate JSON" errors
    against this app's structured-output prompts (IntelliScript,
    YouTube metadata). gpt-oss-120b does not have that failure mode.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    default_model = "openai/gpt-oss-120b"

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


DEFAULT_YOUTUBE_METADATA_GUIDANCE = """Act as a professional YouTube SEO expert and content strategist
for the "Scottish Biker Abroad" channel - European motorcycle
touring, gear reviews, and ride vlogs.

Tone: irreverent British humour, self-aware about motorcycle
culture (don't take the "adventure biker" persona too
seriously), but genuinely informative for riders planning
similar trips.

Titles: give 5 distinct, highly clickable options, each under 70
characters. SEO-focused and specific rather than vague - name the
actual place/route/landmark instead of generic phrases like
"epic ride" or "amazing day". If the ride touches WWII history
sites, castles, or other tourism crossover angles, that's worth
naming directly - those searches perform well for this channel.

Description structure:
1. Start with a compelling hook (first 2 lines must work even if
   YouTube truncates them).
2. Clearly explain what the video is about.
3. Naturally weave in every place name given below - don't just
   list them once, work them into the story of the ride (what was
   passed through, what was stopped at, roughly what the route
   covered). Include roughly how long/how many days the ride was,
   and the cameras used if that's relevant to a gear-curious
   audience.
4. Naturally mention, somewhere in the flow (not as an isolated,
   bolted-on final sentence), that the video was edited with the
   help of a custom-built app called SBA AI Studio, alongside
   DaVinci Resolve. Phrase it however fits the surrounding tone -
   it should read like a real line the channel owner would write,
   not a disclaimer stuck on the end.
5. Include a call to action asking viewers to Like, Comment,
   Share, and Subscribe.
6. End with 10-15 relevant hashtags.

Tags/keywords: 15 SEO tags relevant to the ride, channel, and
motorcycle-touring niche.

Filename suggestion: a short, descriptive, filesystem-safe
filename for the final video export (no spaces, use hyphens).

Pinned comment: a short comment (1-3 sentences) the channel owner
could pin to boost engagement - a question or prompt that invites
replies.

Thumbnail text: 3-6 words suitable for overlaying on the video
thumbnail."""


def load_youtube_metadata_guidance(path: Path | None = None) -> str:
    """
    Reads "youtube_metadata_prompt_guidance" from
    config/settings.json - the brand-voice/style instructions
    portion of YouTubeMetadataGenerator's prompt (channel tone,
    title/description style, and the editing-credit mention).
    Deliberately does NOT cover the mechanical parts of the prompt
    (the day-by-day facts, the anti-hallucination rules, or the
    JSON response-format instructions) - those stay fixed in
    youtube_metadata_generator.py, since loosening those could let
    the model invent facts or break parsing regardless of what
    Gary intended to change.

    Returns DEFAULT_YOUTUBE_METADATA_GUIDANCE (the original,
    only-ever wording before this was editable) if the file is
    missing, isn't valid JSON, doesn't contain that key, or the
    value isn't a non-empty string - this never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return DEFAULT_YOUTUBE_METADATA_GUIDANCE

    value = raw.get(
        "youtube_metadata_prompt_guidance",
        DEFAULT_YOUTUBE_METADATA_GUIDANCE,
    )

    if not isinstance(value, str) or not value.strip():
        return DEFAULT_YOUTUBE_METADATA_GUIDANCE

    return value


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


def load_camera_luts(path: Path | None = None) -> dict[str, str]:
    """
    Reads "camera_luts" from config/settings.json - a per-camera-
    manufacturer "Input LUT" mapping (ML-072), applied to Media
    Pool clips during timeline creation (see _apply_camera_luts()
    in create_timeline.py).

    Returns {} (no LUTs configured - clips are left untouched, the
    original behaviour before this setting existed) if the file is
    missing, isn't valid JSON, doesn't contain that key, or the
    value isn't a dict - this never raises.

    Each entry is validated individually rather than all-or-
    nothing: a non-string key or value in the dict is silently
    skipped rather than invalidating every other, correctly-typed
    entry - a single typo in one camera's LUT shouldn't disable
    LUT assignment for every other camera too.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    value = raw.get("camera_luts", {})

    if not isinstance(value, dict):
        return {}

    return {
        str(manufacturer): str(lut_reference)
        for manufacturer, lut_reference in value.items()
        if isinstance(manufacturer, str)
        and isinstance(lut_reference, str)
        and lut_reference.strip()
    }

    return value


def load_thumbnail_logo_path(path: Path | None = None) -> str:
    """
    Reads "thumbnail_logo_path" from config/settings.json - the
    channel logo image composited onto the bottom-right corner of
    generated thumbnails (ML-061). Returns "" (no logo configured)
    if the file is missing, isn't valid JSON, doesn't contain that
    key, or the value isn't a string - this never raises.
    """

    settings_path = path or DEFAULT_SETTINGS_PATH

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""

    value = raw.get("thumbnail_logo_path", "")

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
