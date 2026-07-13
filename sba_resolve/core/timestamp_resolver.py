"""
SBA AI Studio
MI-002C Timestamp Resolver

Resolves the best available timestamp from metadata.

Priority:

1. DateTimeOriginal
2. CreateDate
3. MediaCreateDate
4. QuickTime CreateDate
5. FileCreateDate
6. FileModifyDate
"""

from datetime import datetime


class TimestampResolver:

    PRIORITY = [
        "DateTimeOriginal",
        "CreateDate",
        "MediaCreateDate",
        "TrackCreateDate",
        "QuickTimeCreateDate",
        "FileCreateDate",
        "FileModifyDate"
    ]

    @staticmethod
    def parse(value):
        """
        Convert ExifTool timestamp into datetime.
        """

        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        value = str(value)

        formats = [
            "%Y:%m:%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%Y:%m:%d %H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass

        return None

    @classmethod
    def resolve(cls, metadata):
        """
        Returns:

            datetime
            source field
            confidence
        """

        for field in cls.PRIORITY:

            if field not in metadata:
                continue

            dt = cls.parse(metadata[field])

            if dt:

                confidence = "HIGH"

                if field.startswith("File"):
                    confidence = "LOW"

                elif field in (
                    "CreateDate",
                    "MediaCreateDate",
                    "TrackCreateDate",
                    "QuickTimeCreateDate",
                ):
                    confidence = "MEDIUM"

                return {
                    "timestamp": dt,
                    "source": field,
                    "confidence": confidence,
                }

        return {
            "timestamp": None,
            "source": None,
            "confidence": "NONE",
        }