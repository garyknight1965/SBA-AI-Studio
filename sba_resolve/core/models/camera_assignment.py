"""
============================================================
SBA AI Studio
Camera Assignment
CORE-011B
Version : 1.0.0 Alpha
============================================================

Defines how a camera is used within a project.

CameraProfile describes WHAT the camera is.

CameraAssignment describes HOW this project uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from sba_resolve.core.models.camera_profile import CameraProfile


class CameraRole(str, Enum):
    UNKNOWN = "Unknown"

    PRIMARY = "Primary Camera"

    SECONDARY = "Secondary Camera"

    CAMERA360 = "360 Camera"

    DRONE = "Drone"

    BROLL = "B-Roll"

    AUDIO = "Audio Recorder"


@dataclass(slots=True)
class CameraAssignment:
    """
    Project-specific camera configuration.

    This object intentionally contains no camera
    identification logic.

    Camera identity is provided by CameraProfile.

    CameraAssignment simply defines how the camera
    should be treated inside this project.
    """

    profile: CameraProfile

    role: CameraRole = CameraRole.UNKNOWN

    transcript_source: bool = False

    preferred_audio_source: bool = False

    enabled: bool = True

    timeline_track: int = 1

    track_name: str = ""

    track_colour: str = ""

    @property
    def display_name(self) -> str:

        return self.profile.display_name

    @property
    def manufacturer(self) -> str:

        return self.profile.manufacturer.value

    @property
    def is_primary(self) -> bool:

        return self.role == CameraRole.PRIMARY

    @property
    def is_secondary(self) -> bool:

        return self.role == CameraRole.SECONDARY

    @property
    def is_drone(self) -> bool:

        return self.role == CameraRole.DRONE

    @property
    def is_360(self) -> bool:

        return self.role == CameraRole.CAMERA360

    def summary(self) -> dict:

        return {
            "camera": self.display_name,
            "role": self.role.value,
            "enabled": self.enabled,
            "transcript_source": self.transcript_source,
            "preferred_audio_source": self.preferred_audio_source,
            "timeline_track": self.timeline_track,
            "track_name": self.track_name,
            "track_colour": self.track_colour,
        }

    def __str__(self) -> str:

        return (
            f"{self.display_name} -> "
            f"{self.role.value}"
        )

    __repr__ = __str__