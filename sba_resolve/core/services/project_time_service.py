"""
============================================================
SBA AI Studio
Project Time Service
ML-011-013B
Version : 1.0.0 Alpha
============================================================

Provides timeline time calculations.

Version 1 determines the earliest capture timestamp
within a collection of MediaFile objects.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sba_resolve.core.models.media_file import MediaFile


class ProjectTimeService:
    """
    Timeline time calculations.
    """

    @staticmethod
    def project_start(
        media_files: Iterable[MediaFile],
    ) -> datetime | None:
        """
        Return the earliest capture timestamp.
        """

        timestamps = []

        for media in media_files:

            timestamp = (
                getattr(media, "capture_time", None)
                or getattr(media, "created", None)
            )

            if timestamp is not None:
                timestamps.append(timestamp)

        if not timestamps:
            return None

        return min(timestamps)