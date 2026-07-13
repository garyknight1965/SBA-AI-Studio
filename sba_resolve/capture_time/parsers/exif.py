"""
SBA AI Studio
Generic EXIF Capture Time Parser
"""

from __future__ import annotations

from typing import Any

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class ExifParser(BaseCaptureTimeParser):
    """Generic EXIF metadata parser."""

    name = "EXIF"
    priority = 50

    _FIELDS = (
        "DateTimeOriginal",
        "SubSecDateTimeOriginal",
        "CreateDate",
        "ModifyDate",
        "FileCreateDate",
        "FileModifyDate",
    )

    def supports(self, metadata: dict[str, Any]) -> bool:
        """Return True if EXIF timestamp fields are present."""
        return any(field in metadata for field in self._FIELDS)

    def parse(self, metadata: dict[str, Any]) -> TimestampCandidate | None:
        """Return the highest quality EXIF timestamp candidate."""

        if not self.supports(metadata):
            return None

        for field in self._FIELDS:
            value = metadata.get(field)

            if not value:
                continue

            timestamp = TimestampCandidate.parse_datetime(value)

            if timestamp is None:
                continue

            return TimestampCandidate(
                timestamp=timestamp,
                source=field,
                confidence=self._confidence(field),
            )

        return None

    @staticmethod
    def _confidence(field: str) -> float:
        scores = {
            "DateTimeOriginal": 1.00,
            "SubSecDateTimeOriginal": 1.00,
            "CreateDate": 0.95,
            "ModifyDate": 0.85,
            "FileCreateDate": 0.60,
            "FileModifyDate": 0.40,
        }

        return scores.get(field, 0.0)