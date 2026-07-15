"""
============================================================
SBA AI Studio
Ride Summary Builder Regression Test
ML-026
Version : 1.0.0
============================================================

Verifies RideSummaryBuilder groups placements by ride_day
correctly, aggregates duration/cameras/scene count per day, and
integrates GPS-derived place names via the (mocked) geocoder -
without any real network access.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class FakeGeocoder:
    """
    Deterministic fake geocoder - no network, no real
    ReverseGeocoder involved at all.
    """

    def __init__(self, places_by_coords):
        self.places_by_coords = places_by_coords
        self.calls = []

    def place_name(self, latitude, longitude):
        self.calls.append((latitude, longitude))
        return self.places_by_coords.get((latitude, longitude))


class RideSummaryBuilderRegressionTest(BaseRegressionTest):

    name = "Ride Summary Builder (ML-026)"

    category = "Planning"

    description = (
        "Verify per-day duration/camera/scene aggregation and "
        "GPS-to-place-name integration in the ride summary "
        "builder."
    )

    def _make_placement(
        self,
        clip_name,
        ride_day,
        scene,
        camera_name,
        created,
        duration_frames,
        gps_latitude=None,
        gps_longitude=None,
        fps=25.0,
    ):

        from sba_resolve.core.models.media_file import MediaFile
        from sba_resolve.core.models.timeline_placement import (
            TimelinePlacement,
        )

        media = MediaFile(
            filename=clip_name,
            full_path=Path(f"/fake/{clip_name}"),
            relative_path=Path(clip_name),
            extension=".mp4",
            size=1024,
            created=created,
            duration=str(duration_frames / fps),
            gps_latitude=gps_latitude,
            gps_longitude=gps_longitude,
        )

        placement = TimelinePlacement(media_file=media)
        placement.ride_day = ride_day
        placement.scene = scene
        placement.camera_name = camera_name
        placement.clip_name = clip_name
        placement.duration_frames = duration_frames

        return placement

    def run(self) -> None:

        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.services.ride_summary_builder import (
            RideSummaryBuilder,
        )

        fps = 25.0

        day1_start = datetime(2026, 5, 12, 9, 0, 0)

        placements = [
            self._make_placement(
                "clip1.mp4", 1, 1, "GoPro HERO13 Black",
                day1_start, round(300 * fps),
                gps_latitude=54.7319, gps_longitude=-4.4180,
            ),
            self._make_placement(
                "clip2.mp4", 1, 2, "GoPro HERO8 Black",
                day1_start, round(120 * fps),
                gps_latitude=54.7319, gps_longitude=-4.4180,
            ),
            self._make_placement(
                "clip3.mp4", 2, 1, "GoPro HERO13 Black",
                datetime(2026, 5, 13, 10, 0, 0), round(600 * fps),
                gps_latitude=55.0, gps_longitude=-3.5,
            ),
        ]

        result = PlanningResult(placements=placements)

        geocoder = FakeGeocoder(
            {
                (54.7319, -4.4180): "Whithorn, Scotland, United Kingdom",
                (55.0, -3.5): "Edinburgh, Scotland, United Kingdom",
            }
        )

        builder = RideSummaryBuilder(geocoder=geocoder)

        summary = builder.build(result, fps=fps)

        if summary["total_days"] != 2:
            raise RuntimeError(
                f"Expected 2 days, got {summary['total_days']}."
            )

        day1 = summary["days"][0]
        day2 = summary["days"][1]

        if day1["day"] != 1 or day2["day"] != 2:
            raise RuntimeError("Days out of order or mislabeled.")

        if day1["date"] != "2026-05-12":
            raise RuntimeError(
                f"Expected day 1 date '2026-05-12', got "
                f"{day1['date']!r}."
            )

        # 300s + 120s = 420s = 7 minutes.
        if day1["duration_minutes"] != 7.0:
            raise RuntimeError(
                f"Expected day 1 duration 7.0 min, got "
                f"{day1['duration_minutes']!r}."
            )

        if day1["cameras"] != ["GoPro HERO13 Black", "GoPro HERO8 Black"]:
            # sorted() alphabetically
            if sorted(day1["cameras"]) != sorted(
                ["GoPro HERO13 Black", "GoPro HERO8 Black"]
            ):
                raise RuntimeError(
                    f"Unexpected day 1 cameras: {day1['cameras']!r}"
                )

        if day1["scene_count"] != 2:
            raise RuntimeError(
                f"Expected day 1 scene_count 2, got "
                f"{day1['scene_count']!r}."
            )

        if day1["places"] != ["Whithorn, Scotland, United Kingdom"]:
            raise RuntimeError(
                f"Expected day 1 places to be Whithorn (deduped "
                f"across both clips at the same coords), got "
                f"{day1['places']!r}."
            )

        # 600s = 10 minutes.
        if day2["duration_minutes"] != 10.0:
            raise RuntimeError(
                f"Expected day 2 duration 10.0 min, got "
                f"{day2['duration_minutes']!r}."
            )

        if day2["places"] != ["Edinburgh, Scotland, United Kingdom"]:
            raise RuntimeError(
                f"Expected day 2 places to be Edinburgh, got "
                f"{day2['places']!r}."
            )

        # Geocoder should be called once per clip with GPS data
        # (2 on day 1 sharing coords + 1 on day 2 = 3 calls), even
        # though day 1's result is deduped down to 1 place in the
        # summary.
        if len(geocoder.calls) != 3:
            raise RuntimeError(
                f"Expected 3 geocoder calls (one per clip with "
                f"GPS data), got {len(geocoder.calls)}."
            )
