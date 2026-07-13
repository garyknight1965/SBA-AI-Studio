\
"""
SBA AI Studio
Camera Recognition Engine
CORE-010-002
Version 1.0.1
"""

from __future__ import annotations

from sba_resolve.core.models.camera_profile import (
    CameraManufacturer,
    CameraProfile,
    CameraType,
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
