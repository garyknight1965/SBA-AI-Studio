"""
============================================================
SBA AI Studio
Camera Profile
CORE-010-001
Version : 1.0.0 Alpha
============================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CameraManufacturer(str, Enum):
    GOPRO = "GoPro"
    DJI = "DJI"
    INSTA360 = "Insta360"
    SONY = "Sony"
    CANON = "Canon"
    UNKNOWN = "Unknown"


class CameraType(str, Enum):
    ACTION = "Action Camera"
    DRONE = "Drone"
    CAMERA360 = "360 Camera"
    MIRRORLESS = "Mirrorless"
    PHONE = "Phone"
    UNKNOWN = "Unknown"


@dataclass(slots=True)
class CameraProfile:
    """
    Canonical camera identity used throughout SBA AI Studio.
    """

    manufacturer: CameraManufacturer = CameraManufacturer.UNKNOWN
    model: str = "Unknown"
    family: str = "Unknown"
    camera_type: CameraType = CameraType.UNKNOWN

    confidence: int = 0
    detection_method: str = "Unknown"

    firmware: str = ""
    encoder: str = ""
    metaformat: str = ""

    # Distinguishes multiple simultaneous streams from the SAME
    # physical camera (e.g. an Insta360 X3 exporting two lens
    # views for one recording moment). Left blank for ordinary,
    # single-stream cameras.
    view: str = ""

    def is_known(self) -> bool:
        return self.manufacturer != CameraManufacturer.UNKNOWN

    @property
    def display_name(self) -> str:
        if self.model and self.model != "Unknown":
            base = f"{self.manufacturer.value} {self.model}"
        else:
            base = self.manufacturer.value

        if self.view:
            return f"{base} ({self.view})"

        return base

    def summary(self) -> dict:
        return {
            "manufacturer": self.manufacturer.value,
            "model": self.model,
            "family": self.family,
            "camera_type": self.camera_type.value,
            "confidence": self.confidence,
            "detection_method": self.detection_method,
            "firmware": self.firmware,
            "encoder": self.encoder,
            "metaformat": self.metaformat,
            "view": self.view,
        }

    def __str__(self) -> str:
        return (
            f"{self.display_name} "
            f"({self.confidence}% via {self.detection_method})"
        )

    __repr__ = __str__
