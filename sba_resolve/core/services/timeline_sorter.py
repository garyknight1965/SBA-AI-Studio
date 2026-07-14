"""
============================================================
SBA AI Studio
Timeline Sorter
ML-011-007D.1
Version : 2.0.0 Alpha
============================================================

Sort MediaFile objects into true chronological order.

Sorting priority:

1. Resolved capture time
2. Camera display name
3. Filename
"""

from __future__ import annotations

from datetime import datetime

from sba_resolve.core.models.media_file import MediaFile


class TimelineSorter:
    """
    Sort MediaFile objects into chronological order.

    This service operates directly on MediaFile objects.
    """

    @staticmethod
    def sort(media_files: list[MediaFile]) -> list[MediaFile]:
        """
        Return MediaFiles sorted chronologically.

        Parameters
        ----------
        media_files
            List of MediaFile objects.

        Returns
        -------
        list[MediaFile]
            Sorted MediaFiles.
        """

        def capture_time(media: MediaFile) -> datetime:
            """
            Determine the best available timestamp.

            Future versions will use the Capture Time
            Resolver result.

            For now we use the resolved creation time.
            """

            if media.created is not None:
                return media.created

            return datetime.min

        return sorted(
            media_files,
            key=lambda media: (
                capture_time(media),
                media.camera_display_name.lower(),
                media.filename.lower(),
            ),
        )