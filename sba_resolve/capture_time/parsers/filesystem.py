"""
SBA AI Studio
Filesystem Capture Time Parser

Final fallback parser.

Uses filesystem timestamps only when no metadata- or filename-based
timestamp could be resolved.
"""

from __future__ import annotations

from pathlib import Path

from sba_resolve.capture_time.models import TimestampCandidate
from sba_resolve.capture_time.parsers.base_parser import BaseCaptureTimeParser


class FileSystemParser(BaseCaptureTimeParser):
    """Resolve timestamps from the operating system."""

    name = "Filesystem"
    priority = 100

    def supports(self, metadata: dict) -> bool:
        return bool(metadata.get("SourceFile"))

    def parse(self, metadata: dict) -> TimestampCandidate | None:

        source = metadata.get("SourceFile")

        if not source:
            return None

        try:
            path = Path(source)

            if not path.exists():
                return None

            stat = path.stat()

            created = TimestampCandidate.from_timestamp(
                stat.st_ctime,
                source="FileCreateDate",
                confidence=0.30,
            )

            modified = TimestampCandidate.from_timestamp(
                stat.st_mtime,
                source="FileModifyDate",
                confidence=0.20,
            )

            if created is not None:
                return created

            return modified

        except Exception:
            return None