"""
============================================================
SBA AI Studio
Planning Segment
ML-011-012A
Version : 2.0.0 Alpha
============================================================

Represents a continuous section of a ride where the
set of available cameras remains unchanged.

PlanningSegments are produced by the Ride Reconstruction
Engine and later consumed by:

    - Timeline Placement Builder
    - Marker Generator
    - Statistics Generator
    - Multicam Detector
    - Resolve Timeline Builder
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class PlanningSegment:
    """
    Represents one continuous ride segment.

    A PlanningSegment describes a period where the set
    of active cameras remains constant.
    """

    ride_day: int = 1

    scene: int = 1

    start_frame: int = 0

    end_frame: int = 0

    available_clips: list[MediaFile] = field(default_factory=list)

    active_cameras: set[str] = field(default_factory=set)

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
        """Number of active cameras."""
        return len(self.active_cameras)

    @property
    def has_multiple_cameras(self) -> bool:
        """True if multiple cameras are active."""
        return self.camera_count > 1

    @property
    def camera_names(self) -> list[str]:
        """Return camera names in alphabetical order."""
        return sorted(self.active_cameras)

    def add_clip(self, media: MediaFile) -> None:
        """
        Add a MediaFile to the segment.
        """

        if media in self.available_clips:
            return

        self.available_clips.append(media)

        camera = (
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
        )

        self.active_cameras.add(camera)

        # Current project rule:
        # Hero13 with lav microphone is our transcript source.
        if "hero13" in camera.lower():
            self.transcript_available = True

    def summary(self) -> dict:
        """Return a serialisable summary."""

        return {
            "ride_day": self.ride_day,
            "scene": self.scene,
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "duration_frames": self.duration_frames,
            "camera_count": self.camera_count,
            "active_cameras": self.camera_names,
            "transcript_available": self.transcript_available,
            "multicam_candidate": self.multicam_candidate,
        }

    def __str__(self) -> str:
        cameras = ", ".join(self.camera_names) or "No Cameras"

        return (
            f"Ride {self.ride_day} Scene {self.scene} | "
            f"{self.start_frame}-{self.end_frame} | "
            f"{cameras}"
        )

    __repr__ = __str__