"""
============================================================
SBA AI Studio
Media File Domain Model
Version : 4.0.1
Sprint : ML-003
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from sba_resolve.core.models.camera_profile import CameraProfile


@dataclass(slots=True)
class MediaFile:
    """
    Represents one media asset inside SBA AI Studio.

    This object is the single source of truth used by:
        - Project Scanner
        - ExifTool
        - Metadata Mapper
        - Database
        - GUI
        - Resolve Import
        - Timeline Builder
    """

    # ------------------------------------------------------------------
    # File Information
    # ------------------------------------------------------------------

    filename: str
    full_path: Path
    relative_path: Path

    extension: str
    size: int

    # ------------------------------------------------------------------
    # Camera Information
    # ------------------------------------------------------------------

    camera_make: str = "Unknown"
    camera_model: str = "Unknown"

    # CORE-010 Camera Intelligence
    camera_profile: CameraProfile = field(default_factory=CameraProfile)

    lens: str = ""

    # ------------------------------------------------------------------
    # Video Information
    # ------------------------------------------------------------------

    width: int = 0
    height: int = 0

    fps: float = 0.0

    duration: str = ""

    codec: str = ""

    bitrate: int = 0

    rotation: int = 0

    # ------------------------------------------------------------------
    # Audio
    # ------------------------------------------------------------------

    audio_channels: int = 0

    sample_rate: int = 0

    # ------------------------------------------------------------------
    # GPS
    # ------------------------------------------------------------------

    gps_latitude: float | None = None
    gps_longitude: float | None = None

    # ------------------------------------------------------------------
    # Dates
    # ------------------------------------------------------------------

    created: datetime | None = None

    modified: datetime | None = None

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    category: str = "Unknown"

    tags: list[str] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Resolve
    # ------------------------------------------------------------------

    imported: bool = False

    verified: bool = False

    bin_name: str = ""

    # ------------------------------------------------------------------
    # AI
    # ------------------------------------------------------------------

    score: float = 0.0

    favorite: bool = False

    rejected: bool = False

    # ------------------------------------------------------------------
    # Integrity (ML-030 Corruption Detector / Project Database)
    # ------------------------------------------------------------------

    corrupted: bool = False

    corruption_reason: str = ""

    # ------------------------------------------------------------------
    # Timestamp Confidence (ML-031)
    # ------------------------------------------------------------------

    timestamp_source: str = ""

    timestamp_confidence: int = 0

    # ------------------------------------------------------------------
    # Convenience Properties
    # ------------------------------------------------------------------

    @property
    def resolution(self) -> str:
        return f"{self.width}x{self.height}"

    @property
    def megapixels(self) -> float:
        return round((self.width * self.height) / 1_000_000, 2)

    @property
    def is_video(self) -> bool:
        return self.extension.lower() in {
            ".mp4",
            ".mov",
            ".avi",
            ".mxf",
            ".braw",
        }

    @property
    def is_audio(self) -> bool:
        return self.extension.lower() in {
            ".wav",
            ".mp3",
            ".m4a",
            ".aac",
            ".flac",
        }

    @property
    def is_image(self) -> bool:
        return self.extension.lower() in {
            ".jpg",
            ".jpeg",
            ".png",
            ".dng",
            ".tif",
            ".tiff",
        }

    @property
    def is_drone(self) -> bool:
        return "DJI" in self.camera_model.upper()

    @property
    def is_gopro(self) -> bool:
        return "HERO" in self.camera_model.upper()

    @property
    def is_insta360(self) -> bool:
        return "INSTA360" in self.camera_model.upper()

    # ------------------------------------------------------------------
    # Camera Intelligence Display
    # ------------------------------------------------------------------

    @property
    def manufacturer(self) -> str:
        if self.camera_profile.is_known():
            return self.camera_profile.manufacturer.value
        return self.camera_make

    @property
    def camera_display_name(self) -> str:
        if self.camera_profile.is_known():
            return self.camera_profile.display_name
        if self.camera_model != "Unknown":
            return self.camera_model
        return self.camera_make

    @property
    def camera_confidence(self) -> int:
        return self.camera_profile.confidence

    # ------------------------------------------------------------------

    def add_tag(self, tag: str) -> None:

        if tag not in self.tags:
            self.tags.append(tag)

    # ------------------------------------------------------------------

    def remove_tag(self, tag: str) -> None:

        if tag in self.tags:
            self.tags.remove(tag)

    # ------------------------------------------------------------------

    def __str__(self) -> str:

        return (
            f"{self.filename} | "
            f"{self.camera_model} | "
            f"{self.resolution} | "
            f"{self.duration}"
        )
