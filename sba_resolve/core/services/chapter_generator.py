"""
============================================================
SBA AI Studio
Chapter Generator
ML-030-001
Version : 1.0.0 Alpha
============================================================

Generates YouTube-style chapter markers from Scene Detection
boundaries. This is pure, deterministic arithmetic on data the
Planning Engine already produced - no AI involved, no
hallucination risk.

IMPORTANT CAVEAT: these timestamps are relative to each Ride
Day's RAW, reconstructed footage (that day's earliest clip =
0:00), not to your final EDITED video. If your edit trims,
reorders, or removes footage, these need adjusting against your
actual edited timeline - this is a starting point, not a final
chapter list.

YouTube's real chapter requirements (checked here, not just
assumed):
    - The first chapter must start at 0:00.
    - At least 3 chapters are required for YouTube to display
      them at all.
    - Each chapter must be at least 10 seconds long.
"""

from __future__ import annotations

from collections import defaultdict

from sba_resolve.core.services.timeline_fps import DEFAULT_PROJECT_FPS

MIN_CHAPTER_SECONDS = 10.0

MIN_CHAPTERS_FOR_YOUTUBE = 3


class ChapterGenerator:
    """
    Builds one chapter list per Ride Day from a PlanningResult.
    """

    def generate(self, result, fps: float | None = None) -> dict:
        """
        Returns:

            {
                "days": [
                    {
                        "ride_day": 1,
                        "chapters": [
                            {
                                "time_seconds": 0.0,
                                "time_text": "0:00",
                                "label": "Scene 1",
                            },
                            ...
                        ],
                        "meets_youtube_requirements": True,
                        "warnings": [...],
                    },
                    ...
                ],
            }
        """

        fps = fps if fps and fps > 0 else DEFAULT_PROJECT_FPS

        placements_by_day: dict[int, list] = defaultdict(list)

        for placement in result.placements:
            placements_by_day[placement.ride_day].append(placement)

        days = [
            self._build_day(ride_day, placements_by_day[ride_day], fps)
            for ride_day in sorted(placements_by_day)
        ]

        return {"days": days}

    def _build_day(self, ride_day: int, placements: list, fps: float) -> dict:

        day_start_frame = min(p.record_frame for p in placements)

        scene_start_frame: dict[int, int] = {}

        for placement in placements:

            scene = placement.scene

            if (
                scene not in scene_start_frame
                or placement.record_frame < scene_start_frame[scene]
            ):
                scene_start_frame[scene] = placement.record_frame

        chapters = []

        for scene in sorted(scene_start_frame):

            elapsed_seconds = (
                scene_start_frame[scene] - day_start_frame
            ) / fps

            chapters.append(
                {
                    "time_seconds": elapsed_seconds,
                    "time_text": self._format_time(elapsed_seconds),
                    "label": f"Scene {scene}",
                }
            )

        if chapters:
            # Guard against float noise - the first chapter must
            # be exactly 0:00 by YouTube's rules, and should
            # already be by construction (day_start_frame IS the
            # earliest scene's start).
            chapters[0]["time_seconds"] = 0.0
            chapters[0]["time_text"] = "0:00"

        warnings = self._check_requirements(chapters)

        return {
            "ride_day": ride_day,
            "chapters": chapters,
            "meets_youtube_requirements": not warnings,
            "warnings": warnings,
        }

    @staticmethod
    def _check_requirements(chapters: list[dict]) -> list[str]:

        warnings = []

        if len(chapters) < MIN_CHAPTERS_FOR_YOUTUBE:
            warnings.append(
                f"Only {len(chapters)} chapter(s) - YouTube "
                f"requires at least {MIN_CHAPTERS_FOR_YOUTUBE} "
                f"to display chapters at all."
            )

        for index in range(1, len(chapters)):

            gap = (
                chapters[index]["time_seconds"]
                - chapters[index - 1]["time_seconds"]
            )

            if gap < MIN_CHAPTER_SECONDS:
                warnings.append(
                    f"'{chapters[index - 1]['label']}' is only "
                    f"{gap:.0f}s before '{chapters[index]['label']}' "
                    f"- YouTube requires each chapter to be at "
                    f"least {MIN_CHAPTER_SECONDS:.0f}s."
                )

        return warnings

    @staticmethod
    def _format_time(total_seconds: float) -> str:

        total_seconds = max(0, round(total_seconds))

        hours, remainder = divmod(total_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"

        return f"{minutes}:{seconds:02d}"

    @staticmethod
    def format_for_description(day_chapters: dict) -> str:
        """
        Renders one day's chapters as ready-to-paste text for a
        YouTube video description.
        """

        return "\n".join(
            f"{chapter['time_text']} {chapter['label']}"
            for chapter in day_chapters["chapters"]
        )
