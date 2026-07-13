"""
SBA AI Studio
Insta360 Capture Time Parser

Supports Insta360 cameras including:
- X3
- X4
- ONE X
- ONE X2
- ONE RS
- ACE
- ACE Pro
"""

from __future__ import annotations

from typing import Any

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class Insta360Parser(BaseCaptureTimeParser):
    """Capture time parser for Insta360 media."""

    name = "Insta360"
    priority = 15

    _FIELDS = (
        "DateTimeOriginal",
        "CreationDate",
        "CreateDate",
        "MediaCreateDate",
        "TrackCreateDate",
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
                "INSTA360",
                "ONE X",
                "ONE X2",
                "ONE RS",
                "X3",
                "X4",
                "ACE",
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
            "DateTimeOriginal": 1.00,
            "CreationDate": 0.99,
            "CreateDate": 0.98,
            "MediaCreateDate": 0.96,
            "TrackCreateDate": 0.94,
            "FileCreateDate": 0.60,
            "FileModifyDate": 0.40,
        }

        return scores.get(field, 0.0)