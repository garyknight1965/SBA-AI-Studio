"""
============================================================
SBA AI Studio
Location Grouper Regression Test
ML-038
Version : 1.0.0
============================================================

Verifies LocationGrouper:
- Groups clips by the place name ReverseGeocoder returns.
- Clips with no GPS, or an unresolvable lookup, land in a single
  UNKNOWN_LOCATION group rather than being dropped.
- Groups are sorted alphabetically by place name, with
  UNKNOWN_LOCATION always last.

Uses a fake geocoder with a fixed lookup table - no real network
calls, no rate-limit delay.
"""

from __future__ import annotations

from pathlib import Path

from regression.base_test import BaseRegressionTest


class FakeGeocoder:
    """
    Returns a place name from a fixed table keyed by (lat, lon),
    or None for anything not in the table - standing in for
    ReverseGeocoder without any real network access.
    """

    def __init__(self, table: dict) -> None:
        self.table = table

    def place_name(self, latitude, longitude):
        return self.table.get((latitude, longitude))


class LocationGrouperRegressionTest(BaseRegressionTest):

    name = "Location Grouper (ML-038)"

    category = "Planning"

    description = (
        "Verify clips are grouped by reverse-geocoded place name, "
        "with no-GPS/unresolvable clips landing in a single "
        "Unknown Location group, sorted last."
    )

    def _make_media(self, filename, latitude, longitude):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            gps_latitude=latitude,
            gps_longitude=longitude,
        )

    def run(self) -> None:

        from sba_resolve.core.models.location_group import (
            UNKNOWN_LOCATION,
        )
        from sba_resolve.core.services.location_grouper import (
            LocationGrouper,
        )

        whithorn_clip_1 = self._make_media("clip1.mp4", 54.73, -4.42)
        whithorn_clip_2 = self._make_media("clip2.mp4", 54.73, -4.42)
        aachen_clip = self._make_media("clip3.mp4", 50.78, 6.09)
        no_gps_clip = self._make_media("clip4.mp4", None, None)
        unresolvable_clip = self._make_media("clip5.mp4", 99.0, 99.0)

        fake_geocoder = FakeGeocoder(
            {
                (54.73, -4.42): "Whithorn, Scotland, United Kingdom",
                (50.78, 6.09): "Aachen, North Rhine-Westphalia, Germany",
                # (99.0, 99.0) deliberately absent -> unresolvable
            }
        )

        grouper = LocationGrouper(geocoder=fake_geocoder)

        groups = grouper.group(
            [
                whithorn_clip_1,
                aachen_clip,
                whithorn_clip_2,
                no_gps_clip,
                unresolvable_clip,
            ]
        )

        if len(groups) != 3:
            raise RuntimeError(
                f"Expected 3 groups (Aachen, Whithorn, Unknown), "
                f"got {len(groups)}: "
                f"{[g.place_name for g in groups]!r}"
            )

        # --------------------------------------------------
        # Alphabetical order for known places, Unknown last.
        # --------------------------------------------------

        if groups[0].place_name != "Aachen, North Rhine-Westphalia, Germany":
            raise RuntimeError(
                f"Expected Aachen first (alphabetical), got "
                f"{groups[0].place_name!r}."
            )

        if groups[1].place_name != "Whithorn, Scotland, United Kingdom":
            raise RuntimeError(
                f"Expected Whithorn second, got "
                f"{groups[1].place_name!r}."
            )

        if groups[2].place_name != UNKNOWN_LOCATION:
            raise RuntimeError(
                f"Expected UNKNOWN_LOCATION last, got "
                f"{groups[2].place_name!r}."
            )

        # --------------------------------------------------
        # Grouping correctness.
        # --------------------------------------------------

        whithorn_group = groups[1]

        if whithorn_group.clip_count != 2:
            raise RuntimeError(
                f"Expected 2 clips in the Whithorn group, got "
                f"{whithorn_group.clip_count}."
            )

        if {c.filename for c in whithorn_group.clips} != {
            "clip1.mp4",
            "clip2.mp4",
        }:
            raise RuntimeError(
                "Whithorn group does not contain exactly the two "
                "clips at that location."
            )

        unknown_group = groups[2]

        if unknown_group.clip_count != 2:
            raise RuntimeError(
                f"Expected 2 clips in the Unknown group (no-GPS + "
                f"unresolvable), got {unknown_group.clip_count}."
            )

        if not unknown_group.is_unknown:
            raise RuntimeError(
                "is_unknown should be True for the Unknown "
                "Location group."
            )

        if whithorn_group.is_unknown:
            raise RuntimeError(
                "is_unknown should be False for a real, resolved "
                "location group."
            )
