"""
============================================================
SBA AI Studio
Planning Pipeline Regression Test
ML-011
Version : 2.1.0
============================================================

Verifies the full Ride Reconstruction pipeline:

    MediaLibrary -> TimelinePlanningService.plan() -> PlanningResult

Uses synthetic MediaFile objects so this test is fully portable
and does not depend on real footage being present on disk.

Version 2 validates the real (ProjectTimeService-based)
gap-preserving placement semantics: record_frame reflects true
elapsed seconds since the project's earliest clip, and track
assignment is stable per camera across ride days.

Version 2.1.0 (2026-07-19, ML-054 Scope Change #2) updates
expectations for the new real default: TimelinePlanningService()
with no override has enable_multicam_audio_sync=False, under
which ONLY GoPro HERO13 Black clips auto-place - hero8_0001.mp4
now correctly lands in result.unsynced_clips instead of
result.placements. This is the new intended default behaviour,
not a regression.
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
        "produces a correct, gap-preserving PlanningResult across "
        "two ride days and two cameras, with HERO13-only "
        "auto-placement under the default (audio sync disabled) "
        "configuration."
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
        # then Hero8, back-to-back with small real-world gaps.
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
        # of 4 hours) so this must become a separate RideDay, while
        # placement still reflects true elapsed time since the
        # project's very first clip (gap-preserving design).
        day2_start = day1_start + timedelta(hours=6)

        library.add(
            self._make_media(
                "hero13_0003.mp4",
                "HERO13 Black",
                day2_start,
                duration_seconds=20,
            )
        )

        # Real default: TimelinePlanningService() with no override
        # means enable_multicam_audio_sync=False - only GoPro
        # HERO13 Black clips auto-place.
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
        # Segments are unaffected by the HERO13-only placement
        # rule - every clip still gets a segment regardless of
        # whether it ends up placed or unsynced.
        if len(result.segments) != 3:
            raise RuntimeError(
                f"Expected 3 planning segments, got "
                f"{len(result.segments)}."
            )

        # Only the 3 Hero13 clips auto-place under the default
        # (audio sync disabled) configuration - hero8_0001.mp4
        # is excluded and lands in unsynced_clips instead.
        if len(result.placements) != 3:
            raise RuntimeError(
                f"Expected 3 placements (HERO13 clips only), got "
                f"{len(result.placements)}."
            )

        by_clip = {p.clip_name: p for p in result.placements}

        if "hero8_0001.mp4" in by_clip:
            raise RuntimeError(
                "hero8_0001.mp4 should NOT be in placements under "
                "the default (audio sync disabled) configuration - "
                "only GoPro HERO13 Black auto-places."
            )

        # project_start = the earliest clip in the whole project
        # (hero13_0001.mp4). Every record_frame is relative to it.
        fps = 25.0

        expected_frames = {
            "hero13_0001.mp4": 0,
            "hero13_0002.mp4": round(61 * fps),
            "hero13_0003.mp4": round(
                timedelta(hours=6).total_seconds() * fps
            ),
        }

        for clip_name, expected_frame in expected_frames.items():

            placement = by_clip.get(clip_name)

            if placement is None:
                raise RuntimeError(
                    f"No placement produced for {clip_name}."
                )

            if placement.record_frame != expected_frame:
                raise RuntimeError(
                    f"{clip_name}: expected record_frame "
                    f"{expected_frame} (gap-preserving, relative "
                    f"to project start), got "
                    f"{placement.record_frame}."
                )

        # hero8_0001.mp4 must instead appear in unsynced_clips,
        # with the correct camera name, ready for a placeholder
        # track.
        unsynced_by_clip = {
            u.clip_name: u for u in result.unsynced_clips
        }

        if "hero8_0001.mp4" not in unsynced_by_clip:
            raise RuntimeError(
                "Expected hero8_0001.mp4 in result.unsynced_clips "
                "under the default (audio sync disabled) "
                "configuration."
            )

        if unsynced_by_clip["hero8_0001.mp4"].camera_name != (
            "GoPro HERO8 Black"
        ):
            raise RuntimeError(
                "Expected hero8_0001.mp4's unsynced camera_name to "
                "be 'GoPro HERO8 Black', got "
                f"{unsynced_by_clip['hero8_0001.mp4'].camera_name!r}."
            )

        # Ride day stamping must be correct.
        if by_clip["hero13_0003.mp4"].ride_day != 2:
            raise RuntimeError(
                "hero13_0003.mp4 should belong to ride day 2."
            )

        for clip_name in ("hero13_0001.mp4", "hero13_0002.mp4"):
            if by_clip[clip_name].ride_day != 1:
                raise RuntimeError(
                    f"{clip_name} should belong to ride day 1."
                )

        # Track assignment must be stable for the same camera
        # (Hero13) across ride days.
        hero13_track = by_clip["hero13_0001.mp4"].track_index

        if by_clip["hero13_0003.mp4"].track_index != hero13_track:
            raise RuntimeError(
                "Hero13's track index changed between ride days; "
                "track assignment must be stable per camera."
            )

        # Transcript availability: Hero13 segments should be
        # flagged as the transcript source.
        if result.statistics.transcript_segments == 0:
            raise RuntimeError(
                "No segments were flagged as having a transcript "
                "available (Hero13 lav mic rule)."
            )