"""
============================================================
SBA AI Studio
Ride Summary Builder - Scene Facts Regression Test
ML-030
Version : 1.0.0
============================================================

Verifies RideSummaryBuilder.build_scenes():
- Per-scene duration is summed correctly from placement data
  (not the always-zero PlanningSegment.start_frame/end_frame).
- camera_count/cameras reflect distinct cameras per scene.
- is_multicam correctly reflects overlap with a
  MulticamCandidate in the same ride_day.
- has_hero13_audio is True only when a HERO13 camera
  contributed a clip to that scene.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from regression.base_test import BaseRegressionTest


class RideSummarySceneFactsRegressionTest(BaseRegressionTest):

    name = "Ride Summary Scene Facts (ML-030)"

    category = "Planning"

    description = (
        "Verify per-scene duration, camera, multicam, and "
        "HERO13-audio facts used for editing suggestions."
    )

    def _make_placement(
        self,
        clip_name,
        ride_day,
        scene,
        camera_name,
        record_frame,
        duration_frames,
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
            created=datetime(2026, 7, 1, 9, 0, 0),
            duration="60",
        )

        placement = TimelinePlacement(media_file=media)
        placement.ride_day = ride_day
        placement.scene = scene
        placement.camera_name = camera_name
        placement.clip_name = clip_name
        placement.record_frame = record_frame
        placement.duration_frames = duration_frames

        return placement

    def run(self) -> None:

        from sba_resolve.core.models.multicam_candidate import (
            MulticamCandidate,
        )
        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.services.ride_summary_builder import (
            RideSummaryBuilder,
        )

        fps = 25.0

        placements = [
            # Scene 1: single camera, no multicam, has HERO13.
            self._make_placement(
                "clip1.mp4",
                1,
                1,
                "GoPro HERO13 Black",
                record_frame=0,
                duration_frames=round(120 * fps),
            ),
            # Scene 2: two cameras, overlapping in time (a real
            # multicam window), includes HERO13.
            self._make_placement(
                "clip2.mp4",
                1,
                2,
                "GoPro HERO13 Black",
                record_frame=round(200 * fps),
                duration_frames=round(60 * fps),
            ),
            self._make_placement(
                "clip3.mp4",
                1,
                2,
                "GoPro HERO8 Black",
                record_frame=round(210 * fps),
                duration_frames=round(40 * fps),
            ),
            # Scene 3: single camera, HERO8 only - no HERO13
            # audio available.
            self._make_placement(
                "clip4.mp4",
                1,
                3,
                "GoPro HERO8 Black",
                record_frame=round(400 * fps),
                duration_frames=round(30 * fps),
            ),
        ]

        multicam_candidates = [
            MulticamCandidate(
                start_frame=round(200 * fps),
                end_frame=round(250 * fps),
                ride_day=1,
            ),
        ]

        result = PlanningResult(
            placements=placements,
            multicam_candidates=multicam_candidates,
        )

        scenes = RideSummaryBuilder().build_scenes(result, fps=fps)

        if len(scenes) != 3:
            raise RuntimeError(f"Expected 3 scenes, got {len(scenes)}.")

        scene1, scene2, scene3 = scenes

        # Scene 1 checks.
        if scene1["duration_minutes"] != 2.0:
            raise RuntimeError(
                f"Expected scene 1 duration 2.0 min, got "
                f"{scene1['duration_minutes']!r}."
            )

        if scene1["is_multicam"]:
            raise RuntimeError("Scene 1 should not be flagged multicam.")

        if not scene1["has_hero13_audio"]:
            raise RuntimeError(
                "Scene 1 has a HERO13 clip - has_hero13_audio "
                "should be True."
            )

        if scene1["camera_count"] != 1:
            raise RuntimeError(
                f"Expected scene 1 camera_count 1, got "
                f"{scene1['camera_count']!r}."
            )

        # Scene 2 checks (the multicam one).
        if scene2["camera_count"] != 2:
            raise RuntimeError(
                f"Expected scene 2 camera_count 2, got "
                f"{scene2['camera_count']!r}."
            )

        if not scene2["is_multicam"]:
            raise RuntimeError(
                "Scene 2 overlaps a real MulticamCandidate - "
                "should be flagged is_multicam=True."
            )

        if scene2["clip_count"] != 2:
            raise RuntimeError(
                f"Expected scene 2 clip_count 2, got "
                f"{scene2['clip_count']!r}."
            )

        # 60s (clip2) + 40s (clip3) = 100s = 1.7 min (rounded).
        if scene2["duration_minutes"] != 1.7:
            raise RuntimeError(
                f"Expected scene 2 duration 1.7 min, got "
                f"{scene2['duration_minutes']!r}."
            )

        # Scene 3 checks (HERO8 only, no HERO13 audio).
        if scene3["has_hero13_audio"]:
            raise RuntimeError(
                "Scene 3 has no HERO13 clip - has_hero13_audio "
                "should be False."
            )

        if scene3["is_multicam"]:
            raise RuntimeError(
                "Scene 3 does not overlap the multicam window - "
                "should not be flagged is_multicam."
            )

        if scene3["cameras"] != ["GoPro HERO8 Black"]:
            raise RuntimeError(
                f"Expected scene 3 cameras ['GoPro HERO8 Black'], "
                f"got {scene3['cameras']!r}."
            )
