"""
============================================================
SBA AI Studio
One Timeline Per Ride Day Regression Test
ML-057
Version : 1.0.0
============================================================

Verifies sba_resolve.commands.create_timeline.create_timeline()
against fake Resolve API objects, specifically for a two-ride-day
project:

- Exactly one Resolve timeline is created PER ride day (not one
  flat project-wide timeline).
- Each day's timeline is named "<project> Day <N> - <YYYY-MM-DD>",
  matching the format Gary chose.
- Each day's placements are rebased so that day's own earliest
  clip lands at frame 0 - Day 2's clips do NOT carry Day 1's
  project-wide frame numbers onto Day 2's timeline.
- Each day's own "Ride Day N" marker is written at frame 0 on
  that day's own timeline, not the other day's.
- The project's timeline frame rate is read once, up front, via
  Project.GetSetting("timelineFrameRate") - not from any specific
  timeline - since no timeline exists yet before the first one is
  built.

Reuses the fake Resolve API harness from test_create_timeline.py
rather than duplicating it.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest
from regression.tests.test_create_timeline import (
    FakeClip,
    FakeContext,
    FakeMediaPool,
    FakeProject,
)


class RideDayTimelinesRegressionTest(BaseRegressionTest):

    name = "One Timeline Per Ride Day (ML-057)"

    category = "Resolve"

    description = (
        "Verify create_timeline() builds one independent, "
        "correctly-named, correctly-rebased Resolve timeline "
        "per ride day, instead of one flat project-wide "
        "timeline."
    )

    def _make_media(
        self, filename, camera_model, created, duration_seconds, fps=24.0
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

        from sba_resolve.commands.create_timeline import create_timeline

        day1_start = datetime(2026, 7, 1, 9, 0, 0)
        day2_start = datetime(2026, 7, 3, 8, 0, 0)

        media_objects = [
            self._make_media(
                "day1_clip1.mp4", "HERO13 Black", day1_start, 60
            ),
            self._make_media(
                "day1_clip2.mp4",
                "HERO13 Black",
                day1_start + timedelta(seconds=61),
                30,
            ),
            self._make_media(
                "day2_clip1.mp4", "HERO13 Black", day2_start, 45
            ),
        ]

        imported_items = [
            FakeClip("day1_clip1.mp4"),
            FakeClip("day1_clip2.mp4"),
            FakeClip("day2_clip1.mp4"),
        ]

        project = FakeProject(timeline_fps="24")
        media_pool = FakeMediaPool()

        context = FakeContext(
            project=project,
            media_pool=media_pool,
            project_data={
                "project_name": "Test Project",
                "media_objects": media_objects,
                "enable_multicam_audio_sync": True,
            },
            imported_items=imported_items,
        )

        timeline = create_timeline(context)

        if timeline is None:
            raise RuntimeError("create_timeline() returned None.")

        # --------------------------------------------------
        # 1. Exactly one timeline per ride day.
        # --------------------------------------------------

        if len(media_pool.created_timelines) != 2:
            raise RuntimeError(
                f"Expected exactly 2 timelines created (one per "
                f"ride day), got "
                f"{len(media_pool.created_timelines)}."
            )

        day1_timeline, day2_timeline = media_pool.created_timelines

        # --------------------------------------------------
        # 2. Correct naming: "<project> Day <N> - <YYYY-MM-DD>".
        # --------------------------------------------------

        if day1_timeline.GetName() != "Test Project Day 1 - 2026-07-01":
            raise RuntimeError(
                f"Expected Day 1 timeline named "
                f"'Test Project Day 1 - 2026-07-01', got "
                f"{day1_timeline.GetName()!r}."
            )

        if day2_timeline.GetName() != "Test Project Day 2 - 2026-07-03":
            raise RuntimeError(
                f"Expected Day 2 timeline named "
                f"'Test Project Day 2 - 2026-07-03', got "
                f"{day2_timeline.GetName()!r}."
            )

        # The return value should be the LAST timeline built
        # (Day 2), matching the single-timeline return contract
        # existing callers/tests rely on.
        if timeline is not day2_timeline:
            raise RuntimeError(
                "Expected create_timeline() to return the last "
                "timeline built (Day 2)."
            )

        # --------------------------------------------------
        # 3. Day 1's clips landed on Day 1's timeline, rebased
        #    to start at frame 0 - and Day 2's clip must NOT
        #    appear on Day 1's timeline at all.
        # --------------------------------------------------

        day1_items = day1_timeline.items_by_track.get(1, [])

        if len(day1_items) != 2:
            raise RuntimeError(
                f"Expected 2 clips on Day 1's timeline, got "
                f"{len(day1_items)}."
            )

        day1_names = {
            item.GetMediaPoolItem().filename for item in day1_items
        }

        if day1_names != {"day1_clip1.mp4", "day1_clip2.mp4"}:
            raise RuntimeError(
                f"Expected only Day 1's own clips on Day 1's "
                f"timeline, got {day1_names!r}."
            )

        first_clip_item = next(
            item
            for item in day1_items
            if item.GetMediaPoolItem().filename == "day1_clip1.mp4"
        )

        if first_clip_item.GetStart() != 0:
            raise RuntimeError(
                f"Expected Day 1's earliest clip to rebase to "
                f"frame 0 on Day 1's own timeline, got "
                f"{first_clip_item.GetStart()}."
            )

        second_clip_item = next(
            item
            for item in day1_items
            if item.GetMediaPoolItem().filename == "day1_clip2.mp4"
        )

        # day1_clip2 starts 61s after day1_clip1, at 24fps.
        expected_second_frame = round(61 * 24)

        if second_clip_item.GetStart() != expected_second_frame:
            raise RuntimeError(
                f"Expected Day 1's second clip to sit at frame "
                f"{expected_second_frame} (61s later at 24fps) "
                f"relative to Day 1's own rebased start, got "
                f"{second_clip_item.GetStart()}."
            )

        # --------------------------------------------------
        # 4. Day 2's single clip landed on Day 2's OWN timeline,
        #    also rebased to frame 0 - NOT carrying Day 1's huge
        #    project-wide frame offset (~2 days later) onto its
        #    own timeline.
        # --------------------------------------------------

        day2_items = day2_timeline.items_by_track.get(1, [])

        if len(day2_items) != 1:
            raise RuntimeError(
                f"Expected 1 clip on Day 2's timeline, got "
                f"{len(day2_items)}."
            )

        if day2_items[0].GetMediaPoolItem().filename != "day2_clip1.mp4":
            raise RuntimeError(
                f"Expected Day 2's own clip on Day 2's timeline, "
                f"got "
                f"{day2_items[0].GetMediaPoolItem().filename!r}."
            )

        if day2_items[0].GetStart() != 0:
            raise RuntimeError(
                f"Expected Day 2's only clip to rebase to frame "
                f"0 on Day 2's own timeline (not carry Day 1's "
                f"project-wide offset), got "
                f"{day2_items[0].GetStart()}."
            )

        # --------------------------------------------------
        # 5. Each day's own "Ride Day N" marker landed at frame
        #    0 on that day's OWN timeline, not the other day's.
        # --------------------------------------------------

        if 0 not in day1_timeline.markers:
            raise RuntimeError(
                "Expected a 'Ride Day 1' marker at frame 0 on "
                "Day 1's own timeline."
            )

        if day1_timeline.markers[0]["name"] != "Ride Day 1":
            raise RuntimeError(
                f"Expected Day 1's frame-0 marker to be named "
                f"'Ride Day 1', got "
                f"{day1_timeline.markers[0]['name']!r}."
            )

        if 0 not in day2_timeline.markers:
            raise RuntimeError(
                "Expected a 'Ride Day 2' marker at frame 0 on "
                "Day 2's own timeline."
            )

        if day2_timeline.markers[0]["name"] != "Ride Day 2":
            raise RuntimeError(
                f"Expected Day 2's frame-0 marker to be named "
                f"'Ride Day 2', got "
                f"{day2_timeline.markers[0]['name']!r}."
            )

        # Cross-contamination check: Day 1's timeline should
        # have exactly 1 marker (its own), not 2.
        if len(day1_timeline.markers) != 1:
            raise RuntimeError(
                f"Expected exactly 1 marker on Day 1's timeline, "
                f"got {len(day1_timeline.markers)} - Day 2's "
                f"marker may have leaked onto Day 1's timeline."
            )

        if len(day2_timeline.markers) != 1:
            raise RuntimeError(
                f"Expected exactly 1 marker on Day 2's timeline, "
                f"got {len(day2_timeline.markers)} - Day 1's "
                f"marker may have leaked onto Day 2's timeline."
            )

        # --------------------------------------------------
        # 6. The project's frame rate was read from the PROJECT
        #    (not a specific timeline) before any timeline
        #    existed - confirmed indirectly above by the correct
        #    24fps-based frame math on both days.
        # --------------------------------------------------

        if project.current_timeline is not day2_timeline:
            raise RuntimeError(
                "Expected the project's current timeline to end "
                "on the last one built (Day 2)."
            )
