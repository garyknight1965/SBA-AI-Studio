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
