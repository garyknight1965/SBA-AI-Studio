"""
============================================================
SBA AI Studio
Timeline FPS
ML-011-019
Version : 1.0.0 Alpha
============================================================

Single source of truth for the frame rate used to convert
real-world elapsed time into timeline frame numbers.

TimelinePlacementBuilder and MulticamDetector both need this
exact same rate - they operate in the same frame space, and if
they used independently-hardcoded constants they could silently
drift apart.

Known limitation (not fixed here): this is a fixed constant, not
read from the actual Resolve project's timeline frame rate. If a
project's real timeline runs at a different fps (confirmed via
tools/resolve_gap_placement_test.py that project frame rates can
differ, e.g. 24fps), frame-exact placement will drift slightly
from true real-time sync. Fixing that requires passing the
project's actual frame rate in from Resolve at build time.
"""

from __future__ import annotations

import re

DEFAULT_PROJECT_FPS = 25.0

_FPS_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


def parse_timeline_fps(raw) -> float | None:
    """
    Parse a Resolve Timeline.GetSetting("timelineFrameRate") value
    into a float.

    Handles:
    - Plain values: "24", "25", "23.976"
    - Drop-frame suffixes: "29.97 DF", "29.97DF"
    - None / empty / unparseable input -> returns None so the
      caller can decide on a fallback rather than silently using
      a wrong number.

    Does NOT work around the known regional bug where Resolve can
    return "23" instead of "23.976" on Windows systems using a
    comma decimal separator - there's no reliable way to detect
    that case from the string alone.
    """

    if raw is None:
        return None

    match = _FPS_PATTERN.search(str(raw))

    if not match:
        return None

    try:
        value = float(match.group())
    except ValueError:
        return None

    return value if value > 0 else None

