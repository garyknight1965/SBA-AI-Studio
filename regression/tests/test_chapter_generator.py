"""
============================================================
SBA AI Studio
Chapter Generator Regression Test
ML-030
Version : 1.0.0
============================================================

Verifies ChapterGenerator:
- Produces one chapter per scene, with correct elapsed time
  relative to that Ride Day's own start (not the whole
  project's).
- The first chapter is always exactly 0:00.
- Flags when there are fewer than 3 chapters (YouTube won't
  display chapters at all below that).
- Flags when two chapters are less than 10s apart (YouTube's
  minimum chapter length).
- format_for_description() renders ready-to-paste text.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from regression.base_test import BaseRegressionTest


class ChapterGeneratorRegressionTest(BaseRegressionTest):

    name = "Chapter Generator (ML-030)"

    category = "Planning"

    description = (
        "Verify chapter timestamps are day-relative, the first "
        "chapter is always 0:00, and YouTube's real chapter "
        "requirements are checked, not just assumed."
    )

    def _make_placement(
        self,
        clip_name,
        ride_day,
        scene,
        record_frame,
        duration_frames=1000,
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
        placement.clip_name = clip_name
        placement.record_frame = record_frame
        placement.duration_frames = duration_frames

        return placement

    def run(self) -> None:

        from sba_resolve.core.models.planning_result import PlanningResult
        from sba_resolve.core.services.chapter_generator import (
            ChapterGenerator,
        )

        fps = 25.0

        # Day 1: 3 well-spaced scenes (each far more than 10s
        # apart) - should meet YouTube's requirements cleanly.
        # Day starts at a large frame offset (100000) to prove
        # chapters are relative to the DAY's start, not frame 0.
        placements = [
            self._make_placement(
                "clip1.mp4", 1, 1, record_frame=100000
            ),
            self._make_placement(
                "clip2.mp4", 1, 2, record_frame=100000 + round(300 * fps)
            ),
            self._make_placement(
                "clip3.mp4", 1, 3, record_frame=100000 + round(900 * fps)
            ),
            # Day 2: only 2 scenes - below YouTube's minimum of 3.
            self._make_placement(
                "clip4.mp4", 2, 1, record_frame=500000
            ),
            self._make_placement(
                "clip5.mp4", 2, 2, record_frame=500000 + round(60 * fps)
            ),
        ]

        result = PlanningResult(placements=placements)

        generator = ChapterGenerator()

        output = generator.generate(result, fps=fps)

        if len(output["days"]) != 2:
            raise RuntimeError(
                f"Expected 2 days, got {len(output['days'])}."
            )

        day1 = output["days"][0]
        day2 = output["days"][1]

        if day1["ride_day"] != 1 or day2["ride_day"] != 2:
            raise RuntimeError("Days out of order or mislabeled.")

        # Day 1 chapters.
        if len(day1["chapters"]) != 3:
            raise RuntimeError(
                f"Expected 3 chapters for day 1, got "
                f"{len(day1['chapters'])}."
            )

        if day1["chapters"][0]["time_text"] != "0:00":
            raise RuntimeError(
                "First chapter must always be 0:00, got "
                f"{day1['chapters'][0]['time_text']!r}."
            )

        if day1["chapters"][1]["time_text"] != "5:00":
            raise RuntimeError(
                f"Expected second chapter at 5:00 (300s in), got "
                f"{day1['chapters'][1]['time_text']!r}."
            )

        if day1["chapters"][2]["time_text"] != "15:00":
            raise RuntimeError(
                f"Expected third chapter at 15:00 (900s in), got "
                f"{day1['chapters'][2]['time_text']!r}."
            )

        if not day1["meets_youtube_requirements"]:
            raise RuntimeError(
                f"Day 1 should meet YouTube's requirements "
                f"(3 chapters, well-spaced), got warnings: "
                f"{day1['warnings']}"
            )

        # Day 2: only 2 chapters - must warn about the 3-chapter
        # minimum.
        if len(day2["chapters"]) != 2:
            raise RuntimeError(
                f"Expected 2 chapters for day 2, got "
                f"{len(day2['chapters'])}."
            )

        if day2["meets_youtube_requirements"]:
            raise RuntimeError(
                "Day 2 has only 2 chapters - should NOT meet "
                "YouTube's minimum-3 requirement."
            )

        if not any("at least 3" in w for w in day2["warnings"]):
            raise RuntimeError(
                f"Expected a warning about needing at least 3 "
                f"chapters, got: {day2['warnings']}"
            )

        # --------------------------------------------------
        # Chapters closer than 10s apart must also warn.
        # --------------------------------------------------

        close_placements = [
            self._make_placement("a.mp4", 1, 1, record_frame=0),
            self._make_placement(
                "b.mp4", 1, 2, record_frame=round(5 * fps)
            ),
            self._make_placement(
                "c.mp4", 1, 3, record_frame=round(600 * fps)
            ),
        ]

        close_result = PlanningResult(placements=close_placements)

        close_output = generator.generate(close_result, fps=fps)

        close_day = close_output["days"][0]

        if close_day["meets_youtube_requirements"]:
            raise RuntimeError(
                "Two chapters only 5s apart should fail YouTube's "
                "10s minimum requirement."
            )

        if not any("10" in w for w in close_day["warnings"]):
            raise RuntimeError(
                f"Expected a warning mentioning the 10s minimum, "
                f"got: {close_day['warnings']}"
            )

        # --------------------------------------------------
        # format_for_description() renders ready-to-paste text.
        # --------------------------------------------------

        rendered = ChapterGenerator.format_for_description(day1)

        expected = "0:00 Scene 1\n5:00 Scene 2\n15:00 Scene 3"

        if rendered != expected:
            raise RuntimeError(
                f"Expected rendered text:\n{expected}\ngot:\n{rendered}"
            )
