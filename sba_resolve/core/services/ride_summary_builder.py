"""
============================================================
SBA AI Studio
Ride Summary Builder
ML-026-003
Version : 1.0.0 Alpha
============================================================

Turns a PlanningResult into a structured, human-readable
per-day summary - the real-world facts (dates, duration,
cameras used, scene count, GPS-derived place names) that
YouTubeMetadataGenerator feeds to the language model.

This is pure summarisation of facts already reconstructed by
the Planning Engine - it never invents ride details.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from sba_resolve.core.services.reverse_geocoder import ReverseGeocoder
from sba_resolve.core.services.timeline_fps import DEFAULT_PROJECT_FPS


class RideSummaryBuilder:
    """
    Builds a per-day ride summary from a PlanningResult.
    """

    def __init__(self, geocoder: ReverseGeocoder | None = None) -> None:
        self.geocoder = geocoder or ReverseGeocoder()

    def build(self, result, fps: float | None = None) -> dict:
        """
        Returns a dict:

            {
                "total_days": int,
                "days": [
                    {
                        "day": 1,
                        "date": "2026-06-25" | None,
                        "duration_minutes": 52.3,
                        "cameras": ["GoPro HERO13 Black", ...],
                        "scene_count": 3,
                        "places": ["Whithorn, Scotland, ..."],
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
            self._build_day(day_index, placements_by_day[day_index], fps)
            for day_index in sorted(placements_by_day)
        ]

        return {
            "total_days": len(days),
            "days": days,
        }

    def _build_day(self, day_index: int, placements: Iterable, fps: float) -> dict:

        placements = list(placements)

        total_duration_seconds = sum(
            (p.duration_frames or 0) / fps for p in placements
        )

        cameras = sorted(
            {
                p.camera_name
                for p in placements
                if p.camera_name
            }
        )

        scene_count = len({p.scene for p in placements})

        capture_times = [
            p.media_file.created
            for p in placements
            if getattr(p.media_file, "created", None) is not None
        ]

        earliest = min(capture_times) if capture_times else None

        places = self._places_for(placements)

        return {
            "day": day_index,
            "date": earliest.date().isoformat() if earliest else None,
            "duration_minutes": round(total_duration_seconds / 60, 1),
            "cameras": cameras,
            "scene_count": scene_count,
            "places": places,
        }

    def _places_for(self, placements: list) -> list[str]:

        places: list[str] = []
        seen: set[str] = set()

        for placement in placements:

            media = placement.media_file

            name = self.geocoder.place_name(
                getattr(media, "gps_latitude", None),
                getattr(media, "gps_longitude", None),
            )

            if name and name not in seen:
                seen.add(name)
                places.append(name)

        return places

    # ------------------------------------------------------------------
    # Scene-level facts (ML-030)
    # ------------------------------------------------------------------

    def build_scenes(self, result, fps: float | None = None) -> list[dict]:
        """
        Returns one dict per (ride_day, scene), ordered by ride day
        then scene number:

            {
                "ride_day": 1,
                "scene": 2,
                "clip_count": 2,
                "duration_minutes": 1.7,
                "camera_count": 2,
                "cameras": ["GoPro HERO13 Black", "GoPro HERO8 Black"],
                "is_multicam": True,
                "has_hero13_audio": True,
            }

        Duration is summed from each placement's actual
        `duration_frames` (real clip length on the timeline), not
        `PlanningSegment.start_frame`/`end_frame`, which are always
        zero. `is_multicam` reflects a genuine frame-range overlap
        with a MulticamCandidate on the same ride day - it isn't
        just "more than one camera in the scene."
        """

        fps = fps if fps and fps > 0 else DEFAULT_PROJECT_FPS

        placements_by_scene: dict[tuple[int, int], list] = defaultdict(
            list
        )

        for placement in result.placements:
            key = (placement.ride_day, placement.scene)
            placements_by_scene[key].append(placement)

        multicam_candidates = list(
            getattr(result, "multicam_candidates", None) or []
        )

        return [
            self._build_scene(
                ride_day,
                scene_number,
                items,
                fps,
                multicam_candidates,
            )
            for (ride_day, scene_number), items in sorted(
                placements_by_scene.items()
            )
        ]

    def _build_scene(
        self,
        ride_day: int,
        scene_number: int,
        placements: list,
        fps: float,
        multicam_candidates: list,
    ) -> dict:

        total_duration_seconds = sum(
            (p.duration_frames or 0) / fps for p in placements
        )

        cameras = sorted(
            {p.camera_name for p in placements if p.camera_name}
        )

        has_hero13_audio = any(
            p.camera_name and "HERO13" in p.camera_name.upper()
            for p in placements
        )

        scene_start = min(p.record_frame for p in placements)
        scene_end = max(p.end_frame for p in placements)

        is_multicam = any(
            candidate.ride_day == ride_day
            and scene_start < candidate.end_frame
            and scene_end > candidate.start_frame
            for candidate in multicam_candidates
        )

        return {
            "ride_day": ride_day,
            "scene": scene_number,
            "clip_count": len(placements),
            "duration_minutes": round(total_duration_seconds / 60, 1),
            "camera_count": len(cameras),
            "cameras": cameras,
            "is_multicam": is_multicam,
            "has_hero13_audio": has_hero13_audio,
        }
