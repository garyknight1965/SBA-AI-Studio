"""
SBA AI Studio
QuickTime Capture Time Parser

Handles MOV/MP4 metadata commonly written by:

- GoPro
- Insta360
- DJI
- Apple iPhone
- Blackmagic
- Canon
- Sony
"""

from __future__ import annotations

from typing import Any

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class QuickTimeParser(BaseCaptureTimeParser):
    """Parser for QuickTime-based metadata."""

    name = "QuickTime"
    priority = 20

    _FIELDS = (
        "MediaCreateDate",
        "TrackCreateDate",
        "CreateDate",
        "CreationDate",
        "ContentCreateDate",
    )

    def supports(self, metadata: dict[str, Any]) -> bool:
        """
        Return True if QuickTime timestamp fields are present.
        """
        return any(field in metadata for field in self._FIELDS)

    def parse(self, metadata: dict[str, Any]) -> TimestampCandidate | None:
        """
        Return the best QuickTime timestamp candidate.
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

            return TimestampCandidate(
                timestamp=timestamp,
                source=field,
                confidence=self._confidence(field),
            )

        return None

    @staticmethod
    def _confidence(field: str) -> float:
        scores = {
            "MediaCreateDate": 0.99,
            "TrackCreateDate": 0.97,
            "CreateDate": 0.95,
            "CreationDate": 0.93,
            "ContentCreateDate": 0.92,
        }

        return scores.get(field, 0.80)