"""
============================================================
SBA AI Studio
Timeline Marker
ML-011-004
Version : 1.0.0 Alpha
============================================================

Represents a planning marker.

Timeline markers are generated during Ride Reconstruction
and later converted into Resolve timeline markers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class TimelineMarker:
    """
    Represents one marker on the reconstructed ride timeline.
    """

    frame: int = 0

    title: str = ""

    description: str = ""

    colour: str = "Blue"

    category: str = "General"

    generated: bool = True

    # Which ride day this marker belongs to. Populated by
    # TimelineMarkerGenerator. Used at the Resolve Builder
    # boundary (create_timeline.py) to group markers onto the
    # correct per-day timeline - not consumed by the Planning
    # Engine itself.
    ride_day: int = 0

    @property
    def has_description(self) -> bool:
        return bool(self.description.strip())

    def summary(self) -> dict:
        return {
            "frame": self.frame,
            "title": self.title,
            "description": self.description,
            "colour": self.colour,
            "category": self.category,
            "generated": self.generated,
            "ride_day": self.ride_day,
        }

    def __str__(self) -> str:
        return (
            f"{self.frame} | "
            f"{self.title}"
        )

    __repr__ = __str__