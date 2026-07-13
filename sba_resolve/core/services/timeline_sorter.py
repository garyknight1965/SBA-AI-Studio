from __future__ import annotations


class TimelineSorter:
    """
    Sort timeline clips into true chronological order.

    Sorting priority:

    1. Capture timestamp
    2. Camera name
    3. Filename
    """

    @staticmethod
    def sort(clips):

        return sorted(
            clips,
            key=lambda c: (
                c.media.capture_time,
                c.media.camera_model or "",
                c.media.file_name.lower(),
            ),
        )