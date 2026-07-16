"""
============================================================
SBA AI Studio
Location Group
Version : 1.0.0
Sprint  : ML-038
============================================================

One place-based grouping of media clips, produced by
LocationGrouper. Mirrors RideDay's shape (index/clips/duration-
style properties) for consistency with the existing day-based
grouping.
"""

from __future__ import annotations

from dataclasses import dataclass, field

UNKNOWN_LOCATION = "Unknown Location"


@dataclass
class LocationGroup:
    """
    All clips reverse-geocoded to the same place name (or to
    UNKNOWN_LOCATION, for clips with no GPS data or an
    unresolvable lookup).
    """

    place_name: str

    clips: list = field(default_factory=list)

    @property
    def clip_count(self) -> int:
        return len(self.clips)

    @property
    def is_unknown(self) -> bool:
        return self.place_name == UNKNOWN_LOCATION
