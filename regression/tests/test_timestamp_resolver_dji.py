"""
============================================================
SBA AI Studio
Timestamp Resolver DJI Filename Regression Test
ML-016
Version : 1.0.0
============================================================

Verifies TimestampResolver.parse_filename() correctly extracts
capture time from both DJI filename conventions:

- Original SD-card naming: DJI_20250626_094438_0001.MP4
- Confirmed DJI Fly app export naming:
  dji_fly_20260625_151204_0001_1782454141375_video_beautify.mp4

Without this, accepted DJI Fly footage would fall through to
the file-modified-time fallback instead of its real capture
time, breaking Ride Day/segment/multicam detection for DJI
clips.
"""

from __future__ import annotations

from datetime import datetime

from regression.base_test import BaseRegressionTest


class TimestampResolverDjiRegressionTest(BaseRegressionTest):

    name = "Timestamp Resolver DJI Filenames (ML-016)"

    category = "Metadata"

    description = (
        "Verify DJI filename capture-time parsing covers both "
        "the original SD-card naming and the confirmed DJI Fly "
        "app export naming."
    )

    def run(self) -> None:

        from sba_resolve.core.metadata.timestamp_resolver import (
            TimestampResolver,
        )

        original_naming = TimestampResolver.parse_filename(
            "DJI_20250626_094438_0001.MP4"
        )

        if original_naming != datetime(2025, 6, 26, 9, 44, 38):
            raise RuntimeError(
                "Failed to parse original DJI SD-card naming: "
                f"got {original_naming!r}."
            )

        dji_fly_naming = TimestampResolver.parse_filename(
            "dji_fly_20260625_151204_0001_"
            "1782454141375_video_beautify.mp4"
        )

        if dji_fly_naming != datetime(2026, 6, 25, 15, 12, 4):
            raise RuntimeError(
                "Failed to parse DJI Fly app export naming: "
                f"got {dji_fly_naming!r}."
            )

        # Case-insensitivity, since real files are lowercase
        # ("dji_fly_...") while the older convention is
        # documented uppercase ("DJI_...").
        lowercase = TimestampResolver.parse_filename(
            "dji_20250626_094438_0001.mp4"
        )

        if lowercase != datetime(2025, 6, 26, 9, 44, 38):
            raise RuntimeError(
                "DJI filename parsing should be case-insensitive, "
                f"got {lowercase!r}."
            )
