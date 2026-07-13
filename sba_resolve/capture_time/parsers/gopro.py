"""
SBA AI Studio
GoPro Capture Time Parser

Supports:
- GoPro Hero 8
- GoPro Hero 9
- GoPro Hero 10
- GoPro Hero 11
- GoPro Hero 12
- GoPro Hero 13

The parser extracts the best available capture timestamp from GoPro
metadata and returns a TimestampCandidate.
"""

from __future__ import annotations

from typing import Any

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class GoProParser(BaseCaptureTimeParser):
    """Capture time parser for GoPro media."""

    name = "GoPro"
    priority = 10

    _FIELDS = (
        "DateTimeOriginal",
        "CreateDate",
        "MediaCreateDate",
        "TrackCreateDate",
        "FileCreateDate",
        "FileModifyDate",
    )

    def supports(self, metadata: dict[str, Any]) -> bool:
        """
        Determine whether this metadata belongs to a GoPro file.
        """

        make = str(metadata.get("Make", "")).upper()
        model = str(metadata.get("Model", "")).upper()
        encoder = str(metadata.get("Encoder", "")).upper()
        software = str(metadata.get("Software", "")).upper()

        values = (make, model, encoder, software)

        return any("GOPRO" in value for value in values)

    def parse(self, metadata: dict[str, Any]) -> TimestampCandidate | None:
        """
        Return the best timestamp candidate for GoPro media.
        """

        if not self.supports(metadata):
            return None

        for field in self._FIELDS:

            value = metadata.get(field)

            if not value:
                continue

            timestamp = TimestampCandidate.parse_datetime(value)

            if timestamp is None:
                continue

            confidence = self._confidence(field)

            return TimestampCandidate(
                timestamp=timestamp,
                source=field,
                confidence=confidence,
            )

        return None

    @staticmethod
    def _confidence(field: str) -> float:
        """
        Confidence score for each metadata source.
        """

        scores = {
            "DateTimeOriginal": 1.00,
            "CreateDate": 0.98,
            "MediaCreateDate": 0.95,
            "TrackCreateDate": 0.92,
            "FileCreateDate": 0.60,
            "FileModifyDate": 0.40,
        }

        return scores.get(field, 0.0)