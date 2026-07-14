"""
============================================================
SBA AI Studio
Planning Segment
ML-011-003
Version : 1.0.0 Alpha
============================================================

Represents a continuous section of a ride where the
set of available cameras remains unchanged.

The Planning Engine produces PlanningSegments during
Ride Reconstruction.

PlanningSegments are later consumed by:

    - Timeline Builder
    - Statistics Generator
    - Marker Generator
    - Multicam Detector
    - Transcript Engine
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class PlanningSegment:
    """
    One continuous ride segment.

    Example

        09:15 -> 09:24

        Hero13
        Hero8
        Insta360

    becomes one PlanningSegment.
    """

    ride_day: int = 1

    start_frame: int = 0

    end_frame: int = 0

    available_clips: list[MediaFile] = field(default_factory=list)

    transcript_available: bool = False

    multicam_candidate: bool = False

    marker_title: str = ""

    marker_description: str = ""

    @property
    def duration_frames(self) -> int:
        """Length of this planning segment."""
        return max(0, self.end_frame - self.start_frame)

    @property
    def camera_count(self) -> int:
        """Number of cameras available."""
        return len(self.available_clips)

    @property
    def has_multiple_cameras(self) -> bool:
        """True if more than one camera is available."""
        return self.camera_count > 1

    def add_clip(self, media: MediaFile) -> None:
        """Add a clip if it is not already present."""
        if media not in self.available_clips:
            self.available_clips.append(media)

    def summary(self) -> dict:
        """Return a serialisable summary."""
        return {
            "ride_day": self.ride_day,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "duration_frames": self.duration_frames,
            "camera_count": self.camera_count,
            "transcript_available": self.transcript_available,
            "multicam_candidate": self.multicam_candidate,
        }

    def __str__(self) -> str:
        return (
            f"Ride {self.ride_day} | "
            f"{self.start_frame}-{self.end_frame} | "
            f"{self.camera_count} camera(s)"
        )

    __repr__ = __str__