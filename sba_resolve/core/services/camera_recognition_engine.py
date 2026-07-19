"""
SBA AI Studio
Camera Recognition Engine
CORE-010-002
Version 1.0.2
"""

from __future__ import annotations

import re

from sba_resolve.core.models.camera_profile import (
    CameraManufacturer,
    CameraProfile,
    CameraType,
)

# Matches Insta360 X3 filenames as they actually appear on disk, e.g.:
#   VID_20260717_114753_10_002.mp4
#   VID_20260717_152440_00_008_204150.mp4  (with optional trailing suffix)
_INSTA360_FILENAME_PATTERN = re.compile(
    r"^VID_\d{8}_\d{6}_\d{2}_\d{3}(_\d{6})?\.[A-Za-z0-9]+$"
)


class CameraRecognitionEngine:

    @staticmethod
    def detect(metadata: dict, source_path: str = "") -> CameraProfile:

        model = str(metadata.get("Model", "")).upper()
        make = str(metadata.get("Make", "")).upper()
        encoder = str(metadata.get("Encoder", "")).upper()
        meta = str(metadata.get("MetaFormat", "")).lower()
        handler = str(metadata.get("HandlerDescription", "")).upper()
        path = source_path.replace("\\", "/").upper()
        filename = source_path.replace("\\", "/").rsplit("/", 1)[-1]

        if "HERO" in model or meta == "gpmd" or "GOPRO" in handler:
            return CameraProfile(
                manufacturer=CameraManufacturer.GOPRO,
                model=metadata.get("Model", "GoPro"),
                family="Hero",
                camera_type=CameraType.ACTION,
                confidence=100,
                detection_method="Metadata",
                firmware=str(metadata.get("FirmwareVersion", "")),
                encoder=str(metadata.get("CompressorName", "")),
                metaformat=meta,
            )

        if "DJI FLIP" in encoder:
            return CameraProfile(
                manufacturer=CameraManufacturer.DJI,
                model="Flip",
                family="Flip",
                camera_type=CameraType.DRONE,
                confidence=100,
                detection_method="Encoder",
                encoder=encoder,
                metaformat=meta,
            )

        if meta == "djmd" or "DJI" in make:
            return CameraProfile(
                manufacturer=CameraManufacturer.DJI,
                model=str(metadata.get("Model", "Unknown")),
                family="DJI",
                camera_type=CameraType.DRONE,
                confidence=90,
                detection_method="MetaFormat",
                encoder=encoder,
                metaformat=meta,
            )

        if _INSTA360_FILENAME_PATTERN.match(filename):
            return CameraProfile(
                manufacturer=CameraManufacturer.INSTA360,
                model="X3",
                family="X Series",
                camera_type=CameraType.CAMERA360,
                confidence=85,
                detection_method="Filename Pattern",
                encoder=encoder,
            )

        if "/360/" in path or path.endswith("/360"):
            return CameraProfile(
                manufacturer=CameraManufacturer.INSTA360,
                model="X3",
                family="X Series",
                camera_type=CameraType.CAMERA360,
                confidence=75,
                detection_method="Folder Rule",
                encoder=encoder,
            )

        return CameraProfile()