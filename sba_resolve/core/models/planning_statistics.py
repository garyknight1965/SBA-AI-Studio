"""
============================================================
SBA AI Studio
Planning Statistics
ML-011-005
Version : 1.0.0 Alpha
============================================================

Represents statistical information generated during
Ride Reconstruction.

This object is populated by StatisticsGenerator.

It intentionally contains no calculation logic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PlanningStatistics:
    """
    Stores Planning Engine statistics.
    """

    ride_days: int = 0

    scenes: int = 0

    total_clips: int = 0

    total_cameras: int = 0

    multicam_segments: int = 0

    transcript_segments: int = 0

    timeline_frames: int = 0

    timeline_duration_seconds: float = 0.0

    markers: int = 0

    @property
    def has_multicam(self) -> bool:
        return self.multicam_segments > 0

    @property
    def has_transcript(self) -> bool:
        return self.transcript_segments > 0

    def summary(self) -> dict:
        return {
            "ride_days": self.ride_days,
            "scenes": self.scenes,
            "total_clips": self.total_clips,
            "total_cameras": self.total_cameras,
            "multicam_segments": self.multicam_segments,
            "transcript_segments": self.transcript_segments,
            "timeline_frames": self.timeline_frames,
            "timeline_duration_seconds": self.timeline_duration_seconds,
            "markers": self.markers,
        }

    def __str__(self) -> str:
        return (
            f"Ride Days: {self.ride_days} | "
            f"Clips: {self.total_clips} | "
            f"Cameras: {self.total_cameras}"
        )

    __repr__ = __str__