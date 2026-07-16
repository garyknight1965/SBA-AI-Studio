"""
============================================================
SBA AI Studio
Timestamp Resolver
Version : 4.0.0 Alpha
Sprint : ML-004B
============================================================
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


class TimestampResolver:
    """
    Resolve the best available timestamp for a media asset.

    Resolution order:

        1. CreateDate
        2. MediaCreateDate
        3. DateTimeOriginal
        4. Filename
        5. File Modified Date
    """

    DATE_FIELDS = (
        "CreateDate",
        "MediaCreateDate",
        "DateTimeOriginal",
    )

    @classmethod
    def resolve(cls, metadata: dict) -> datetime | None:

        # ----------------------------------------------------------
        # 1 Metadata
        # ----------------------------------------------------------

        for field in cls.DATE_FIELDS:

            value = metadata.get(field)

            if value:

                dt = cls.parse_datetime(value)

                if dt:
                    return dt

        # ----------------------------------------------------------
        # 2 Filename
        # ----------------------------------------------------------

        source = metadata.get("SourceFile")

        if source:

            path = Path(source)

            dt = cls.parse_filename(path.name)

            if dt:
                return dt

            if path.exists():
                return datetime.fromtimestamp(path.stat().st_mtime)

        return None

    # ==============================================================
    # Resolve, reporting WHICH source won
    #
    # Same resolution order as resolve(), but also returns the
    # name of the source that produced the timestamp, so callers
    # (MetadataMapper -> ConfidenceEngine) can score how much to
    # trust it. Used instead of resolve() wherever that source
    # name is needed; resolve() itself is left untouched.
    # ==============================================================

    @classmethod
    def resolve_with_source(
        cls, metadata: dict
    ) -> tuple[datetime | None, str | None]:

        # ----------------------------------------------------------
        # 1 Metadata
        # ----------------------------------------------------------

        for field in cls.DATE_FIELDS:

            value = metadata.get(field)

            if value:

                dt = cls.parse_datetime(value)

                if dt:
                    return dt, field

        # ----------------------------------------------------------
        # 2 Filename
        # ----------------------------------------------------------

        source = metadata.get("SourceFile")

        if source:

            path = Path(source)

            for parser, source_name in (
                (cls._parse_dji, "DJI Filename"),
                (cls._parse_insta360, "Insta360 Filename"),
            ):

                dt = parser(path.name)

                if dt:
                    return dt, source_name

            if path.exists():
                return (
                    datetime.fromtimestamp(path.stat().st_mtime),
                    "FileModified",
                )

        return None, None

    # ==============================================================
    # Date parser
    # ==============================================================

    @staticmethod
    def parse_datetime(value):

        if not value:
            return None

        formats = (

            "%Y:%m:%d %H:%M:%S",

            "%Y-%m-%d %H:%M:%S",

            "%Y:%m:%d %H:%M:%S.%f",

            "%Y-%m-%dT%H:%M:%S",

            "%Y-%m-%dT%H:%M:%S.%f",
        )

        for fmt in formats:

            try:
                return datetime.strptime(value, fmt)

            except ValueError:
                pass

        return None

    # ==============================================================
    # Filename parser
    # ==============================================================

    @classmethod
    def parse_filename(cls, filename):

        parsers = (

            cls._parse_dji,

            cls._parse_insta360,

        )

        for parser in parsers:

            dt = parser(filename)

            if dt:
                return dt

        return None

    # ==============================================================
    # DJI
    #
    # DJI_20250626_094438_0001.MP4  (original SD-card naming)
    # dji_fly_20260625_151204_0001_1782454141375_video_beautify.mp4
    #   (confirmed DJI Fly app export naming)
    # ==============================================================

    @staticmethod
    def _parse_dji(filename):

        match = re.search(

            r"DJI(?:_FLY)?_(20\d{6})_(\d{6})",

            filename,

            re.IGNORECASE,
        )

        if not match:
            return None

        return datetime.strptime(

            match.group(1) + match.group(2),

            "%Y%m%d%H%M%S",
        )

    # ==============================================================
    # Insta360
    #
    # VID_20250626_094438_001.insv
    # VID_20250626_094438_001.mp4
    # ==============================================================

    @staticmethod
    def _parse_insta360(filename):

        match = re.search(

            r"VID_(20\d{6})_(\d{6})",

            filename,

            re.IGNORECASE,
        )

        if not match:
            return None

        return datetime.strptime(

            match.group(1) + match.group(2),

            "%Y%m%d%H%M%S",
        )