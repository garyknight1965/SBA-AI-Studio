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
        }

    def __str__(self) -> str:
        return (
            f"{self.frame} | "
            f"{self.title}"
        )

    __repr__ = __str__