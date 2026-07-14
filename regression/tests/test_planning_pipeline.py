"""
============================================================
SBA AI Studio
Planning Pipeline Regression Test
ML-011
Version : 1.0.0
============================================================

Verifies the full Ride Reconstruction pipeline:

    MediaLibrary -> TimelinePlanningService.plan() -> PlanningResult

Uses synthetic MediaFile objects so this test is fully portable
and does not depend on real footage being present on disk.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class PlanningPipelineRegressionTest(BaseRegressionTest):

    name = "Planning Pipeline (ML-011)"

    category = "Planning"

    description = (
        "Verify MediaLibrary -> TimelinePlanningService.plan() "
        "produces a correct PlanningResult across two ride days "
        "and two cameras."
    )

    def _make_media(
        self,
        filename,
        camera_model,
        created,
        duration_seconds,
        fps=25.0,
    ):

        from sba_resolve.core.models.camera_profile import (
            CameraManufacturer,
            CameraProfile,
            CameraType,
        )
        from sba_resolve.core.models.media_file import MediaFile

        profile = CameraProfile(
            manufacturer=CameraManufacturer.GOPRO,
            model=camera_model,
            family="Hero",
            camera_type=CameraType.ACTION,
            confidence=100,
            detection_method="Test Fixture",
        )

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            camera_model=camera_model,
            camera_profile=profile,
            created=created,
            duration=str(duration_seconds),
            fps=fps,
        )

    def run(self) -> None:

        from sba_resolve.core.models.media_library import MediaLibrary
        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        library = MediaLibrary()

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        # Ride day 1: Hero13 (with lav mic / transcript source),
        # then Hero8, back-to-back.
        library.add(
            self._make_media(
                "hero13_0001.mp4",
                "HERO13 Black",
                day1_start,
                duration_seconds=60,
            )
        )
        library.add(
            self._make_media(
                "hero13_0002.mp4",
                "HERO13 Black",
                day1_start + timedelta(seconds=61),
                duration_seconds=30,
            )
        )
        library.add(
            self._make_media(
                "hero8_0001.mp4",
                "HERO8 Black",
                day1_start + timedelta(seconds=95),
                duration_seconds=45,
            )
        )

        # Ride day 2: gap of 6 hours (> DayDetector.DEFAULT_MAX_GAP
        # of 4 hours) so this must become a separate RideDay.
        day2_start = day1_start + timedelta(hours=6)

        library.add(
            self._make_media(
                "hero13_0003.mp4",
                "HERO13 Black",
                day2_start,
                duration_seconds=20,
            )
        )

        service = TimelinePlanningService()

        result = service.plan(library)

        if not isinstance(result, PlanningResult):
            raise RuntimeError(
                "plan() did not return a PlanningResult."
            )

        if result.statistics.ride_days != 2:
            raise RuntimeError(
                f"Expected 2 ride days, got "
                f"{result.statistics.ride_days}."
            )

        if result.statistics.total_clips != 4:
            raise RuntimeError(
                f"Expected 4 total clips, got "
                f"{result.statistics.total_clips}."
            )

        if not result.has_segments:
            raise RuntimeError("PlanningResult has no segments.")

        # Day 1 should produce 2 segments (Hero13 x2 clips grouped,
        # then Hero8 x1 clip). Day 2 should produce 1 segment.
        if len(result.segments) != 3:
            raise RuntimeError(
                f"Expected 3 planning segments, got "
                f"{len(result.segments)}."
            )

        if len(result.placements) != 4:
            raise RuntimeError(
                f"Expected 4 placements, got "
                f"{len(result.placements)}."
            )

        # Verify sequential placement math on ride day 1, Hero13
        # track: first clip at frame 0, second clip starts where
        # the first one ends (60s * 25fps = 1500 frames).
        hero13_day1 = [
            p for p in result.placements
            if p.ride_day == 1 and p.camera_name == "GoPro HERO13 Black"
        ]

        hero13_day1.sort(key=lambda p: p.record_frame)

        if len(hero13_day1) != 2:
            raise RuntimeError(
                "Expected 2 Hero13 placements on ride day 1."
            )

        if hero13_day1[0].record_frame != 0:
            raise RuntimeError(
                "First clip on a track must start at frame 0."
            )

        expected_second_start = hero13_day1[0].duration_frames

        if hero13_day1[1].record_frame != expected_second_start:
            raise RuntimeError(
                "Second clip did not start where the first "
                "clip's duration ended (sequential placement)."
            )

        # Ride day 2 must reset its frame cursor independently of
        # ride day 1.
        hero13_day2 = [
            p for p in result.placements
            if p.ride_day == 2 and p.camera_name == "GoPro HERO13 Black"
        ]

        if len(hero13_day2) != 1:
            raise RuntimeError(
                "Expected 1 Hero13 placement on ride day 2."
            )

        if hero13_day2[0].record_frame != 0:
            raise RuntimeError(
                "Ride day 2 frame cursor did not reset to 0."
            )

        # Hero13 and Hero8 must land on different, stable tracks.
        hero8_day1 = [
            p for p in result.placements
            if p.camera_name == "GoPro HERO8 Black"
        ]

        if not hero8_day1:
            raise RuntimeError("No Hero8 placements produced.")

        if hero8_day1[0].track_index == hero13_day1[0].track_index:
            raise RuntimeError(
                "Hero13 and Hero8 clips were placed on the same "
                "track."
            )

        # Transcript availability: Hero13 segments should be
        # flagged as the transcript source.
        if result.statistics.transcript_segments == 0:
            raise RuntimeError(
                "No segments were flagged as having a transcript "
                "available (Hero13 lav mic rule)."
            )
