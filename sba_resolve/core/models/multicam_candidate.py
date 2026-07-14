"""
============================================================
SBA AI Studio
Multicam Candidate
ML-011-006
Version : 1.0.0 Alpha
============================================================

Represents a potential multicam group discovered during
Ride Reconstruction.

The Planning Engine determines candidates.

The Resolve Timeline Builder later decides how they
are used.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sba_resolve.core.models.media_file import MediaFile


@dataclass(slots=True)
class MulticamCandidate:
    """
    Represents one multicam opportunity.
    """

    start_frame: int = 0

    end_frame: int = 0

    confidence: float = 0.0

    clips: list[MediaFile] = field(default_factory=list)

    reason: str = ""

    approved: bool = False

    @property
    def duration_frames(self) -> int:
        return max(0, self.end_frame - self.start_frame)

    @property
    def camera_names(self) -> list[str]:
        """
        Return the distinct camera names represented in this
        candidate's clips, alphabetically sorted.
        """

        names = {
            getattr(media, "camera_display_name", None)
            or getattr(media, "camera_model", None)
            or "Unknown"
            for media in self.clips
        }

        return sorted(names)

    @property
    def camera_count(self) -> int:
        """
        Number of distinct cameras represented, not the number
        of clips (a single camera can contribute more than one
        clip to the same overlap window).
        """
        return len(self.camera_names)

    @property
    def is_valid(self) -> bool:
        return self.camera_count >= 2

    def add_clip(self, media: MediaFile) -> None:
        if media not in self.clips:
            self.clips.append(media)

    def summary(self) -> dict:
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "duration_frames": self.duration_frames,
            "camera_count": self.camera_count,
            "confidence": self.confidence,
            "reason": self.reason,
            "approved": self.approved,
        }

    def __str__(self) -> str:
        return (
            f"{self.camera_count} camera(s) | "
            f"{self.confidence:.0%} confidence"
        )

    __repr__ = __str__