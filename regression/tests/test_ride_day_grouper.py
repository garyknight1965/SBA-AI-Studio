"""
============================================================
SBA AI Studio
Ride Day Grouper Regression Test
Version : 1.0.0
============================================================

Verifies RideDayGrouper (the "one timeline per ride day"
grouping/rebasing service):

- Placements/markers/unsynced clips are split correctly by
  ride_day.
- Each day's placements and markers are rebased so the day's
  earliest clip lands at frame 0, and every other frame in that
  day shifts by the same offset (internal relative timing is
  preserved).
- Rebasing one day never affects another day's frames.
- The date label is derived from each day's own earliest clip.
- A day with no known creation times falls back to "Day N" with
  no date suffix.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class RideDayGrouperRegressionTest(BaseRegressionTest):

    name = "Ride Day Grouper (ML-999)"

    category = "Planning"

    description = (
        "Verify PlanningResult is correctly split into one "
        "rebased RideDayTimelinePlan per ride day."
    )

    def _make_media(self, filename, created=None):

        from sba_resolve.core.models.media_file import MediaFile

        return MediaFile(
            filename=filename,
            full_path=Path(f"/fake/{filename}"),
            relative_path=Path(filename),
            extension=".mp4",
            size=1024,
            created=created,
        )

    def run(self) -> None:

        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.models.timeline_marker import TimelineMarker
        from sba_resolve.core.models.timeline_placement import (
            TimelinePlacement,
        )
        from sba_resolve.core.models.unsynced_clip import UnsyncedClip
        from sba_resolve.core.services.ride_day_grouper import (
            RideDayGrouper,
        )

        day1_start = datetime(2026, 7, 12, 9, 0, 0)
        day2_start = datetime(2026, 7, 13, 8, 30, 0)

        day1_clip1 = self._make_media("day1_clip1.mp4", day1_start)
        day1_clip2 = self._make_media(
            "day1_clip2.mp4", day1_start
        )

        day2_clip1 = self._make_media("day2_clip1.mp4", day2_start)

        # Day 1: frames 100000 and 101500 (project-wide, real
        # elapsed time since project start).
        day1_placement1 = TimelinePlacement(
            media_file=day1_clip1,
            ride_day=1,
            scene=1,
            track_index=1,
            record_frame=100_000,
            duration_frames=500,
            camera_name="GoPro HERO13 Black",
            clip_name="day1_clip1.mp4",
        )

        day1_placement2 = TimelinePlacement(
            media_file=day1_clip2,
            ride_day=1,
            scene=1,
            track_index=1,
            record_frame=101_500,
            duration_frames=300,
            camera_name="GoPro HERO13 Black",
            clip_name="day1_clip2.mp4",
        )

        # Day 2: much later project-wide frame (real elapsed
        # time since project start, roughly 24h later).
        day2_placement1 = TimelinePlacement(
            media_file=day2_clip1,
            ride_day=2,
            scene=1,
            track_index=1,
            record_frame=2_260_000,
            duration_frames=400,
            camera_name="GoPro HERO13 Black",
            clip_name="day2_clip1.mp4",
        )

        day1_marker = TimelineMarker(
            frame=100_000,
            title="Ride Day 1",
            category="Ride Day",
            ride_day=1,
        )

        day2_marker = TimelineMarker(
            frame=2_260_000,
            title="Ride Day 2",
            category="Ride Day",
            ride_day=2,
        )

        day1_unsynced = UnsyncedClip(
            camera_name="GoPro HERO8 Black",
            clip_name="day1_hero8.mp4",
            reason="Audio sync disabled.",
            ride_day=1,
        )

        result = PlanningResult(
            placements=[
                day1_placement1,
                day1_placement2,
                day2_placement1,
            ],
            markers=[day1_marker, day2_marker],
            unsynced_clips=[day1_unsynced],
        )

        plans = RideDayGrouper.group(result)

        # --------------------------------------------------
        # 1. Correct number of days, in order.
        # --------------------------------------------------

        if len(plans) != 2:
            raise RuntimeError(
                f"Expected 2 RideDayTimelinePlan objects, got "
                f"{len(plans)}."
            )

        day1_plan, day2_plan = plans

        if day1_plan.ride_day != 1 or day2_plan.ride_day != 2:
            raise RuntimeError(
                f"Expected plans in ride_day order [1, 2], got "
                f"[{day1_plan.ride_day}, {day2_plan.ride_day}]."
            )

        # --------------------------------------------------
        # 2. Day 1 rebasing: earliest clip (100000) -> frame 0,
        #    internal offset to the second clip preserved.
        # --------------------------------------------------

        if len(day1_plan.placements) != 2:
            raise RuntimeError(
                f"Expected 2 placements on Day 1, got "
                f"{len(day1_plan.placements)}."
            )

        rebased_by_name = {
            p.clip_name: p for p in day1_plan.placements
        }

        if rebased_by_name["day1_clip1.mp4"].record_frame != 0:
            raise RuntimeError(
                f"Expected Day 1's earliest clip to rebase to "
                f"frame 0, got "
                f"{rebased_by_name['day1_clip1.mp4'].record_frame}."
            )

        if rebased_by_name["day1_clip2.mp4"].record_frame != 1_500:
            raise RuntimeError(
                f"Expected the second Day 1 clip's relative "
                f"offset (1500 frames) to be preserved after "
                f"rebasing, got "
                f"{rebased_by_name['day1_clip2.mp4'].record_frame}."
            )

        # --------------------------------------------------
        # 3. Day 2 rebasing is independent of Day 1 - its own
        #    single clip also rebases to frame 0, regardless of
        #    Day 1's project-wide frame numbers.
        # --------------------------------------------------

        if len(day2_plan.placements) != 1:
            raise RuntimeError(
                f"Expected 1 placement on Day 2, got "
                f"{len(day2_plan.placements)}."
            )

        if day2_plan.placements[0].record_frame != 0:
            raise RuntimeError(
                f"Expected Day 2's only clip to rebase to frame "
                f"0, got {day2_plan.placements[0].record_frame}."
            )

        # --------------------------------------------------
        # 4. Markers rebase the same way and stay on the
        #    correct day.
        # --------------------------------------------------

        if len(day1_plan.markers) != 1 or len(day2_plan.markers) != 1:
            raise RuntimeError(
                "Expected exactly 1 marker on each day after "
                "grouping."
            )

        if day1_plan.markers[0].frame != 0:
            raise RuntimeError(
                f"Expected Day 1's marker to rebase to frame 0, "
                f"got {day1_plan.markers[0].frame}."
            )

        if day2_plan.markers[0].frame != 0:
            raise RuntimeError(
                f"Expected Day 2's marker to rebase to frame 0, "
                f"got {day2_plan.markers[0].frame}."
            )

        # --------------------------------------------------
        # 5. Unsynced clips are grouped by day, untouched
        #    otherwise (no frame to rebase).
        # --------------------------------------------------

        if len(day1_plan.unsynced_clips) != 1:
            raise RuntimeError(
                f"Expected 1 unsynced clip on Day 1, got "
                f"{len(day1_plan.unsynced_clips)}."
            )

        if day2_plan.unsynced_clips:
            raise RuntimeError(
                "Expected no unsynced clips on Day 2."
            )

        # --------------------------------------------------
        # 6. Date labels derived from each day's own earliest
        #    clip, and the timeline_name_suffix format Gary
        #    chose ("Day 1 - 2026-07-12").
        # --------------------------------------------------

        if day1_plan.date_label != "2026-07-12":
            raise RuntimeError(
                f"Expected Day 1's date label '2026-07-12', got "
                f"{day1_plan.date_label!r}."
            )

        if day1_plan.timeline_name_suffix != "Day 1 - 2026-07-12":
            raise RuntimeError(
                f"Expected timeline name suffix "
                f"'Day 1 - 2026-07-12', got "
                f"{day1_plan.timeline_name_suffix!r}."
            )

        if day2_plan.date_label != "2026-07-13":
            raise RuntimeError(
                f"Expected Day 2's date label '2026-07-13', got "
                f"{day2_plan.date_label!r}."
            )

        # --------------------------------------------------
        # 7. Fallback: a day with no known creation times gets
        #    no date suffix.
        # --------------------------------------------------

        undated_clip = self._make_media("day3_clip.mp4", created=None)

        undated_placement = TimelinePlacement(
            media_file=undated_clip,
            ride_day=3,
            scene=1,
            track_index=1,
            record_frame=5_000_000,
            duration_frames=250,
            camera_name="GoPro HERO13 Black",
            clip_name="day3_clip.mp4",
        )

        undated_result = PlanningResult(
            placements=[undated_placement],
        )

        undated_plans = RideDayGrouper.group(undated_result)

        if len(undated_plans) != 1:
            raise RuntimeError(
                f"Expected 1 plan for the undated fixture, got "
                f"{len(undated_plans)}."
            )

        if undated_plans[0].date_label != "":
            raise RuntimeError(
                f"Expected no date label when no clip has a "
                f"known creation time, got "
                f"{undated_plans[0].date_label!r}."
            )

        if undated_plans[0].timeline_name_suffix != "Day 3":
            raise RuntimeError(
                f"Expected fallback timeline name suffix "
                f"'Day 3', got "
                f"{undated_plans[0].timeline_name_suffix!r}."
            )
