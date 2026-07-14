"""
============================================================
SBA AI Studio
Timeline Placement Builder
ML-011-014
Version : 3.0.0 Alpha
============================================================

Creates fully populated TimelinePlacement objects from
PlanningSegments.

This service calculates timeline placement information but
does not communicate with DaVinci Resolve.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable

from sba_resolve.core.models.planning_segment import PlanningSegment
from sba_resolve.core.models.timeline_placement import TimelinePlacement
from sba_resolve.core.services.project_time_service import (
    ProjectTimeService,
)


class TimelinePlacementBuilder:
    """
    Builds TimelinePlacement objects from PlanningSegments.
    """

    DEFAULT_FPS = 25.0

    def build(
        self,
        segments: Iterable[PlanningSegment],
    ) -> list[TimelinePlacement]:

        segments = list(segments)

        if not segments:
            return []

        media_files = []

        for segment in segments:
            media_files.extend(segment.available_clips)

        project_start = ProjectTimeService.project_start(media_files)

        placements: list[TimelinePlacement] = []

        for segment in segments:

            for media in segment.available_clips:

                placement = TimelinePlacement(
                    media_file=media
                )

                placement.ride_day = segment.ride_day

                placement.camera_name = (
                    getattr(media, "camera_display_name", None)
                    or getattr(media, "camera_model", None)
                    or "Unknown"
                )

                placement.clip_name = getattr(
                    media,
                    "filename",
                    "",
                )

                placement.track_index = 1

                placement.record_frame = self._record_frame(
                    media,
                    project_start,
                )

                placement.duration_frames = self._duration_frames(
                    media
                )

                placements.append(placement)

        return placements

    def _record_frame(
        self,
        media,
        project_start: datetime | None,
    ) -> int:

        if project_start is None:
            return 0

        capture_time = (
            getattr(media, "capture_time", None)
            or getattr(media, "created", None)
        )

        if capture_time is None:
            return 0

        delta = (
            capture_time - project_start
        ).total_seconds()

        return round(delta * self.DEFAULT_FPS)

    def _duration_frames(
        self,
        media,
    ) -> int:

        duration = getattr(media, "duration", None)

        if duration is None:
            return 0

        fps = (
            getattr(media, "fps", None)
            or self.DEFAULT_FPS
        )

        try:
            return round(float(duration) * float(fps))
        except (TypeError, ValueError):
            return 0