"""
SBA AI Studio
Filename Capture Time Parser

Extracts capture timestamps from common filename patterns.
"""

from __future__ import annotations

import re

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class FilenameParser(BaseCaptureTimeParser):
    """Extract timestamps from filenames."""

    name = "Filename"
    priority = 90

    _PATTERNS = (
        # IMG_20260712_153045
        (
            re.compile(r"(\d{8})[_-](\d{6})"),
            "%Y%m%d%H%M%S",
        ),

        # 2026-07-12_15-30-45
        (
            re.compile(
                r"(\d{4})-(\d{2})-(\d{2})[_ ](\d{2})[-:](\d{2})[-:](\d{2})"
            ),
            None,
        ),

        # 20260712153045
        (
            re.compile(r"(\d{14})"),
            "%Y%m%d%H%M%S",
        ),
    )

    def supports(self, metadata: dict) -> bool:
        return bool(metadata.get("FileName"))

    def parse(self, metadata: dict) -> TimestampCandidate | None:

        filename = metadata.get("FileName")

        if not filename:
            return None

        for pattern, fmt in self._PATTERNS:

            match = pattern.search(filename)

            if not match:
                continue

            try:

                if fmt:

                    value = "".join(match.groups())

                    timestamp = TimestampCandidate.parse_datetime(
                        value,
                        fmt=fmt,
                    )

                else:

                    y, m, d, hh, mm, ss = match.groups()

                    value = (
                        f"{y}-{m}-{d} "
                        f"{hh}:{mm}:{ss}"
                    )

                    timestamp = TimestampCandidate.parse_datetime(value)

                if timestamp is None:
                    continue

                return TimestampCandidate(
                    timestamp=timestamp,
                    source="FileName",
                    confidence=0.55,
                )

            except Exception:
                continue

        return None