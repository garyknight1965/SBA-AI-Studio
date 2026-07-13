"""
SBA AI Studio
Apple iPhone Capture Time Parser

Supports:
- iPhone
- iPad
- Apple QuickTime video
"""

from __future__ import annotations

from typing import Any

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class IPhoneParser(BaseCaptureTimeParser):
    """Capture time parser for Apple media."""

    name = "Apple iPhone"
    priority = 18

    _FIELDS = (
        "CreationDate",
        "ContentCreateDate",
        "MediaCreateDate",
        "TrackCreateDate",
        "DateTimeOriginal",
        "CreateDate",
        "FileCreateDate",
        "FileModifyDate",
    )

    def supports(self, metadata: dict[str, Any]) -> bool:

        make = str(metadata.get("Make", "")).upper()
        model = str(metadata.get("Model", "")).upper()
        software = str(metadata.get("Software", "")).upper()

        values = (make, model, software)

        return any(
            keyword in value
            for value in values
            for keyword in (
                "APPLE",
                "IPHONE",
                "IPAD",
                "IOS",
            )
        )

    def parse(self, metadata: dict[str, Any]) -> TimestampCandidate | None:

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
            "CreationDate": 1.00,
            "ContentCreateDate": 0.99,
            "MediaCreateDate": 0.98,
            "TrackCreateDate": 0.96,
            "DateTimeOriginal": 0.95,
            "CreateDate": 0.94,
            "FileCreateDate": 0.60,
            "FileModifyDate": 0.40,
        }

        return scores.get(field, 0.0)