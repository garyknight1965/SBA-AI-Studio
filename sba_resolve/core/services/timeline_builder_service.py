"""
============================================================
SBA AI Studio
Timeline Builder Service
Version : 1.0.0
Sprint : ML-009
============================================================

Builds a TimelinePlan from a MediaLibrary.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sba_resolve.core.models.media_library import MediaLibrary
from sba_resolve.core.models.timeline_plan import (
    TimelineClip,
    TimelineDay,
    TimelinePlan,
    TimelineTrack,
)


class TimelineBuilderService:
    """
    Builds an editable TimelinePlan from a MediaLibrary.
    """

    def build(
        self,
        library: MediaLibrary,
    ) -> TimelinePlan:

        plan = TimelinePlan()

        library.sort_by_capture_time()

        grouped_by_day: dict[date, list] = defaultdict(list)

        for media in library:

            if media.created is None:
                continue

            grouped_by_day[media.created.date()].append(media)

        for day in sorted(grouped_by_day.keys()):

            day_model = TimelineDay(day)

            grouped_by_camera: dict[str, list] = defaultdict(list)

            for media in grouped_by_day[day]:

                grouped_by_camera[
                    media.camera_display_name
                ].append(media)

            track_number = 1

            for camera in sorted(grouped_by_camera.keys()):

                track = TimelineTrack(camera)

                clips = sorted(
                    grouped_by_camera[camera],
                    key=lambda m: m.created,
                )

                for media in clips:

                    clip = TimelineClip(
                        media=media,
                        track=track_number,
                    )

                    track.add(clip)

                    plan.source_files.append(
                        media.full_path
                    )

                day_model.add_track(track)

                track_number += 1

            plan.add_day(day_model)

        return plan