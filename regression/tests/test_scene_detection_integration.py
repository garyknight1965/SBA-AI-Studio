"""
============================================================
SBA AI Studio
Scene Detection Integration Regression Test
ML-020
Version : 1.0.0
============================================================

Verifies Scene Detection is correctly wired through the full
Planning Engine pipeline:

- PlanningSegments and TimelinePlacements are stamped with the
  correct scene index (not just ride_day).
- PlanningStatistics.scenes reflects the real scene count.
- TimelineMarkerGenerator emits a "Scene N" marker for every
  scene EXCEPT scene 1 of each day (which lands on the exact
  same frame as that day's Ride Day marker - Resolve only
  accepts one marker per frame, so scene 1 is intentionally
  skipped rather than silently colliding).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class SceneDetectionIntegrationRegressionTest(BaseRegressionTest):

    name = "Scene Detection Integration (ML-020)"

    category = "Planning"

    description = (
        "Verify Scene Detection is wired through segments, "
        "placements, statistics, and markers end to end."
    )

    def _make_media(self, filename, camera_model, created, duration_seconds=60, fps=25.0):

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
        from sba_resolve.core.services.timeline_planning_service import (
            TimelinePlanningService,
        )

        day1_start = datetime(2026, 7, 1, 9, 0, 0)

        library = MediaLibrary()

        # Day 1, Scene 1: two clips close together.
        library.add(
            self._make_media("clip1.mp4", "HERO13 Black", day1_start)
        )
        library.add(
            self._make_media(
                "clip2.mp4",
                "HERO13 Black",
                day1_start + timedelta(seconds=90),
            )
        )

        # Day 1, Scene 2: after a 20 minute gap (fuel stop).
        scene2_start = day1_start + timedelta(seconds=90, minutes=20)
        library.add(
            self._make_media("clip3.mp4", "HERO13 Black", scene2_start)
        )

        # Day 2 (after a 6 hour gap - well past the 4 hour Ride Day
        # threshold): Scene 1 of the new day.
        day2_start = scene2_start + timedelta(hours=6)
        library.add(
            self._make_media("clip4.mp4", "HERO13 Black", day2_start)
        )

        result = TimelinePlanningService().plan(library)

        # --------------------------------------------------
        # Statistics
        # --------------------------------------------------

        if result.statistics.ride_days != 2:
            raise RuntimeError(
                f"Expected 2 ride days, got "
                f"{result.statistics.ride_days}."
            )

        if result.statistics.scenes != 3:
            raise RuntimeError(
                f"Expected 3 scenes total (2 on day 1, 1 on day "
                f"2), got {result.statistics.scenes}."
            )

        # --------------------------------------------------
        # Segments stamped with (ride_day, scene)
        # --------------------------------------------------

        segments_by_clip = {}

        for segment in result.segments:
            for clip in segment.available_clips:
                segments_by_clip[clip.filename] = (
                    segment.ride_day,
                    segment.scene,
                )

        expected_segment_stamps = {
            "clip1.mp4": (1, 1),
            "clip2.mp4": (1, 1),
            "clip3.mp4": (1, 2),
            "clip4.mp4": (2, 1),
        }

        if segments_by_clip != expected_segment_stamps:
            raise RuntimeError(
                f"Segment (ride_day, scene) stamps don't match. "
                f"Expected {expected_segment_stamps}, got "
                f"{segments_by_clip}."
            )

        # --------------------------------------------------
        # Placements stamped with (ride_day, scene) too
        # --------------------------------------------------

        placements_by_clip = {
            p.clip_name: (p.ride_day, p.scene)
            for p in result.placements
        }

        if placements_by_clip != expected_segment_stamps:
            raise RuntimeError(
                f"Placement (ride_day, scene) stamps don't "
                f"match. Expected {expected_segment_stamps}, got "
                f"{placements_by_clip}."
            )

        # --------------------------------------------------
        # Markers: Ride Day 1, Ride Day 2, and Scene 2 of Day 1
        # (Scene 1 of each day is intentionally skipped - same
        # frame as that day's Ride Day marker).
        # --------------------------------------------------

        scene_markers = [
            m for m in result.markers if m.category == "Scene"
        ]

        if len(scene_markers) != 1:
            raise RuntimeError(
                f"Expected exactly 1 Scene marker (Day 1 Scene "
                f"2 - both days' Scene 1 should be skipped), got "
                f"{len(scene_markers)}: "
                f"{[m.title for m in scene_markers]}"
            )

        if scene_markers[0].title != "Day 1 - Scene 2":
            raise RuntimeError(
                f"Expected the Scene marker titled 'Day 1 - "
                f"Scene 2', got {scene_markers[0].title!r}."
            )

        ride_day_markers = [
            m for m in result.markers if m.category == "Ride Day"
        ]

        if len(ride_day_markers) != 2:
            raise RuntimeError(
                f"Expected 2 Ride Day markers, got "
                f"{len(ride_day_markers)}."
            )

        # No two markers should ever share a frame (Resolve only
        # accepts one marker per frame).
        frames = [m.frame for m in result.markers]

        if len(frames) != len(set(frames)):
            raise RuntimeError(
                f"Two or more markers share the same frame - "
                f"Resolve would silently fail to add one of "
                f"them. Frames: {frames}"
            )
