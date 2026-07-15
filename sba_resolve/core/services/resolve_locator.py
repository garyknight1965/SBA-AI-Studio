"""
============================================================
SBA AI Studio
Resolve Module Locator
ML-021-001
Version : 1.0.0 Alpha
============================================================

Locates DaVinci Resolve's scripting module and puts it on
sys.path, so `import DaVinciResolveScript` works without
requiring PYTHONPATH/environment variables to already be set up
system-wide, outside this project, before running SBA AI Studio.

Resolution order:
    1. Already importable - nothing to do.
    2. Blackmagic's own documented env var (RESOLVE_SCRIPT_API) -
       DaVinciResolveScript.py lives in "<that>/Modules".
    3. "resolve_module_path" in config/settings.json, if set.
    4. Common default install locations, per OS.

Raises a clear, actionable RuntimeError (naming everywhere that
was checked, and how to fix it) if none of these work, instead
of a bare ModuleNotFoundError surfacing from deep inside
DaVinciResolveScript's own import machinery.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import sys
from pathlib import Path
from typing import Iterator

# config/settings.json, relative to the project root. This file
# lives at sba_resolve/core/services/, so the project root is
# three levels up.
DEFAULT_SETTINGS_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "settings.json"
)

# Common default install locations, per OS - Blackmagic's own
# documented locations for a standard DaVinci Resolve install.
DEFAULT_CANDIDATES: dict[str, list[str]] = {
    "Windows": [
        r"C:\ProgramData\Blackmagic Design\DaVinci Resolve"
        r"\Support\Developer\Scripting\Modules",
    ],
    "Darwin": [
        "/Library/Application Support/Blackmagic Design/"
        "DaVinci Resolve/Developer/Scripting/Modules",
    ],
    "Linux": [
        "/opt/resolve/Developer/Scripting/Modules",
        "/home/resolve/Developer/Scripting/Modules",
    ],
}


def ensure_resolve_module_importable() -> str | None:
    """
    Makes sure `import DaVinciResolveScript` will work, adding
    its containing folder to sys.path if needed.

    Returns the path that was added to sys.path (for logging), or
    None if the module was already importable with no changes
    needed.

    Raises RuntimeError, listing everywhere that was checked and
    what to do next, if the module can't be found anywhere.
    """

    if importlib.util.find_spec("DaVinciResolveScript") is not None:
        return None

    checked: list[str] = []

    for candidate in _candidates():

        if not candidate:
            continue

        checked.append(candidate)

        if not Path(candidate).exists():
            continue

        if candidate not in sys.path:
            sys.path.insert(0, candidate)

        if importlib.util.find_spec("DaVinciResolveScript") is not None:
            return candidate

        # Existed on disk but didn't actually contain the module -
        # don't leave it cluttering sys.path.
        sys.path.remove(candidate)

    raise RuntimeError(
        "Could not locate DaVinci Resolve's scripting module "
        "(DaVinciResolveScript.py).\n"
        "Checked:\n"
        + "\n".join(f"  - {c}" for c in checked)
        + "\n\n"
        "To fix this, either:\n"
        "  1. Set the RESOLVE_SCRIPT_API environment variable to "
        "your Resolve Scripting folder (Blackmagic's documented "
        "setup), or\n"
        '  2. Set "resolve_module_path" in config/settings.json '
        "to the folder containing DaVinciResolveScript.py."
    )


def _candidates() -> Iterator[str | None]:

    api = os.environ.get("RESOLVE_SCRIPT_API")

    if api:
        yield str(Path(api) / "Modules")

    yield _settings_path()

    for path in DEFAULT_CANDIDATES.get(platform.system(), []):
        yield path


def _settings_path() -> str | None:
    """
    Reads "resolve_module_path" from config/settings.json.
    Returns None if the file is missing, malformed, or doesn't
    have that key - never raises.
    """

    try:
        raw = json.loads(
            DEFAULT_SETTINGS_PATH.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError):
        return None

    value = raw.get("resolve_module_path")

    return value or None
