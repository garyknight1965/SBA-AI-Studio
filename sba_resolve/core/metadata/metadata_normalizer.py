"""
============================================================
SBA AI Studio
Metadata Normalizer
Version : 4.0.0 Alpha
Sprint : ML-004A
============================================================
"""

from __future__ import annotations

import re
from datetime import datetime


class MetadataNormalizer:

    @staticmethod
    def normalize(items: list[dict]) -> list[dict]:
        return [MetadataNormalizer.normalize_item(i) for i in items]

    @staticmethod
    def normalize_item(item: dict) -> dict:

        item = dict(item)

        # --------------------------------------------------
        # File Size
        # --------------------------------------------------

        item["FileSize"] = MetadataNormalizer._file_size(
            item.get("FileSize#") or item.get("FileSize")
        )

        # --------------------------------------------------
        # Width / Height
        # --------------------------------------------------

        item["ImageWidth"] = MetadataNormalizer._to_int(
            item.get("ImageWidth")
        )

        item["ImageHeight"] = MetadataNormalizer._to_int(
            item.get("ImageHeight")
        )

        # --------------------------------------------------
        # Frame Rate
        # --------------------------------------------------

        item["VideoFrameRate"] = MetadataNormalizer._to_float(
            item.get("VideoFrameRate")
        )

        # --------------------------------------------------
        # Bitrate
        # --------------------------------------------------

        item["AvgBitrate"] = MetadataNormalizer._to_int(
            item.get("AvgBitrate")
        )

        # --------------------------------------------------
        # Audio
        # --------------------------------------------------

        item["AudioChannels"] = MetadataNormalizer._to_int(
            item.get("AudioChannels")
        )

        item["AudioSampleRate"] = MetadataNormalizer._to_int(
            item.get("AudioSampleRate")
        )

        # --------------------------------------------------
        # Camera Make
        # --------------------------------------------------

        if not item.get("Make"):
            item["Make"] = MetadataNormalizer._infer_make(
                item.get("Model", "")
            )

        # --------------------------------------------------

        return item

    @staticmethod
    def _infer_make(model: str) -> str:

        model = model.upper()

        if "HERO" in model:
            return "GoPro"

        if "DJI" in model:
            return "DJI"

        if "INSTA360" in model:
            return "Insta360"

        if "SONY" in model:
            return "Sony"

        if "CANON" in model:
            return "Canon"

        return "Unknown"

    @staticmethod
    def _to_int(value):

        if value is None:
            return 0

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        if isinstance(value, str):

            digits = re.sub(r"[^\d]", "", value)

            if digits:
                return int(digits)

        return 0

    @staticmethod
    def _to_float(value):

        if value is None:
            return 0.0

        try:
            return float(value)
        except Exception:
            return 0.0

    @staticmethod
    def _file_size(value):

        if value is None:
            return 0

        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str):

            m = re.match(
                r"([\d.]+)\s*(KB|MB|GB|TB)?",
                value,
                re.IGNORECASE,
            )

            if not m:
                return 0

            number = float(m.group(1))
            unit = (m.group(2) or "").upper()

            factor = {
                "KB": 1024,
                "MB": 1024**2,
                "GB": 1024**3,
                "TB": 1024**4,
            }.get(unit, 1)

            return int(number * factor)

        return 0