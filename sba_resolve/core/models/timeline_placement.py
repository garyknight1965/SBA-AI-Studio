"""
============================================================
SBA AI Studio
Timeline Placement
ML-011-002
Version : 1.0.0 Alpha
============================================================

Represents the planned placement of a MediaFile on a
timeline.

This model is produced by the Planning Engine and later
consumed by the Resolve Timeline Builder.

It intentionally contains no Resolve API code.
"""

from __future__ import annotations

from dataclasses import dataclass

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class TimelinePlacement:
    """
    Represents a single planned clip placement.

    The Planning Engine determines where each clip belongs
    on the timeline. The Resolve Timeline Builder later uses
    this information to place the clip using Resolve's
    recordFrame functionality.
    """

    media_file: MediaFile

    ride_day: int = 1

    track_index: int = 1

    record_frame: int = 0

    duration_frames: int = 0

    camera_name: str = ""

    clip_name: str = ""

    @property
    def end_frame(self) -> int:
        """Return the final frame occupied by this clip."""
        return self.record_frame + self.duration_frames

    @property
    def has_duration(self) -> bool:
        """True if the clip has a valid duration."""
        return self.duration_frames > 0

    def summary(self) -> dict:
        """Return a serialisable summary."""
        return {
            "clip": self.clip_name or self.media_file.filename,
            "camera": self.camera_name or self.media_file.camera_display_name,
            "ride_day": self.ride_day,
            "track": self.track_index,
            "record_frame": self.record_frame,
            "duration_frames": self.duration_frames,
            "end_frame": self.end_frame,
        }

    def __str__(self) -> str:
        return (
            f"{self.media_file.filename} | "
            f"Track {self.track_index} | "
            f"Frame {self.record_frame}"
        )

    __repr__ = __str__